from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.licenciamento.models import (
    STATUS_FILA,
    TIPOS_BASICOS_OBRIGATORIOS,
    StatusAprovacaoDocumento,
    StatusLicenca,
    TipoDocumento,
)
from apps.usuarios.models import Gestor

CHAVE_CATEGORIA = "categoria_id"


def categoria_do_ambulante(ambulante):
    """Categoria pretendida no cadastro ou a da solicitação mais recente."""
    from apps.licenciamento.models import CategoriaProduto, LicencaAlvara

    extras = ambulante.dados_complementares or {}
    categoria_id = extras.get(CHAVE_CATEGORIA)
    if categoria_id:
        categoria = CategoriaProduto.objects.filter(pk=categoria_id).first()
        if categoria:
            return categoria

    licenca = (
        LicencaAlvara.objects.filter(ambulante=ambulante)
        .select_related("categoria_produto")
        .order_by("-id")
        .first()
    )
    if licenca:
        return licenca.categoria_produto
    return None


def gravar_categoria_pretendida(ambulante, categoria):
    extras = dict(ambulante.dados_complementares or {})
    if categoria is None:
        extras.pop(CHAVE_CATEGORIA, None)
        extras.pop("categoria_nome", None)
    else:
        extras[CHAVE_CATEGORIA] = categoria.pk
        extras["categoria_nome"] = categoria.nome_categoria
    ambulante.dados_complementares = extras
    ambulante.save(update_fields=["dados_complementares", "atualizado_em"])


def tipos_obrigatorios(ambulante, categoria=None):
    """Tipos que precisam existir (e, para avanço, estar aprovados)."""
    categoria = categoria or categoria_do_ambulante(ambulante)
    tipos = list(TIPOS_BASICOS_OBRIGATORIOS)
    if ambulante.cnpj:
        tipos.append(TipoDocumento.MEI)
    if categoria and categoria.exige_laudo_sanitario:
        tipos.append(TipoDocumento.LAUDO_SANITARIO)
    if categoria and categoria.exige_laudo_bombeiros:
        tipos.append(TipoDocumento.LAUDO_BOMBEIROS)
    return tipos


def documento_atual(ambulante, tipo):
    return ambulante.documentos.filter(tipo_documento=tipo).first()


def tipos_faltando_envio(ambulante, categoria=None):
    """Tipos sem arquivo válido (ausente ou rejeitado)."""
    faltando = []
    for tipo in tipos_obrigatorios(ambulante, categoria):
        doc = documento_atual(ambulante, tipo)
        if doc is None or doc.rejeitado:
            faltando.append(tipo)
    return faltando


def tipos_faltando_aprovacao(ambulante, categoria=None):
    """Tipos que ainda não estão aprovados — bloqueiam o avanço da solicitação."""
    faltando = []
    for tipo in tipos_obrigatorios(ambulante, categoria):
        doc = documento_atual(ambulante, tipo)
        if doc is None or not doc.aprovado:
            faltando.append(tipo)
    return faltando


def pode_avancar_solicitacao(ambulante, categoria=None):
    return not tipos_faltando_aprovacao(ambulante, categoria)


def registrar_documento(ambulante, tipo, arquivo, data_validade=None):
    from apps.licenciamento.models import DocumentoAnexo

    existente = documento_atual(ambulante, tipo)
    if existente is None:
        return DocumentoAnexo.objects.create(
            ambulante=ambulante,
            tipo_documento=tipo,
            arquivo=arquivo,
            data_validade=data_validade,
            status_aprovacao=StatusAprovacaoDocumento.PENDENTE,
        )
    return existente.reenviar(arquivo, data_validade=data_validade)


def marcar_pendencia_documental(ambulante):
    ambulante.licencas.filter(status=StatusLicenca.EM_ANALISE).update(
        status=StatusLicenca.PENDENCIA_DOCUMENTAL
    )


def reabrir_analise_se_sem_rejeicoes(ambulante):
    if ambulante.documentos.filter(
        status_aprovacao=StatusAprovacaoDocumento.REJEITADO
    ).exists():
        return
    ambulante.licencas.filter(status=StatusLicenca.PENDENCIA_DOCUMENTAL).update(
        status=StatusLicenca.EM_ANALISE
    )


