"""Serviços do protótipo de rotas de fiscalização."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.licenciamento.models import LicencaAlvara, StatusLicenca
from apps.usuarios.models import Ambulante, Fiscal, Gestor

from .models import (
    ParadaRota,
    RegistroVisita,
    RotaFiscal,
    StatusParada,
    StatusRota,
)


def _ponto_do_ambulante(ambulante):
    licenca = (
        LicencaAlvara.objects.filter(
            ambulante=ambulante,
            status=StatusLicenca.ATIVO,
            ponto_ocupacao__isnull=False,
        )
        .select_related("ponto_ocupacao")
        .order_by("-data_emissao", "-pk")
        .first()
    )
    if licenca and licenca.ponto_ocupacao_id:
        return licenca.ponto_ocupacao
    return getattr(ambulante, "ponto_pretendido", None)


@transaction.atomic
def criar_rota(gestor, fiscal, titulo, ambulante_ids, data_prevista=None, observacoes=""):
    if not isinstance(fiscal, Fiscal):
        fiscal = Fiscal.objects.filter(pk=getattr(fiscal, "pk", None)).first()
    if fiscal is None:
        raise ValueError("Fiscal inválido para a rota.")

    criado_por = None
    if gestor is not None:
        criado_por = Gestor.objects.filter(pk=getattr(gestor, "pk", None)).first()

    ids = [int(x) for x in ambulante_ids if x]
    if not ids:
        raise ValueError("Selecione ao menos um ambulante para a rota.")

    ambulantes = list(
        Ambulante.objects.filter(pk__in=ids, ativo=True).select_related(
            "ponto_pretendido"
        )
    )
    por_id = {a.pk: a for a in ambulantes}
    ordenados = [por_id[i] for i in ids if i in por_id]
    if not ordenados:
        raise ValueError("Nenhum ambulante válido encontrado.")

    rota = RotaFiscal.objects.create(
        titulo=(titulo or "").strip() or f"Rota — {fiscal.nome}",
        fiscal=fiscal,
        criado_por=criado_por,
        status=StatusRota.AGENDADA,
        data_prevista=data_prevista,
        observacoes_gestor=(observacoes or "").strip(),
    )
    for ordem, ambulante in enumerate(ordenados, start=1):
        ParadaRota.objects.create(
            rota=rota,
            ordem=ordem,
            ambulante=ambulante,
            ponto=_ponto_do_ambulante(ambulante),
            status=StatusParada.PENDENTE,
        )
    return rota


def iniciar_rota(fiscal, rota_id):
    rota = (
        RotaFiscal.objects.select_related("fiscal")
        .prefetch_related("paradas")
        .filter(pk=rota_id, fiscal_id=fiscal.pk)
        .first()
    )
    if rota is None:
        raise ValueError("Rota não encontrada para este fiscal.")
    if rota.status not in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO):
        raise ValueError("Esta rota não pode ser iniciada.")
    if rota.status == StatusRota.AGENDADA:
        rota.status = StatusRota.EM_ANDAMENTO
        rota.iniciada_em = timezone.now()
        rota.save(update_fields=["status", "iniciada_em", "atualizado_em"])
    return rota


@transaction.atomic
def registrar_visita_parada(fiscal, parada_id, dados):
    parada = (
        ParadaRota.objects.select_related("rota", "ambulante", "ponto")
        .filter(pk=parada_id, rota__fiscal_id=fiscal.pk)
        .first()
    )
    if parada is None:
        raise ValueError("Parada não encontrada.")
    if parada.rota.status not in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO):
        raise ValueError("A rota já foi encerrada.")
    if parada.rota.status == StatusRota.AGENDADA:
        iniciar_rota(fiscal, parada.rota_id)

    encontrou = bool(dados.get("encontrou_ambulante"))
    recebido = bool(dados.get("foi_recebido")) if encontrou else False
    observacoes = (dados.get("observacoes") or "").strip()
    ocorrencia = dados.get("ocorrencia")

    visita, _criada = RegistroVisita.objects.update_or_create(
        parada=parada,
        defaults={
            "encontrou_ambulante": encontrou,
            "foi_recebido": recebido,
            "observacoes": observacoes,
            "ocorrencia": ocorrencia,
            "registrado_em": timezone.now(),
        },
    )
    parada.status = StatusParada.CONCLUIDA
    parada.save(update_fields=["status", "atualizado_em"])
    return visita


@transaction.atomic
def concluir_rota(fiscal, rota_id, incompleta=False, relato=""):
    rota = (
        RotaFiscal.objects.prefetch_related("paradas")
        .filter(pk=rota_id, fiscal_id=fiscal.pk)
        .first()
    )
    if rota is None:
        raise ValueError("Rota não encontrada para este fiscal.")
    if rota.status in (StatusRota.CONCLUIDA, StatusRota.INCOMPLETA):
        raise ValueError("Esta rota já foi encerrada.")

    pendentes = rota.paradas.filter(status=StatusParada.PENDENTE)
    if incompleta or pendentes.exists():
        pendentes.update(status=StatusParada.PULADA)
        rota.status = StatusRota.INCOMPLETA
        rota.relato_incompleta = (relato or "").strip()
    else:
        rota.status = StatusRota.CONCLUIDA
        rota.relato_incompleta = ""

    if rota.iniciada_em is None:
        rota.iniciada_em = timezone.now()
    rota.concluida_em = timezone.now()
    rota.save(
        update_fields=[
            "status",
            "relato_incompleta",
            "iniciada_em",
            "concluida_em",
            "atualizado_em",
        ]
    )
    return rota


def vincular_ocorrencia_a_parada(parada_id, ocorrencia, fiscal):
    """Associa ocorrência já criada a uma parada (retorno do formulário de ocorrência)."""
    parada = (
        ParadaRota.objects.select_related("rota")
        .filter(pk=parada_id, rota__fiscal_id=fiscal.pk)
        .first()
    )
    if parada is None:
        raise ValueError("Parada não encontrada.")
    visita, _ = RegistroVisita.objects.get_or_create(
        parada=parada,
        defaults={
            "encontrou_ambulante": True,
            "foi_recebido": True,
            "observacoes": "Visita com ocorrência registrada.",
            "registrado_em": timezone.now(),
        },
    )
    visita.ocorrencia = ocorrencia
    visita.save(update_fields=["ocorrencia", "atualizado_em"])
    if parada.status == StatusParada.PENDENTE:
        parada.status = StatusParada.CONCLUIDA
        parada.save(update_fields=["status", "atualizado_em"])
    return visita


def resumir_rota(rota):
    paradas = list(
        rota.paradas.select_related("ambulante", "ponto").prefetch_related("visita")
    )
    concluidas = [p for p in paradas if p.status == StatusParada.CONCLUIDA]
    puladas = [p for p in paradas if p.status == StatusParada.PULADA]
    sem_ambulante = [
        p
        for p in concluidas
        if hasattr(p, "visita")
        and p.visita
        and not p.visita.encontrou_ambulante
    ]
    com_ocorrencia = [
        p
        for p in concluidas
        if hasattr(p, "visita") and p.visita and p.visita.ocorrencia_id
    ]
    return {
        "id": rota.pk,
        "titulo": rota.titulo,
        "status": rota.status,
        "status_display": rota.get_status_display(),
        "fiscal": rota.fiscal.nome_completo,
        "fiscal_id": rota.fiscal_id,
        "data_prevista": rota.data_prevista.isoformat() if rota.data_prevista else None,
        "iniciada_em": rota.iniciada_em.isoformat() if rota.iniciada_em else None,
        "concluida_em": rota.concluida_em.isoformat() if rota.concluida_em else None,
        "total_paradas": len(paradas),
        "paradas_concluidas": len(concluidas),
        "paradas_puladas": len(puladas),
        "sem_ambulante": len(sem_ambulante),
        "com_ocorrencia": len(com_ocorrencia),
        "relato_incompleta": rota.relato_incompleta,
        "pontos_sem_ambulante": [
            (p.ponto.nome_identificacao if p.ponto else p.ambulante.nome_completo)
            for p in sem_ambulante
        ],
    }


def resumo_rotas_agregado(limite=10):
    hoje = timezone.localdate()
    qs = RotaFiscal.objects.select_related("fiscal").prefetch_related(
        "paradas__visita", "paradas__ponto", "paradas__ambulante"
    )
    recentes = list(
        qs.filter(
            status__in=(StatusRota.CONCLUIDA, StatusRota.INCOMPLETA)
        ).order_by("-concluida_em", "-criado_em")[:limite]
    )
    resumos = [resumir_rota(r) for r in recentes]
    concluidas_hoje = qs.filter(
        status__in=(StatusRota.CONCLUIDA, StatusRota.INCOMPLETA),
        concluida_em__date=hoje,
    ).count()
    em_andamento = qs.filter(status=StatusRota.EM_ANDAMENTO).count()
    agendadas = qs.filter(status=StatusRota.AGENDADA).count()
    sem_ambulante = sum(r["sem_ambulante"] for r in resumos)
    ocorrencias = sum(r["com_ocorrencia"] for r in resumos)
    pontos = []
    for r in resumos:
        pontos.extend(r.get("pontos_sem_ambulante") or [])
    return {
        "concluidas_hoje": concluidas_hoje,
        "em_andamento": em_andamento,
        "agendadas": agendadas,
        "sem_ambulante": sem_ambulante,
        "ocorrencias_em_rotas": ocorrencias,
        "pontos_sem_ambulante": pontos[:8],
        "rotas": resumos,
    }


def sugerir_ambulantes_rota_mock(limite=4):
    """Mock do copiloto: ambulantes com licença ativa e ponto georreferenciado."""
    licencas = (
        LicencaAlvara.objects.filter(
            status=StatusLicenca.ATIVO,
            ponto_ocupacao__isnull=False,
            ambulante__ativo=True,
        )
        .select_related("ambulante", "ponto_ocupacao")
        .order_by("ponto_ocupacao__bairro", "ambulante__nome")[:limite]
    )
    sugeridos = []
    for licenca in licencas:
        ponto = licenca.ponto_ocupacao
        sugeridos.append(
            {
                "ambulante_id": licenca.ambulante_id,
                "nome": licenca.ambulante.nome_completo,
                "apelido": licenca.ambulante.apelido_nome_fantasia or "",
                "ponto": ponto.nome_identificacao if ponto else "",
                "bairro": ponto.bairro if ponto else "",
                "coordenadas": (ponto.coordenadas if ponto else "") or "",
                "numero_licenca": licenca.numero_licenca or "",
                "motivo": f"Licença ativa em {ponto.bairro if ponto else 'ponto cadastrado'}",
            }
        )
    if len(sugeridos) < limite:
        extras = (
            Ambulante.objects.filter(ativo=True, ponto_pretendido__isnull=False)
            .exclude(pk__in=[s["ambulante_id"] for s in sugeridos])
            .select_related("ponto_pretendido")[: limite - len(sugeridos)]
        )
        for ambulante in extras:
            ponto = ambulante.ponto_pretendido
            sugeridos.append(
                {
                    "ambulante_id": ambulante.pk,
                    "nome": ambulante.nome_completo,
                    "apelido": ambulante.apelido_nome_fantasia or "",
                    "ponto": ponto.nome_identificacao if ponto else "",
                    "bairro": ponto.bairro if ponto else "",
                    "coordenadas": (ponto.coordenadas if ponto else "") or "",
                    "numero_licenca": "",
                    "motivo": "Ponto pretendido cadastrado (sem alvará ativo)",
                }
            )
    return sugeridos


def proxima_parada(rota):
    """Primeira parada ainda pendente, na ordem da rota."""
    return (
        rota.paradas.filter(status=StatusParada.PENDENTE)
        .select_related("ambulante", "ponto")
        .order_by("ordem", "pk")
        .first()
    )


def paradas_para_mapa(rota):
    itens = []
    for parada in rota.paradas.select_related("ambulante", "ponto").all():
        coords = parada.coordenadas_lat_lng
        itens.append(
            {
                "id": parada.pk,
                "ordem": parada.ordem,
                "status": parada.status,
                "ambulante": parada.ambulante.nome_completo,
                "ponto": parada.ponto.nome_identificacao if parada.ponto else "",
                "bairro": parada.ponto.bairro if parada.ponto else "",
                "endereco": parada.endereco_completo,
                "lat": coords[0] if coords else None,
                "lng": coords[1] if coords else None,
            }
        )
    return itens


def rotas_pendentes_analise():
    return RotaFiscal.objects.filter(
        status__in=(StatusRota.CONCLUIDA, StatusRota.INCOMPLETA)
    ).count()
