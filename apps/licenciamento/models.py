from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import ModeloBase


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
    AGUARDANDO_PAGAMENTO = "Aguardando Pagamento da Taxa", "Aguardando Pagamento da Taxa"
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
        self.save(update_fields=["status_aprovacao", "motivo_rejeicao", "atualizado_em"])
        return self

    def rejeitar(self, motivo):
        justificativa = (motivo or "").strip()
        if not justificativa:
            raise ValidationError("A justificativa da rejeição é obrigatória.")
        self.status_aprovacao = StatusAprovacaoDocumento.REJEITADO
        self.motivo_rejeicao = justificativa
        self.save(update_fields=["status_aprovacao", "motivo_rejeicao", "atualizado_em"])
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
    numero_licenca = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    data_emissao = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=StatusLicenca.choices,
        default=StatusLicenca.EM_ANALISE,
    )
    motivo_parecer = models.TextField(blank=True, default="")

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
    def tipo_pedido(self):
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
    dia_semana = models.CharField(max_length=20)
    horario_inicio = models.TimeField()
    horario_termino = models.TimeField()
    status = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Escala de Trabalho"
        verbose_name_plural = "Escalas de Trabalho"

    def __str__(self):
        return f"{self.licenca_alvara} - {self.dia_semana}"
