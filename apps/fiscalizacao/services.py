import hmac
from dataclasses import dataclass, field

from django.db.models import Q
from django.utils import timezone

from apps.core.qrcode import gerar_codigo_qr
from apps.licenciamento.models import LicencaAlvara, StatusLicenca
from apps.licenciamento.services import marcar_licencas_vencidas
from apps.usuarios.forms import normalizar_cpf
from apps.usuarios.models import Ambulante, Fiscal

from .models import (
    TIPO_POR_MOTIVO,
    OcorrenciaInspecao,
    StatusOcorrencia,
    TipoOcorrencia,
)

DIAS_SEMANA_ORDEM = (
    "segunda",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sabado",
    "domingo",
)


@dataclass
class ResultadoInspecao:
    valido: bool = False
    motivo: str = ""
    mensagem: str = ""
    licenca: LicencaAlvara | None = None
    ambulante: Ambulante | None = None
    fora_horario: bool = False
    candidatos: list = field(default_factory=list)

    @property
    def tipo_sugerido(self):
        return TIPO_POR_MOTIVO.get(self.motivo, TipoOcorrencia.OUTRO)


def esta_fora_do_horario(licenca, momento=None):
    """True se há escala e o instante atual não está nela."""
    escalas = list(licenca.escalas.all())
    if not escalas:
        return False
    momento = timezone.localtime(momento) if momento else timezone.localtime()
    dia = DIAS_SEMANA_ORDEM[momento.weekday()]
    hora = momento.time()
    for escala in escalas:
        if escala.dia_semana != dia:
            continue
        if escala.horario_inicio <= hora <= escala.horario_termino:
            return False
    return True


def _ficha_da_licenca(licenca, motivo_ok="ok", mensagem="Credencial válida."):
    marcar_licencas_vencidas()
    licenca.refresh_from_db()
    ambulante = licenca.ambulante
    if licenca.status == StatusLicenca.SUSPENSO:
        return ResultadoInspecao(
            motivo="suspenso",
            mensagem="Licença suspensa. O QR Code não é aceito.",
            licenca=licenca,
            ambulante=ambulante,
        )
    if licenca.status == StatusLicenca.VENCIDO or not licenca.qr_valido:
        if licenca.status == StatusLicenca.VENCIDO or (
            licenca.data_vencimento and licenca.data_vencimento < timezone.localdate()
        ):
            return ResultadoInspecao(
                motivo="vencido",
                mensagem="Licença vencida. O QR Code não é aceito.",
                licenca=licenca,
                ambulante=ambulante,
            )
        return ResultadoInspecao(
            motivo="invalido",
            mensagem=f"Licença com status {licenca.status}. QR Code não é aceito.",
            licenca=licenca,
            ambulante=ambulante,
        )
    if esta_fora_do_horario(licenca):
        return ResultadoInspecao(
            motivo="fora_horario",
            mensagem="Licença ativa, mas fora do horário autorizado na escala.",
            licenca=licenca,
            ambulante=ambulante,
            fora_horario=True,
        )
    return ResultadoInspecao(
        valido=True,
        motivo=motivo_ok,
        mensagem=mensagem,
        licenca=licenca,
        ambulante=ambulante,
    )


def inspecionar_qr(codigo):
    """Classifica o QR: válido, vencido, suspenso, fora do horário ou adulterado."""
    codigo = (codigo or "").strip()
    if not codigo:
        return ResultadoInspecao(
            motivo="vazio",
            mensagem="Informe o código do QR Code.",
        )

    marcar_licencas_vencidas()
    ambulante = Ambulante.objects.filter(codigo_qr_code=codigo).first()
    if ambulante is None:
        return ResultadoInspecao(
            motivo="adulterado",
            mensagem="QR Code inválido ou adulterado.",
        )

    licencas = list(
        ambulante.licencas.select_related(
            "ponto_ocupacao",
            "categoria_produto",
            "estrutura_trabalho",
        )
        .prefetch_related("escalas")
        .order_by("-data_emissao", "-pk")
    )
    correspondente = None
    for candidata in licencas:
        gerado = gerar_codigo_qr(candidata)
        if len(gerado) == len(codigo) and hmac.compare_digest(gerado, codigo):
            correspondente = candidata
            break
    if correspondente is None:
        return ResultadoInspecao(
            motivo="adulterado",
            mensagem="QR Code inválido ou adulterado.",
            ambulante=ambulante,
        )
    return _ficha_da_licenca(correspondente)


