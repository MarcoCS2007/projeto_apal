from django.db import models

from apps.core.models import ModeloBase


class LogAssistente(ModeloBase):
    ambulante = models.ForeignKey(
        "usuarios.Ambulante", on_delete=models.CASCADE, related_name="logs_assistente"
    )
    pergunta = models.TextField()
    resposta = models.TextField(blank=True)
    fonte = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Log do Assistente"
        verbose_name_plural = "Logs do Assistente"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"Log ({self.id}) - {self.ambulante}"
