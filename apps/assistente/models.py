from django.db import models

from apps.core.models import ModeloBase


class LogAssistente(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="logs_assistente"
    )
    pergunta = models.TextField()

    class Meta:
        verbose_name = "Log do Assistente"
        verbose_name_plural = "Logs do Assistente"

    def __str__(self):
        return f"Log ({self.id}) - {self.ambulante}"