def requerimento_em_aberto(ambulante):
    from apps.licenciamento.models import LicencaAlvara

    return (
        LicencaAlvara.objects.filter(ambulante=ambulante, status__in=STATUS_FILA)
        .order_by("-criado_em")
        .first()
    )


@transaction.atomic
def abrir_requerimento(ambulante, categoria=None):
    """Cria (ou reaproveita) um requerimento Em Análise para o ambulante."""
    from apps.licenciamento.models import LicencaAlvara

    existente = requerimento_em_aberto(ambulante)
    if existente:
        return existente, False
    if not ambulante.cadastro_completo:
        return None, False

    estrutura = ambulante.estruturas.order_by("id").first()
    if estrutura is None:
        return None, False

    categoria = categoria or categoria_do_ambulante(ambulante)
    licenca = LicencaAlvara.objects.create(
        ambulante=ambulante,
        estrutura_trabalho=estrutura,
        ponto_ocupacao=ambulante.ponto_pretendido,
        categoria_produto=categoria,
        status=StatusLicenca.EM_ANALISE,
    )
    return licenca, True


def _gestor_do_usuario(usuario):
    return Gestor.objects.filter(pk=usuario.pk).first()


@transaction.atomic
def aplicar_parecer(licenca, gestor, acao, motivo="", categoria=None, ponto=None):
    if licenca.status not in STATUS_FILA:
        raise ValidationError("Este requerimento já saiu da fila de análise.")

    if ponto is not None:
        if (
            ponto.pk != licenca.ponto_ocupacao_id
            and not ponto.disponivel_para_nova_atribuicao()
        ):
            raise ValidationError("Este ponto não está livre para nova ocupação.")
        licenca.ponto_ocupacao = ponto
    if categoria is not None:
        licenca.categoria_produto = categoria
    if licenca.estrutura_trabalho is None:
        licenca.estrutura_trabalho = licenca.ambulante.estruturas.order_by("id").first()

    justificativa = (motivo or "").strip()
    licenca.motivo_parecer = justificativa
    licenca.gestor_responsavel = _gestor_do_usuario(gestor)

    if acao == "indeferir":
        if not justificativa:
            raise ValidationError("Informe o motivo do indeferimento.")
        licenca.status = StatusLicenca.INDEFERIDO
        licenca.save()
        return licenca

    if acao == "pendencia":
        if not justificativa:
            raise ValidationError(
                "Informe a pendência documental para devolver o processo."
            )
        licenca.status = StatusLicenca.PENDENCIA_DOCUMENTAL
        licenca.save()
        return licenca

    if acao != "deferir":
        raise ValidationError("Ação de parecer inválida.")

    if not pode_avancar_solicitacao(licenca.ambulante, licenca.categoria_produto):
        faltando = tipos_faltando_aprovacao(
            licenca.ambulante, licenca.categoria_produto
        )
        nomes = ", ".join(str(TipoDocumento(t).label) for t in faltando)
        raise ValidationError(
            "Não é possível avançar a solicitação até os documentos "
            f"obrigatórios estarem aprovados: {nomes}."
        )

    estrutura = licenca.estrutura_trabalho
    ponto_atual = licenca.ponto_ocupacao
    if ponto_atual is None:
        raise ValidationError("Selecione um ponto de ocupação antes de deferir.")
    if not ponto_atual.disponivel_para_nova_atribuicao():
        raise ValidationError("Este ponto não está livre para nova ocupação.")
    if estrutura and not ponto_atual.metragem_compativel(estrutura.dimensoes_metragem):
        raise ValidationError("A metragem da estrutura ultrapassa o máximo deste ponto.")
    if licenca.categoria_produto is None:
        raise ValidationError("Selecione a categoria do produto antes de deferir.")

    licenca.status = StatusLicenca.APROVADO
    if not licenca.motivo_parecer:
        licenca.motivo_parecer = (
            f"Deferido em {timezone.localdate().strftime('%d/%m/%Y')} "
            "e encaminhado para emissão."
        )
    licenca.save()
    return licenca
