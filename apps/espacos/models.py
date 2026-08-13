from django.db import models

from apps.core.models import ModeloBase


class StatusOcupacao(models.TextChoices):
    LIVRE = "Livre", "Livre"
    OCUPADO = "Ocupado", "Ocupado"
    BLOQUEADO = "Bloqueado", "Bloqueado"
    RESERVADO = "Reservado", "Reservado"


class PontoOcupacaoQuerySet(models.QuerySet):
    def livres(self):
        return self.filter(ativo=True, status_ocupacao=StatusOcupacao.LIVRE)


class Endereco(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="enderecos"
    )
    cep = models.CharField("CEP", max_length=9)
    logradouro = models.CharField("Logradouro", max_length=255)
    numero = models.CharField("Número", max_length=20)
    complemento = models.CharField("Complemento", max_length=100, blank=True, null=True)
    bairro = models.CharField("Bairro", max_length=100)
    cidade = models.CharField("Cidade", max_length=100)
    estado_uf = models.CharField("UF", max_length=2)

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"

    def __str__(self):
        return f"{self.logradouro}, {self.numero} - {self.cidade}/{self.estado_uf}"


class EstruturaTrabalho(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="estruturas"
    )
    tipo_estrutura = models.CharField("Tipo de Estrutura", max_length=255)
    dimensoes_metragem = models.DecimalField(
        "Dimensões (m²)", max_digits=5, decimal_places=2
    )
    foto_estrutura = models.ImageField(
        "Foto da Estrutura", upload_to="estruturas/", blank=True, null=True
    )
    descricao = models.TextField("Descrição")

    class Meta:
        verbose_name = "Estrutura de Trabalho"
        verbose_name_plural = "Estruturas de Trabalho"

    def __str__(self):
        return f"{self.tipo_estrutura} - {self.ambulante}"


class PontoOcupacao(ModeloBase):
    nome_identificacao = models.CharField("Nome de Identificação", max_length=255)
    logradouro = models.CharField("Logradouro", max_length=255)
    bairro = models.CharField("Bairro", max_length=255)
    coordenadas = models.CharField("Coordenadas", max_length=255, blank=True, null=True)
    metragem_maxima = models.DecimalField(
        "Metragem Máxima (m²)", max_digits=5, decimal_places=2
    )
    status_ocupacao = models.CharField(
        "Status de Ocupação",
        max_length=50,
        choices=StatusOcupacao.choices,
        default=StatusOcupacao.LIVRE,
    )

    objects = PontoOcupacaoQuerySet.as_manager()

    class Meta:
        verbose_name = "Ponto de Ocupação"
        verbose_name_plural = "Pontos de Ocupação"

    def __str__(self):
        return self.nome_identificacao

    def tem_licenca_ativa(self):
        from apps.licenciamento.models import StatusLicenca

        return self.licencas.filter(
            ativo=True,
            status=StatusLicenca.ATIVO,
        ).exists()

    def disponivel_para_nova_atribuicao(self):
        if not self.ativo or self.status_ocupacao != StatusOcupacao.LIVRE:
            return False
        return not self.tem_licenca_ativa()

    def metragem_compativel(self, metragem):
        if metragem is None:
            return True
        return metragem <= self.metragem_maxima