def consultar_campo(termo):
    """Busca por QR, CPF, nome ou número do alvará."""
    termo = (termo or "").strip()
    if not termo:
        return ResultadoInspecao(
            motivo="vazio",
            mensagem="Informe CPF, nome, número do alvará ou o código do QR.",
        )

    if len(termo) >= 32:
        return inspecionar_qr(termo)

    licenca = (
        LicencaAlvara.objects.filter(numero_licenca__iexact=termo)
        .select_related(
            "ambulante",
            "ponto_ocupacao",
            "categoria_produto",
            "estrutura_trabalho",
        )
        .prefetch_related("escalas")
        .first()
    )
    if licenca is None and termo.upper().startswith("ALV"):
        licenca = (
            LicencaAlvara.objects.filter(numero_licenca__icontains=termo)
            .select_related(
                "ambulante",
                "ponto_ocupacao",
                "categoria_produto",
                "estrutura_trabalho",
            )
            .prefetch_related("escalas")
            .first()
        )
    if licenca:
        return _ficha_da_licenca(
            licenca,
            motivo_ok="ok",
            mensagem="Ficha localizada pela busca manual.",
        )

    cpf = normalizar_cpf(termo)
    candidatos = []
    if len(cpf) == 11:
        encontrados = Ambulante.objects.filter(cpf=cpf)
    else:
        encontrados = Ambulante.objects.filter(
            Q(nome__icontains=termo)
            | Q(sobrenome__icontains=termo)
            | Q(apelido_nome_fantasia__icontains=termo)
        )
    candidatos = list(encontrados.order_by("nome", "sobrenome")[:8])
    if not candidatos:
        return ResultadoInspecao(
            motivo="nao_encontrado",
            mensagem="Nenhum ambulante ou alvará encontrado para essa busca.",
        )
    if len(candidatos) > 1:
        return ResultadoInspecao(
            motivo="varios",
            mensagem="Vários cadastros encontrados. Selecione o ambulante.",
            candidatos=candidatos,
        )

    ambulante = candidatos[0]
    licenca = (
        ambulante.licencas.select_related(
            "ponto_ocupacao",
            "categoria_produto",
            "estrutura_trabalho",
        )
        .prefetch_related("escalas")
        .order_by("-data_emissao", "-pk")
        .first()
    )
    if licenca is None:
        return ResultadoInspecao(
            motivo="sem_licenca",
            mensagem="Ambulante localizado, mas sem licença emitida.",
            ambulante=ambulante,
        )
    return _ficha_da_licenca(
        licenca,
        motivo_ok="ok",
        mensagem="Ficha localizada pela busca manual.",
    )


def tipo_sugerido_para(motivo):
    return TIPO_POR_MOTIVO.get(motivo, TipoOcorrencia.OUTRO)


def registrar_ocorrencia(
    fiscal_user,
    ambulante,
    tipo_ocorrencia,
    descricao,
    local_ocorrencia="",
    evidencia_foto=None,
    infracao=None,
    data_ocorrencia=None,
):
    fiscal = Fiscal.objects.filter(pk=fiscal_user.pk).first()
    if fiscal is None:
        raise ValueError("O usuário logado não é um fiscal.")
    ocorrencia = OcorrenciaInspecao(
        fiscal=fiscal,
        ambulante=ambulante,
        tipo_ocorrencia=tipo_ocorrencia,
        descricao=descricao,
        local_ocorrencia=local_ocorrencia or "",
        status_ocorrencia=StatusOcorrencia.REGISTRADA,
        infracao=infracao,
        data_ocorrencia=data_ocorrencia or timezone.now(),
    )
    if evidencia_foto:
        ocorrencia.evidencia_foto = evidencia_foto
    ocorrencia.save()
    return ocorrencia


