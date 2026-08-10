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


class DocumentoAnexo(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="documentos"
    )
    tipo_documento = models.CharField("Tipo de Documento", max_length=100)
    arquivo = models.FileField("Arquivo", upload_to="documentos/")
    data_upload = models.DateTimeField("Data de Upload", auto_now_add=True)
    data_validade = models.DateField("Data de Validade", null=True, blank=True)
    status_aprovacao = models.CharField("Status de Aprovação", max_length=50)
    motivo_rejeicao = models.TextField("Motivo da Rejeição", null=True, blank=True)

    class Meta:
        verbose_name = "Documento Anexo"
        verbose_name_plural = "Documentos Anexos"

    def __str__(self):
        return f"{self.tipo_documento} - {self.ambulante}"


class LicencaAlvara(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="licencas"
    )
    estrutura_trabalho = models.ForeignKey(
        "espacos.EstruturaTrabalho", on_delete=models.CASCADE, related_name="licencas"
    )
    ponto_ocupacao = models.ForeignKey(
        "espacos.PontoOcupacao", on_delete=models.CASCADE, related_name="licencas"
    )
    categoria_produto = models.ForeignKey(
        "CategoriaProduto", on_delete=models.CASCADE, related_name="licencas"
    )
    gestor_responsavel = models.ForeignKey(
        "usuarios.Gestor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="licencas_aprovadas",
    )
    numero_licenca = models.CharField(max_length=50, unique=True)
    data_emissao = models.DateField()
    data_vencimento = models.DateField()
    status = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Licença Alvará"
        verbose_name_plural = "Licenças Alvarás"

    def __str__(self):
        return f"{self.numero_licenca} - {self.ambulante}"


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
