from apps.licenciamento.models import StatusLicenca
from apps.licenciamento.services import licenca_atual

from .models import EventoScore, TipoEventoScore

PONTUACAO_MIN = 0
PONTUACAO_MAX = 100

PONTOS = {
    TipoEventoScore.LICENCA_ATIVA: 10,
    TipoEventoScore.RENOVACAO: 8,
    TipoEventoScore.OCORRENCIA_PROCEDENTE: -20,
    TipoEventoScore.LICENCA_SUSPENSA: -15,
    TipoEventoScore.LICENCA_CANCELADA: -25,
}

FAIXAS = (
    {
        "nome": "Diamante",
        "minimo": 90,
        "descricao": "Ambulante modelo: licença em dia e sem infração procedente.",
        "cor": "#2563EB",
        "fundo": "#EFF6FF",
    },
    {
        "nome": "Ouro",
        "minimo": 75,
        "descricao": "Bom histórico de pagamentos e poucas pendências.",
        "cor": "#D97706",
        "fundo": "#FEF3C7",
    },
    {
        "nome": "Prata",
        "minimo": 50,
        "descricao": "Cadastro em dia, com espaço para regularizar infrações.",
        "cor": "#4B5563",
        "fundo": "#F3F4F6",
    },
    {
        "nome": "Bronze",
        "minimo": 0,
        "descricao": "Iniciante ou com pendências de licença/ocorrência.",
        "cor": "#92400E",
        "fundo": "#FFF8F0",
    },
)


def faixas_exibicao():
    teto = PONTUACAO_MAX
    resultado = []
    for faixa in FAIXAS:
        resultado.append({**faixa, "maximo": teto})
        teto = faixa["minimo"] - 1
    return resultado


def faixa_score(pontos):
    pontos = max(PONTUACAO_MIN, min(PONTUACAO_MAX, int(pontos or 0)))
    atual = FAIXAS[-1]
    for faixa in FAIXAS:
        if pontos >= faixa["minimo"]:
            atual = faixa
            break
    proxima = None
    for faixa in reversed(FAIXAS):
        if faixa["minimo"] > atual["minimo"]:
            proxima = faixa
            break
    faltam = (proxima["minimo"] - pontos) if proxima else 0
    return {
        **atual,
        "pontos": pontos,
        "proxima": proxima["nome"] if proxima else None,
        "faltam": max(0, faltam),
        "percentual": pontos,
    }


def registrar_evento_score(ambulante, tipo, descricao, chave=""):
    """Aplica o delta da regra, grava histórico e devolve o evento (ou None se repetido)."""
    if ambulante is None:
        return None
    chave = (chave or "").strip()
    if chave and EventoScore.objects.filter(ambulante=ambulante, chave=chave).exists():
        return None
    delta = PONTOS[tipo]
    atual = ambulante.pontuacao
    novo = max(PONTUACAO_MIN, min(PONTUACAO_MAX, atual + delta))
    aplicado = novo - atual
    evento = EventoScore.objects.create(
        ambulante=ambulante,
        tipo=tipo,
        pontos=aplicado,
        saldo_apos=novo,
        descricao=descricao,
        chave=chave,
    )
    if aplicado:
        ambulante.pontuacao = novo
        ambulante.save(update_fields=["pontuacao", "atualizado_em"])
    return evento


def pontuar_licenca_ativa(ambulante, licenca):
    return registrar_evento_score(
        ambulante,
        TipoEventoScore.LICENCA_ATIVA,
        f"Alvará {licenca.numero_licenca} emitido e licença ativa.",
        chave=f"licenca_ativa:{licenca.pk}",
    )


def pontuar_renovacao(ambulante, licenca):
    return registrar_evento_score(
        ambulante,
        TipoEventoScore.RENOVACAO,
        f"Renovação aberta no prazo (protocolo {licenca.protocolo}).",
        chave=f"renovacao:{licenca.pk}",
    )


def pontuar_ocorrencia_procedente(ambulante, ocorrencia):
    return registrar_evento_score(
        ambulante,
        TipoEventoScore.OCORRENCIA_PROCEDENTE,
        f"Ocorrência #{ocorrencia.pk} marcada como procedente ({ocorrencia.tipo_ocorrencia}).",
        chave=f"ocorrencia_procedente:{ocorrencia.pk}",
    )


def pontuar_licenca_suspensa(ambulante):
    return registrar_evento_score(
        ambulante,
        TipoEventoScore.LICENCA_SUSPENSA,
        "Licença ou conta suspensa pela gestão.",
        chave=f"suspensa:{ambulante.pk}:{ambulante.pontuacao}",
    )


