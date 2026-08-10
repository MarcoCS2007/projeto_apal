from django.db import models

from apps.core.models import ModeloBase


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
