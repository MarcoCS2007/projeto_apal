from django.db import models


class AtivoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)


class ModeloBase(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)

    objects = models.Manager()
    ativos = AtivoManager()

    class Meta:
        abstract = True
