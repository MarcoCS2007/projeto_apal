from django.db import models

from apps.core.models import ModeloBase


class OcorrenciaInspecao(ModeloBase):
    fiscal = models.ForeignKey(
        "usuarios.Fiscal",
        on_delete=models.CASCADE,
        related_name="ocorrencias_registradas",
    )
    ambulante = models.ForeignKey(
        "usuarios.Ambulante",
        on_delete=models.CASCADE,
        related_name="ocorrencias_recebidas",
    )
    tipo_ocorrencia = models.CharField(max_length=100)
    descricao = models.TextField()
    evidencia_foto = models.ImageField(
        upload_to="fiscalizacao/ocorrencias/", null=True, blank=True
    )
    status_ocorrencia = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Ocorrência de Inspeção"
        verbose_name_plural = "Ocorrências de Inspeção"

    def __str__(self):
        return f"{self.tipo_ocorrencia} - {self.ambulante}"
