from django import forms

from .forms import separar_nome
from .forms_cadastro import GENERO_CHOICES, TIPO_COMERCIO_CHOICES, _incluir_valor_atual
from .models import Ambulante, Genero


class EditarAmbulanteGestorForm(forms.Form):
    nome_completo = forms.CharField(
        label="Nome completo",
        max_length=300,
        widget=forms.TextInput(attrs={"placeholder": "Nome completo"}),
    )
    email = forms.EmailField(label="E-mail")
    telefone_whatsapp = forms.CharField(label="Telefone / WhatsApp", max_length=20)
    telefone_2 = forms.CharField(
        label="Telefone secundário",
        max_length=20,
        required=False,
    )
    apelido_nome_fantasia = forms.CharField(
        label="Nome fantasia / apelido",
        max_length=150,
        required=False,
    )
    tipo_atuacao = forms.ChoiceField(
        label="Tipo de atuação",
        choices=TIPO_COMERCIO_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "styled-select"}),
    )
    nis = forms.CharField(label="NIS", max_length=20, required=False)
    escolaridade = forms.CharField(label="Escolaridade", max_length=100, required=False)
    genero = forms.ChoiceField(
        label="Gênero",
        choices=GENERO_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "styled-select"}),
    )
    renda_estimada = forms.DecimalField(
        label="Renda mensal estimada (R$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        if ambulante:
            self.fields["tipo_atuacao"].choices = _incluir_valor_atual(
                TIPO_COMERCIO_CHOICES, ambulante.tipo_atuacao
            )
            self.fields["genero"].choices = _incluir_valor_atual(
                GENERO_CHOICES, ambulante.genero
            )
            if not args:
                self.fields["nome_completo"].initial = ambulante.nome_completo
                self.fields["email"].initial = ambulante.email
                self.fields["telefone_whatsapp"].initial = ambulante.telefone_whatsapp
                self.fields["telefone_2"].initial = ambulante.telefone_2 or ""
                self.fields["apelido_nome_fantasia"].initial = (
                    ambulante.apelido_nome_fantasia or ""
                )
                self.fields["tipo_atuacao"].initial = ambulante.tipo_atuacao
                self.fields["nis"].initial = ambulante.nis or ""
                self.fields["escolaridade"].initial = ambulante.escolaridade
                self.fields["genero"].initial = ambulante.genero or Genero.NAO_INFORMADO
                self.fields["renda_estimada"].initial = ambulante.renda_estimada

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duplicado = (
            Ambulante.objects.filter(email__iexact=email)
            .exclude(pk=self.ambulante.pk)
            .exists()
        )
        if duplicado:
            raise forms.ValidationError("Já existe um ambulante com este e-mail.")
        return email

    def save(self):
        ambulante = self.ambulante
        nome, sobrenome = separar_nome(self.cleaned_data["nome_completo"])
        ambulante.nome = nome
        ambulante.sobrenome = sobrenome
        ambulante.email = self.cleaned_data["email"]
        ambulante.telefone_whatsapp = self.cleaned_data["telefone_whatsapp"]
        ambulante.telefone_2 = self.cleaned_data.get("telefone_2") or None
        ambulante.apelido_nome_fantasia = (
            self.cleaned_data.get("apelido_nome_fantasia") or None
        )
        ambulante.tipo_atuacao = self.cleaned_data.get("tipo_atuacao") or ""
        ambulante.nis = self.cleaned_data.get("nis") or None
        ambulante.escolaridade = self.cleaned_data.get("escolaridade") or ""
        ambulante.genero = self.cleaned_data.get("genero") or Genero.NAO_INFORMADO
        ambulante.renda_estimada = self.cleaned_data.get("renda_estimada")
        ambulante.save()
        return ambulante
