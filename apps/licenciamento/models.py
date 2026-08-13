from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import ModeloBase

VALOR_TAXA_DAM = Decimal("120.00")


class CategoriaProduto(ModeloBase):
    nome_categoria = models.CharField("Nome da Categoria", max_length=255)
    descricao = models.TextField("Descrição", blank=True, null=True)
    exige_laudo_sanitario = models.BooleanField("Exige Laudo Sanitário", default=False)
    exige_laudo_bombeiros = models.BooleanField(
        "Exige Laudo dos Bombeiros", default=False
    )

    class Meta:
        verbose_name = "Categoria de Produto"
        verbose_name_plural = "Categorias de Produtos"

    def __str__(self):
        return self.nome_categoria


class TipoDocumento(models.TextChoices):
    COMPROVANTE_RESIDENCIA = "comprovante_residencia", "Comprovante de Residência"
    RG_CPF = "rg_cpf", "RG/CPF"
    MEI = "mei", "MEI / CNPJ"
    LAUDO_SANITARIO = "laudo_sanitario", "Laudo Sanitário"
    LAUDO_BOMBEIROS = "laudo_bombeiros", "Laudo dos Bombeiros"


class StatusAprovacaoDocumento(models.TextChoices):
    PENDENTE = "Pendente", "Pendente"
    APROVADO = "Aprovado", "Aprovado"
    REJEITADO = "Rejeitado", "Rejeitado"


class StatusLicenca(models.TextChoices):
    EM_ANALISE = "Em Análise", "Em Análise"
    PENDENCIA_DOCUMENTAL = "Pendência Documental", "Pendência Documental"
    APROVADO = "Aprovado", "Aprovado"
    INDEFERIDO = "Indeferido", "Indeferido"
    AGUARDANDO_PAGAMENTO = (
        "Aguardando Pagamento da Taxa",
        "Aguardando Pagamento da Taxa",
    )
    ATIVO = "Ativo", "Ativo"
    VENCIDO = "Vencido", "Vencido"
    SUSPENSO = "Suspenso", "Suspenso"
    CANCELADO = "Cancelado", "Cancelado"


StatusSolicitacao = StatusLicenca

STATUS_LICENCA_ATIVA = (StatusLicenca.ATIVO,)

STATUS_FILA = (
    StatusLicenca.EM_ANALISE,
    StatusLicenca.PENDENCIA_DOCUMENTAL,
)

STATUS_LISTAGEM_GESTOR = (
    StatusLicenca.APROVADO,
    StatusLicenca.ATIVO,
    StatusLicenca.VENCIDO,
    StatusLicenca.SUSPENSO,
)

STATUS_ESCALA_AUTORIZADA = "Autorizado"

DIAS_SEMANA = (
    ("segunda", "Segunda-feira"),
    ("terca", "Terça-feira"),
    ("quarta", "Quarta-feira"),
    ("quinta", "Quinta-feira"),
    ("sexta", "Sexta-feira"),
    ("sabado", "Sábado"),
    ("domingo", "Domingo"),
)

DIAS_SEMANA_PADRAO = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado")


TIPOS_BASICOS_OBRIGATORIOS = (
    TipoDocumento.COMPROVANTE_RESIDENCIA,
    TipoDocumento.RG_CPF,
)


class DocumentoAnexo(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="documentos"
    )
    tipo_documento = models.CharField(
        "Tipo de Documento",
        max_length=100,
        choices=TipoDocumento.choices,
    )
    arquivo = models.FileField(
        "Arquivo",
        upload_to="documentos/",
        validators=[
            FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "webp"]),
        ],
    )
    data_upload = models.DateTimeField("Data de Upload", auto_now_add=True)
    data_validade = models.DateField("Data de Validade", null=True, blank=True)
    status_aprovacao = models.CharField(
        "Status de Aprovação",
        max_length=50,
        choices=StatusAprovacaoDocumento.choices,
        default=StatusAprovacaoDocumento.PENDENTE,
    )
    motivo_rejeicao = models.TextField("Motivo da Rejeição", null=True, blank=True)

    class Meta:
        verbose_name = "Documento Anexo"
        verbose_name_plural = "Documentos Anexos"
        constraints = (
            models.UniqueConstraint(
                fields=("ambulante", "tipo_documento"),
                name="uniq_documento_ambulante_tipo",
            ),
        )

    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.ambulante}"

    @property
    def pendente(self):
        return self.status_aprovacao == StatusAprovacaoDocumento.PENDENTE

    @property
    def aprovado(self):
        return self.status_aprovacao == StatusAprovacaoDocumento.APROVADO

    @property
    def rejeitado(self):
        return self.status_aprovacao == StatusAprovacaoDocumento.REJEITADO

    def aprovar(self):
        self.status_aprovacao = StatusAprovacaoDocumento.APROVADO
        self.motivo_rejeicao = ""
        self.save(
            update_fields=["status_aprovacao", "motivo_rejeicao", "atualizado_em"]
        )
        return self

    def rejeitar(self, motivo):
        justificativa = (motivo or "").strip()
        if not justificativa:
            raise ValidationError("A justificativa da rejeição é obrigatória.")
        self.status_aprovacao = StatusAprovacaoDocumento.REJEITADO
        self.motivo_rejeicao = justificativa
        self.save(
            update_fields=["status_aprovacao", "motivo_rejeicao", "atualizado_em"]
        )
        from apps.licenciamento.services import marcar_pendencia_documental

        marcar_pendencia_documental(self.ambulante)
        return self

    def reenviar(self, arquivo, data_validade=None):
        from django.utils import timezone

        self.arquivo = arquivo
        self.data_validade = data_validade
        self.status_aprovacao = StatusAprovacaoDocumento.PENDENTE
        self.motivo_rejeicao = ""
        self.data_upload = timezone.now()
        self.save(
            update_fields=[
                "arquivo",
                "data_validade",
                "status_aprovacao",
                "motivo_rejeicao",
                "data_upload",
                "atualizado_em",
            ]
        )
        from apps.licenciamento.services import reabrir_analise_se_sem_rejeicoes

        reabrir_analise_se_sem_rejeicoes(self.ambulante)
        return self


