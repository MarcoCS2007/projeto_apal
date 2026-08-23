from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import PontoOcupacao, StatusOcupacao


class PontoOcupacaoForm(forms.ModelForm):
    class Meta:
        model = PontoOcupacao
        fields = (
            "nome_identificacao",
            "logradouro",
            "bairro",
            "coordenadas",
            "metragem_maxima",
            "status_ocupacao",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_identificacao"].widget.attrs.update(
            {
                "id": "nome-ponto",
                "placeholder": "Ex: Praça Central — vaga 01",
            }
        )
        self.fields["logradouro"].widget.attrs.update(
            {
                "id": "logradouro-ponto",
                "placeholder": "Ex: Praça Barão do Rio Branco",
            }
        )
        self.fields["bairro"].widget.attrs.update(
            {
                "id": "bairro-ponto",
                "placeholder": "Ex: Centro",
            }
        )
        self.fields["coordenadas"].widget.attrs.update(
            {
                "id": "coordenadas-ponto",
                "placeholder": "Ex: -14.8661,-40.8390",
            }
        )
        self.fields["metragem_maxima"].widget.attrs.update(
            {
                "id": "metragem-ponto",
                "placeholder": "Ex: 10.00",
                "step": "0.01",
                "min": "0.01",
            }
        )
        self.fields["status_ocupacao"].widget.attrs.update(
            {"id": "status-ponto", "class": "styled-select"}
        )
        self.fields["coordenadas"].required = False

    def clean_nome_identificacao(self):
        nome = (self.cleaned_data.get("nome_identificacao") or "").strip()
        if not nome:
            raise ValidationError("Informe o nome de identificação do ponto.")
        duplicado = PontoOcupacao.objects.filter(
            nome_identificacao__iexact=nome,
            ativo=True,
        )
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise ValidationError("Já existe um ponto com este nome.")
        return nome

    def clean_metragem_maxima(self):
        metragem = self.cleaned_data.get("metragem_maxima")
        if metragem is None or metragem <= Decimal(0):
            raise ValidationError("Informe uma metragem máxima positiva.")
        return metragem

    def clean_status_ocupacao(self):
        status = self.cleaned_data.get("status_ocupacao") or StatusOcupacao.LIVRE
        if (
            self.instance.pk
            and status == StatusOcupacao.LIVRE
            and self.instance.tem_licenca_ativa()
        ):
            raise ValidationError(
                "Este ponto possui licença ativa e não pode voltar para Livre."
            )
        return status