TRANSICOES_STATUS = {
    StatusOcorrencia.REGISTRADA: frozenset(
        {
            StatusOcorrencia.EM_ANALISE,
            StatusOcorrencia.PROCEDENTE,
            StatusOcorrencia.IMPROCEDENTE,
        }
    ),
    StatusOcorrencia.EM_ANALISE: frozenset(
        {
            StatusOcorrencia.PROCEDENTE,
            StatusOcorrencia.IMPROCEDENTE,
        }
    ),
    StatusOcorrencia.PROCEDENTE: frozenset({StatusOcorrencia.CONVERTIDA_MULTA}),
}

STATUS_QUE_AFETAM_LICENCA = frozenset(
    {
        StatusOcorrencia.PROCEDENTE,
        StatusOcorrencia.CONVERTIDA_MULTA,
    }
)


def filtrar_ocorrencias(q="", status="", tipo=""):
    qs = OcorrenciaInspecao.objects.select_related("fiscal", "ambulante").order_by(
        "-criado_em"
    )
    termo = (q or "").strip()
    if termo:
        cpf = normalizar_cpf(termo)
        filtros = (
            Q(fiscal__nome__icontains=termo)
            | Q(fiscal__sobrenome__icontains=termo)
            | Q(ambulante__nome__icontains=termo)
            | Q(ambulante__sobrenome__icontains=termo)
            | Q(ambulante__apelido_nome_fantasia__icontains=termo)
            | Q(local_ocorrencia__icontains=termo)
            | Q(tipo_ocorrencia__icontains=termo)
            | Q(descricao__icontains=termo)
        )
        if len(cpf) >= 3:
            filtros |= Q(ambulante__cpf__icontains=cpf)
        qs = qs.filter(filtros)
    if status in StatusOcorrencia.values:
        qs = qs.filter(status_ocorrencia=status)
    if tipo in TipoOcorrencia.values:
        qs = qs.filter(tipo_ocorrencia=tipo)
    return qs


def transicoes_permitidas(status_atual):
    return tuple(sorted(TRANSICOES_STATUS.get(status_atual, frozenset())))


def aplicar_efeito_licenca(ambulante, acao):
    if ambulante is None:
        return None
    if acao == "suspender":
        afetadas = ambulante.licencas.filter(status=StatusLicenca.ATIVO).update(
            status=StatusLicenca.SUSPENSO
        )
        if afetadas:
            from apps.usuarios.score import pontuar_licenca_suspensa

            pontuar_licenca_suspensa(ambulante)
        return "suspenso" if afetadas else None
    if acao == "cancelar":
        afetadas = ambulante.licencas.exclude(
            status__in=(StatusLicenca.CANCELADO, StatusLicenca.INDEFERIDO)
        ).update(status=StatusLicenca.CANCELADO)
        if afetadas:
            from apps.usuarios.score import pontuar_licenca_cancelada

            pontuar_licenca_cancelada(ambulante)
        return "cancelado" if afetadas else None
    raise ValueError("Ação sobre a licença inválida.")


def auditar_ocorrencia(ocorrencia, novo_status, infracao=None):
    """Atualiza o auto e aciona o novo fluxo de gamificação se procedente."""
    atual = ocorrencia.status_ocorrencia
    destino = (novo_status or atual).strip() or atual
    mudou_status = destino != atual

    if mudou_status:
        if destino not in transicoes_permitidas(atual):
            raise ValueError(f"Não é possível mudar de {atual} para {destino}.")
        ocorrencia.status_ocorrencia = destino

    if infracao:
        ocorrencia.infracao = infracao

    if destino == StatusOcorrencia.PROCEDENTE:
        ocorrencia.status_gestor = "APROVADA"
    elif destino == StatusOcorrencia.IMPROCEDENTE:
        ocorrencia.status_gestor = "REJEITADA"
    else:
        ocorrencia.status_gestor = "PENDENTE"

    ocorrencia.save(
        update_fields=[
            "status_ocorrencia",
            "status_gestor",
            "infracao",
            "atualizado_em",
        ]
    )

    if mudou_status and destino == StatusOcorrencia.PROCEDENTE:
        from apps.usuarios.score import processar_ocorrencia

        processar_ocorrencia(ocorrencia.id)

    return ocorrencia, None