def pontuar_licenca_cancelada(ambulante):
    return registrar_evento_score(
        ambulante,
        TipoEventoScore.LICENCA_CANCELADA,
        "Licença ou conta cancelada pela gestão.",
        chave=f"cancelada:{ambulante.pk}:{ambulante.pontuacao}",
    )


def dicas_regularizacao(ambulante):
    dicas = []
    licenca = licenca_atual(ambulante) if ambulante else None
    if licenca is None:
        dicas.append(
            "Complete o cadastro e acompanhe o alvará para somar pontos de licença em dia."
        )
    elif licenca.status == StatusLicenca.SUSPENSO:
        dicas.append(
            "A licença está suspensa. Regularize a ocorrência no dossiê da prefeitura."
        )
    elif licenca.status == StatusLicenca.VENCIDO:
        dicas.append("Renove o alvará no prazo para recuperar pontos de renovação.")
    elif licenca.status == StatusLicenca.CANCELADO:
        dicas.append(
            "A licença foi cancelada. Abra um novo requerimento após a orientação da gestão."
        )
    elif licenca.status == StatusLicenca.ATIVO:
        dicas.append(
            "Mantenha a credencial visível e evite infrações de ponto e horário."
        )
    if ambulante and ambulante.pontuacao < 75:
        dicas.append("Evite novas autuações: ocorrência procedente reduz o score.")
    return dicas


def resumo_score(ambulante):
    pontos = ambulante.pontuacao if ambulante else 0
    return {
        "pontuacao": pontos,
        "maximo": PONTUACAO_MAX,
        "faixa": faixa_score(pontos),
        "faixas": faixas_exibicao(),
        "eventos": (
            ambulante.eventos_score.order_by("-criado_em")[:20] if ambulante else []
        ),
        "dicas": dicas_regularizacao(ambulante),
        "regras": [
            {
                "rotulo": "Licença ativa / alvará emitido",
                "pontos": PONTOS[TipoEventoScore.LICENCA_ATIVA],
            },
            {
                "rotulo": "Renovação no prazo",
                "pontos": PONTOS[TipoEventoScore.RENOVACAO],
            },
            {
                "rotulo": "Ocorrência procedente",
                "pontos": PONTOS[TipoEventoScore.OCORRENCIA_PROCEDENTE],
            },
            {
                "rotulo": "Licença suspensa",
                "pontos": PONTOS[TipoEventoScore.LICENCA_SUSPENSA],
            },
            {
                "rotulo": "Licença cancelada",
                "pontos": PONTOS[TipoEventoScore.LICENCA_CANCELADA],
            },
        ],
    }


def processar_ocorrencia(ocorrencia_id):
    try:
        from apps.fiscalizacao.models import OcorrenciaInspecao

        ocorrencia = OcorrenciaInspecao.objects.select_related(
            "infracao", "ambulante"
        ).get(id=ocorrencia_id)

        if (
            ocorrencia.status_gestor == "APROVADA"
            and ocorrencia.infracao
            and ocorrencia.ambulante
        ):
            ambulante = ocorrencia.ambulante
            novo_score = ambulante.pontuacao - ocorrencia.infracao.pontos_desconto

            ambulante.pontuacao = max(0, novo_score)
            ambulante.save(update_fields=["pontuacao"])

    except Exception as e:  # noqa: BLE001
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao processar ocorrência no score: {e}")


def verificar_recuperacao_mensal():
    from datetime import timedelta

    from django.utils import timezone

    from apps.fiscalizacao.models import OcorrenciaInspecao
    from apps.usuarios.models import Ambulante, ConfiguracaoSeguranca

    config = ConfiguracaoSeguranca.carregar()
    dias = config.dias_recuperacao_score
    limite_dias = timezone.now() - timedelta(days=dias)

    ambulantes_elegiveis = Ambulante.objects.filter(pontuacao__lt=100)
    afetados = 0

    for ambulante in ambulantes_elegiveis:
        teve_ocorrencia_recente = OcorrenciaInspecao.objects.filter(
            ambulante=ambulante, status_gestor="APROVADA", criado_em__gte=limite_dias
        ).exists()

        if not teve_ocorrencia_recente:
            ambulante.pontuacao = min(100, ambulante.pontuacao + 2)
            ambulante.save(update_fields=["pontuacao"])
            afetados += 1

    return afetados
