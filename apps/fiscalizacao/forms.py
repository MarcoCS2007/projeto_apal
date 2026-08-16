from django import forms
from django.utils import timezone

from apps.usuarios.forms import normalizar_cpf
from apps.usuarios.models import Ambulante

from .models import CatalogoInfracao, StatusOcorrencia, TipoOcorrencia
from .services import transicoes_permitidas


class BuscaCampoForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "busca-fiscal",
                "placeholder": "CPF, nome, ALV-2026-0001 ou código do QR",
                "data-hint": "Busque por CPF, nome, número do alvará ou código do QR.",
            }
        ),
    )


class OcorrenciaForm(forms.Form):
    ambulante_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    identificacao = forms.CharField(
        required=False,
        label="CPF ou nº da licença",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ex: ALV-2026-0001 ou CPF (em branco se não identificado)",
                "data-hint": "Opcional se o ambulante já foi identificado na fiscalização.",
            }
        ),
    )
    local_ocorrencia = forms.CharField(
        required=True,
        label="Local da infração",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Endereço, ponto de referência ou via pública",
                "data-hint": "Informe rua, ponto ou referência para localizar a ocorrência.",
            }
        ),
    )
    tipo_ocorrencia = forms.ChoiceField(
        label="Tipo de infração",
        choices=TipoOcorrencia.choices,
    )
    descricao = forms.CharField(
        label="Relatório da fiscalização",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Descreva os fatos constatados pelo agente.",
                "data-hint": "Descreva o que foi visto, horário aproximado e qualquer evidência.",
            }
        ),
    )
    evidencia_foto = forms.ImageField(
        required=False,
        label="Foto da evidência",
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/*", "capture": "environment"}
        ),
    )
    infracao = forms.ModelChoiceField(
        queryset=CatalogoInfracao.objects.all(),
        required=False,
        label="Catálogo de Infração",
        empty_label="Selecione a infração (opcional)",
    )
    data_ocorrencia = forms.DateTimeField(
        label="Data e Hora da Ocorrência",
        required=False,
        initial=timezone.now,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control"}
        ),
    )

    def clean(self):
        dados = super().clean()
        ambulante_id = dados.get("ambulante_id")
        identificacao = (dados.get("identificacao") or "").strip()
        ambulante = None
        if ambulante_id:
            ambulante = Ambulante.objects.filter(pk=ambulante_id).first()
        elif identificacao:
            cpf = normalizar_cpf(identificacao)
            if len(cpf) == 11:
                ambulante = Ambulante.objects.filter(cpf=cpf).first()
            if ambulante is None:
                from apps.licenciamento.models import LicencaAlvara

                licenca = (
                    LicencaAlvara.objects.filter(numero_licenca__iexact=identificacao)
                    .select_related("ambulante")
                    .first()
                )
                if licenca:
                    ambulante = licenca.ambulante
        dados["ambulante"] = ambulante
        return dados


class FiltroOcorrenciaForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Pesquisar",
        widget=forms.TextInput(
            attrs={
                "id": "search-ocorrencias",
                "placeholder": "Fiscal, infrator, local ou tipo de infração",
            }
        ),
    )
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "Todos")] + list(StatusOcorrencia.choices),
        widget=forms.Select(attrs={"class": "styled-select", "id": "filtro-status"}),
    )
    tipo = forms.ChoiceField(
        required=False,
        label="Tipo",
        choices=[("", "Todos")] + list(TipoOcorrencia.choices),
        widget=forms.Select(attrs={"class": "styled-select", "id": "filtro-tipo"}),
    )


class AuditoriaOcorrenciaForm(forms.Form):
    status_ocorrencia = forms.ChoiceField(
        label="Status do auto",
        widget=forms.Select(attrs={"class": "styled-select"}),
    )
    infracao = forms.ModelChoiceField(
        queryset=CatalogoInfracao.objects.all(),
        required=False,
        label="Penalidade Aplicada",
        empty_label="Nenhuma (ou manter a original)",
        widget=forms.Select(attrs={"class": "styled-select"}),
    )

    def __init__(self, *args, ocorrencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        atual = (
            ocorrencia.status_ocorrencia if ocorrencia else StatusOcorrencia.REGISTRADA
        )
        opcoes = [(atual, atual)]
        for status in transicoes_permitidas(atual):
            if status != atual:
                opcoes.append((status, status))
        self.fields["status_ocorrencia"].choices = opcoes
        if ocorrencia and ocorrencia.infracao:
            self.fields["infracao"].initial = ocorrencia.infracao


class CatalogoInfracaoForm(forms.ModelForm):
    class Meta:
        model = CatalogoInfracao
        fields = ("descricao", "gravidade", "pontos_desconto")
        widgets = {  # noqa: RUF012
            "descricao": forms.TextInput(
                attrs={
                    "placeholder": "Ex: Venda fora do horário regulamentado",
                    "class": "form-control",
                }
            ),
            "gravidade": forms.Select(attrs={"class": "styled-select"}),
            "pontos_desconto": forms.NumberInput(
                attrs={"min": 0, "class": "form-control"}
            ),
        }
