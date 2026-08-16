from django.db import models
from django.utils import timezone

from apps.core.models import ModeloBase


class TipoOcorrencia(models.TextChoices):
    ADVERTENCIA = "Advertência", "Advertência"
    MULTA = "Multa", "Multa"
    APREENSAO = "Apreensão", "Apreensão"
    FORA_PONTO = "Irregularidade de ponto", "Irregularidade de ponto"
    FORA_HORARIO = "Irregularidade de horário", "Irregularidade de horário"
    SEM_LICENCA = "Comércio sem licença válida", "Comércio sem licença válida"
    SEM_CREDENCIAL = "Falta de credencial", "Falta de credencial"
    OUTRO = "Outra irregularidade", "Outra irregularidade"


class StatusOcorrencia(models.TextChoices):
    REGISTRADA = "Registrada", "Registrada"
    EM_ANALISE = "Em análise", "Em análise"
    PROCEDENTE = "Procedente", "Procedente"
    IMPROCEDENTE = "Improcedente", "Improcedente"
    CONVERTIDA_MULTA = "Convertida em multa", "Convertida em multa"


TIPO_POR_MOTIVO = {
    "fora_horario": TipoOcorrencia.FORA_HORARIO,
    "suspenso": TipoOcorrencia.SEM_LICENCA,
    "vencido": TipoOcorrencia.SEM_LICENCA,
    "adulterado": TipoOcorrencia.SEM_CREDENCIAL,
    "invalido": TipoOcorrencia.SEM_LICENCA,
}


class CatalogoInfracao(ModeloBase):
    GRAVIDADE_CHOICES = (
        ("LEVE", "Leve"),
        ("MEDIA", "Média"),
        ("GRAVE", "Grave"),
        ("GRAVISSIMA", "Gravíssima"),
    )
    descricao = models.CharField(max_length=255)
    gravidade = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES)
    pontos_desconto = models.IntegerField()

    class Meta:
        verbose_name = "Catálogo de Infração"
        verbose_name_plural = "Catálogos de Infrações"

    def __str__(self):
        return f"{self.descricao} - {self.get_gravidade_display()}"


class OcorrenciaInspecao(ModeloBase):
    STATUS_GESTOR_CHOICES = (
        ("PENDENTE", "Pendente"),
        ("APROVADA", "Aprovada"),
        ("REJEITADA", "Rejeitada"),
    )

    fiscal = models.ForeignKey(
        "usuarios.Fiscal",
        on_delete=models.CASCADE,
        related_name="ocorrencias_registradas",
    )
    ambulante = models.ForeignKey(
        "usuarios.Ambulante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ocorrencias_recebidas",
    )
    tipo_ocorrencia = models.CharField(max_length=100, choices=TipoOcorrencia.choices)
    descricao = models.TextField()
    local_ocorrencia = models.CharField(max_length=255, blank=True, default="")
    evidencia_foto = models.ImageField(
        upload_to="fiscalizacao/ocorrencias/", null=True, blank=True
    )
    status_ocorrencia = models.CharField(
        max_length=50,
        choices=StatusOcorrencia.choices,
        default=StatusOcorrencia.REGISTRADA,
    )
    infracao = models.ForeignKey(
        "CatalogoInfracao", on_delete=models.SET_NULL, null=True, blank=True
    )
    status_gestor = models.CharField(
        max_length=20, choices=STATUS_GESTOR_CHOICES, default="PENDENTE"
    )
    data_ocorrencia = models.DateTimeField(
        "Data e Hora da Ocorrência", default=timezone.now
    )

    class Meta:
        verbose_name = "Ocorrência de Inspeção"
        verbose_name_plural = "Ocorrências de Inspeção"

    def __str__(self):
        alvo = self.ambulante or "não identificado"
        return f"{self.tipo_ocorrencia} - {alvo}"

    @property
    def classe_badge(self):
        if self.status_ocorrencia == StatusOcorrencia.IMPROCEDENTE:
            return "success"
        if self.status_ocorrencia in (
            StatusOcorrencia.PROCEDENTE,
            StatusOcorrencia.CONVERTIDA_MULTA,
        ):
            return "danger"
        if self.status_ocorrencia == StatusOcorrencia.EM_ANALISE:
            return "purple"
        return "warning"

    @property
    def status_final(self):
        return self.status_ocorrencia in (
            StatusOcorrencia.IMPROCEDENTE,
            StatusOcorrencia.CONVERTIDA_MULTA,
        )