class LicencaAlvara(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="licencas"
    )
    estrutura_trabalho = models.ForeignKey(
        "espacos.EstruturaTrabalho",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas",
    )
    ponto_ocupacao = models.ForeignKey(
        "espacos.PontoOcupacao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas",
    )
    categoria_produto = models.ForeignKey(
        "CategoriaProduto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas",
    )
    gestor_responsavel = models.ForeignKey(
        "usuarios.Gestor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas_aprovadas",
    )
    protocolo = models.CharField(max_length=50, unique=True, null=True, blank=True)
    numero_licenca = models.CharField(max_length=50, unique=True, null=True, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=StatusLicenca.choices,
        default=StatusLicenca.EM_ANALISE,
    )
    motivo_parecer = models.TextField(blank=True, default="")
    taxa_paga = models.BooleanField("Taxa municipal paga", default=False)
    licenca_origem = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renovacoes",
    )

    class Meta:
        verbose_name = "Licença Alvará"
        verbose_name_plural = "Licenças Alvarás"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.protocolo or self.numero_licenca or self.pk} - {self.ambulante}"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        super().save(*args, **kwargs)
        if not self.protocolo:
            ano = (self.criado_em or timezone.now()).year
            self.protocolo = f"REQ-{ano}-{self.pk:04d}"
            super().save(update_fields=["protocolo"])

    @property
    def na_fila(self):
        return self.status in STATUS_FILA

    @property
    def aguardando_taxa(self):
        return (not self.taxa_paga) and self.status in (
            StatusLicenca.APROVADO,
            StatusLicenca.AGUARDANDO_PAGAMENTO,
        )

    @property
    def pode_emitir(self):
        return self.status == StatusLicenca.APROVADO and not self.numero_licenca

    @property
    def qr_valido(self):
        from django.utils import timezone

        if self.status != StatusLicenca.ATIVO:
            return False
        if self.data_vencimento and self.data_vencimento < timezone.localdate():
            return False
        return True

    @property
    def texto_horario_autorizado(self):
        escalas = list(self.escalas.all())
        if not escalas:
            return "Não informado"
        ordem = {chave: indice for indice, (chave, _rotulo) in enumerate(DIAS_SEMANA)}
        escalas = sorted(escalas, key=lambda item: ordem.get(item.dia_semana, 99))
        horarios = {(item.horario_inicio, item.horario_termino) for item in escalas}
        dias = ", ".join(item.get_dia_semana_display() for item in escalas)
        if len(horarios) == 1:
            inicio, termino = next(iter(horarios))
            return f"{dias}, {inicio.strftime('%H:%M')} às {termino.strftime('%H:%M')}"
        return "; ".join(
            f"{item.get_dia_semana_display()} "
            f"{item.horario_inicio.strftime('%H:%M')}–"
            f"{item.horario_termino.strftime('%H:%M')}"
            for item in escalas
        )

    @property
    def pode_renovar(self):
        return self.status == StatusLicenca.VENCIDO

    @property
    def valor_taxa(self):
        return VALOR_TAXA_DAM

    @property
    def classe_badge(self):
        if self.aguardando_taxa:
            return "warning"
        if self.status in (StatusLicenca.ATIVO, StatusLicenca.APROVADO):
            return "success"
        if self.status == StatusLicenca.PENDENCIA_DOCUMENTAL:
            return "purple"
        if self.status in (
            StatusLicenca.INDEFERIDO,
            StatusLicenca.VENCIDO,
            StatusLicenca.SUSPENSO,
            StatusLicenca.CANCELADO,
        ):
            return "danger"
        return "warning"

    @property
    def tipo_pedido(self):
        if self.licenca_origem_id:
            if self.numero_licenca:
                return "Renovação / alvará emitido"
            return "Renovação"
        if self.numero_licenca:
            return "Renovação / alvará emitido"
        tipo = (self.ambulante.tipo_atuacao or "").lower()
        if tipo == "movel":
            return "Nova Licença (Móvel)"
        if tipo == "eventual":
            return "Nova Licença (Eventual)"
        return "Nova Licença (Fixo)"


class EscalaTrabalho(ModeloBase):
    licenca_alvara = models.ForeignKey(
        "LicencaAlvara", on_delete=models.CASCADE, related_name="escalas"
    )
    dia_semana = models.CharField(max_length=20, choices=DIAS_SEMANA)
    horario_inicio = models.TimeField()
    horario_termino = models.TimeField()
    status = models.CharField(max_length=50, default=STATUS_ESCALA_AUTORIZADA)

    class Meta:
        verbose_name = "Escala de Trabalho"
        verbose_name_plural = "Escalas de Trabalho"

    def __str__(self):
        return f"{self.licenca_alvara} - {self.dia_semana}"
