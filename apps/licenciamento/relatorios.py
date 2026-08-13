from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.espacos.models import PontoOcupacao, StatusOcupacao
from apps.fiscalizacao.models import OcorrenciaInspecao
from apps.usuarios.models import Ambulante

from .models import STATUS_FILA, LicencaAlvara, StatusLicenca
from .services import marcar_licencas_vencidas

PERIODO_INFRACOES_DIAS = 30
LIMIAR_LOTACAO = 90
CIDADE_SEDE = "Vitória da Conquista"


def _aplicar_origem(qs, origem, campo_ambulante="ambulante"):
    if origem == "residentes":
        return qs.filter(**{f"{campo_ambulante}__tipo_atuacao": "fixo"})
    if origem == "itinerantes":
        return qs.filter(**{f"{campo_ambulante}__tipo_atuacao": "movel"})
    return qs


def _percentual(parte, total):
    if not total:
        return 0.0
    return round((parte / total) * 100, 1)


def indicadores_gerenciais(bairro="", origem="", periodo_dias=PERIODO_INFRACOES_DIAS):
    """Números reais de licença, ocupação, infração e categoria para o dashboard."""
    marcar_licencas_vencidas()
    bairro = (bairro or "").strip()
    origem = (origem or "").strip()
    try:
        periodo_dias = max(1, int(periodo_dias or PERIODO_INFRACOES_DIAS))
    except (TypeError, ValueError):
        periodo_dias = PERIODO_INFRACOES_DIAS

    licencas = LicencaAlvara.objects.all()
    if bairro:
        licencas = licencas.filter(ponto_ocupacao__bairro__iexact=bairro)
    licencas = _aplicar_origem(licencas, origem)

    hoje = timezone.localdate()
    ativas = licencas.filter(status=StatusLicenca.ATIVO)
    vencidas = licencas.filter(status=StatusLicenca.VENCIDO)
    pendentes = licencas.filter(status__in=STATUS_FILA)
    suspensas = licencas.filter(status=StatusLicenca.SUSPENSO)
    vencendo = ativas.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + timedelta(days=30),
    )

    pontos = PontoOcupacao.objects.filter(ativo=True)
    if bairro:
        pontos = pontos.filter(bairro__iexact=bairro)
    ocupacao_qs = (
        pontos.values("bairro")
        .annotate(
            total=Count("id"),
            ocupados=Count("id", filter=Q(status_ocupacao=StatusOcupacao.OCUPADO)),
            livres=Count("id", filter=Q(status_ocupacao=StatusOcupacao.LIVRE)),
        )
        .order_by("bairro")
    )
    ativas_por_bairro = {
        row["ponto_ocupacao__bairro"]: row["total"]
        for row in ativas.filter(ponto_ocupacao__isnull=False)
        .values("ponto_ocupacao__bairro")
        .annotate(total=Count("id"))
        if row["ponto_ocupacao__bairro"]
    }
    ocupacao = []
    alerta_lotacao = None
    for row in ocupacao_qs:
        nome = row["bairro"] or "Não informado"
        total = row["total"]
        ocupados = row["ocupados"]
        percentual = _percentual(ocupados, total)
        item = {
            "bairro": nome,
            "total": total,
            "ocupados": ocupados,
            "livres": row["livres"],
            "percentual": percentual,
            "licencas_ativas": ativas_por_bairro.get(row["bairro"], 0),
        }
        ocupacao.append(item)
        if percentual >= LIMIAR_LOTACAO and alerta_lotacao is None:
            alerta_lotacao = item

    categorias = [
        {
            "nome": row["categoria_produto__nome_categoria"] or "Sem categoria",
            "total": row["total"],
        }
        for row in ativas.values("categoria_produto__nome_categoria")
        .annotate(total=Count("id"))
        .order_by("-total", "categoria_produto__nome_categoria")
    ]

    desde = timezone.now() - timedelta(days=periodo_dias)
    ocorrencias = OcorrenciaInspecao.objects.filter(criado_em__gte=desde)
    if bairro:
        ocorrencias = ocorrencias.filter(
            Q(local_ocorrencia__icontains=bairro)
            | Q(ambulante__licencas__ponto_ocupacao__bairro__iexact=bairro)
        ).distinct()
    ocorrencias = _aplicar_origem(ocorrencias, origem)

    ambulantes = Ambulante.objects.all()
    if bairro:
        ambulantes = ambulantes.filter(
            Q(licencas__ponto_ocupacao__bairro__iexact=bairro)
            | Q(ponto_pretendido__bairro__iexact=bairro)
        ).distinct()
    residentes = ambulantes.filter(tipo_atuacao="fixo").count()
    itinerantes = ambulantes.filter(tipo_atuacao="movel").count()

    bairros = list(
        PontoOcupacao.objects.filter(ativo=True)
        .exclude(bairro="")
        .order_by("bairro")
        .values_list("bairro", flat=True)
        .distinct()
    )

    return {
        "filtro_bairro": bairro,
        "filtro_origem": origem,
        "periodo_dias": periodo_dias,
        "bairros": bairros,
        "licencas_ativas": ativas.count(),
        "licencas_vencidas": vencidas.count(),
        "licencas_pendentes": pendentes.count(),
        "licencas_suspensas": suspensas.count(),
        "licencas_vencendo": vencendo.count(),
        "ocorrencias_periodo": ocorrencias.count(),
        "residentes": residentes,
        "itinerantes": itinerantes,
        "ocupacao": ocupacao,
        "categorias": categorias,
        "alerta_lotacao": alerta_lotacao,
        "cidade_sede": CIDADE_SEDE,
    }


def indicadores_json(dados):
    """Recorte serializável para a API JSON (sem queryset)."""
    return {
        "filtros": {
            "bairro": dados["filtro_bairro"],
            "origem": dados["filtro_origem"] or "todos",
            "periodo_dias": dados["periodo_dias"],
        },
        "licencas": {
            "ativas": dados["licencas_ativas"],
            "vencidas": dados["licencas_vencidas"],
            "pendentes": dados["licencas_pendentes"],
            "suspensas": dados["licencas_suspensas"],
            "vencendo_30_dias": dados["licencas_vencendo"],
        },
        "ocorrencias_periodo": dados["ocorrencias_periodo"],
        "residentes": dados["residentes"],
        "itinerantes": dados["itinerantes"],
        "ocupacao": dados["ocupacao"],
        "categorias": dados["categorias"],
    }
