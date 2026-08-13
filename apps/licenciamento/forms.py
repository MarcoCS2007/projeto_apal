from datetime import time, timedelta

from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.utils import timezone

from apps.espacos.models import PontoOcupacao, StatusOcupacao
from apps.licenciamento.models import (
    DIAS_SEMANA,
    DIAS_SEMANA_PADRAO,
    CategoriaProduto,
    TipoDocumento,
)
from apps.licenciamento.services import (
    categoria_do_ambulante,
    registrar_documento,
)

EXTENSOES_DOCUMENTO = ["pdf", "png", "jpg", "jpeg", "webp"]

CAMPOS_ARQUIVO = (
    ("arquivo_comprovante_residencia", TipoDocumento.COMPROVANTE_RESIDENCIA),
    ("arquivo_rg_cpf", TipoDocumento.RG_CPF),
    ("arquivo_mei", TipoDocumento.MEI),
    ("arquivo_laudo_sanitario", TipoDocumento.LAUDO_SANITARIO),
    ("arquivo_laudo_bombeiros", TipoDocumento.LAUDO_BOMBEIROS),
)

CAMPOS_VALIDADE = {
    TipoDocumento.LAUDO_SANITARIO: "validade_laudo_sanitario",
    TipoDocumento.LAUDO_BOMBEIROS: "validade_laudo_bombeiros",
}


def _arquivo_widget(input_id):
    return forms.ClearableFileInput(
        attrs={
            "id": input_id,
            "accept": ".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*",
        }
    )


class CategoriaProdutoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProduto
        fields = (
            "nome_categoria",
            "descricao",
            "exige_laudo_sanitario",
            "exige_laudo_bombeiros",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_categoria"].widget.attrs.update(
            {
                "id": "nome-categoria",
                "placeholder": "Ex: Alimentação Preparada (Lanches/Refeições)",
            }
        )
        self.fields["descricao"].widget = forms.TextInput(
            attrs={
                "id": "descricao-categoria",
                "placeholder": (
                    "Ex: Venda de acarajé, churrasquinho, pastéis, "
                    "lanches rápidos e sucos."
                ),
            }
        )
        self.fields["descricao"].required = True
        self.fields["exige_laudo_sanitario"].widget.attrs.update(
            {"id": "exige-sanitario", "style": "width: 18px; height: 18px;"}
        )
        self.fields["exige_laudo_bombeiros"].widget.attrs.update(
            {"id": "exige-bombeiros", "style": "width: 18px; height: 18px;"}
        )

    def clean_nome_categoria(self):
        nome = (self.cleaned_data.get("nome_categoria") or "").strip()
        duplicadas = CategoriaProduto.objects.filter(
            nome_categoria__iexact=nome,
            ativo=True,
        )
        if self.instance.pk:
            duplicadas = duplicadas.exclude(pk=self.instance.pk)
        if duplicadas.exists():
            raise forms.ValidationError("Já existe uma categoria com este nome")
        return nome


class AnexosDocumentosForm(forms.Form):
    arquivo_comprovante_residencia = forms.FileField(
        label="Comprovante de Residência",
        required=False,
        validators=[FileExtensionValidator(EXTENSOES_DOCUMENTO)],
        widget=_arquivo_widget("doc-comprovante"),
    )
    arquivo_rg_cpf = forms.FileField(
        label="Cópia do RG/CPF",
        required=False,
        validators=[FileExtensionValidator(EXTENSOES_DOCUMENTO)],
        widget=_arquivo_widget("doc-rg"),
    )
    arquivo_mei = forms.FileField(
        label="Comprovante de MEI / CNPJ",
        required=False,
        validators=[FileExtensionValidator(EXTENSOES_DOCUMENTO)],
        widget=_arquivo_widget("doc-mei"),
    )
    arquivo_laudo_sanitario = forms.FileField(
        label="Laudo Sanitário",
        required=False,
        validators=[FileExtensionValidator(EXTENSOES_DOCUMENTO)],
        widget=_arquivo_widget("doc-saude"),
    )
    validade_laudo_sanitario = forms.DateField(
        label="Validade do laudo sanitário",
        required=False,
        widget=forms.DateInput(
            attrs={"id": "validade-saude", "type": "date"},
            format="%Y-%m-%d",
        ),
    )
    arquivo_laudo_bombeiros = forms.FileField(
        label="Laudo dos Bombeiros",
        required=False,
        validators=[FileExtensionValidator(EXTENSOES_DOCUMENTO)],
        widget=_arquivo_widget("doc-bombeiros"),
    )
    validade_laudo_bombeiros = forms.DateField(
        label="Validade do laudo dos bombeiros",
        required=False,
        widget=forms.DateInput(
            attrs={"id": "validade-bombeiros", "type": "date"},
            format="%Y-%m-%d",
        ),
    )
    foto = forms.ImageField(
        label="Foto 3x4 recente",
        required=False,
        widget=forms.ClearableFileInput(attrs={"id": "doc-foto", "accept": "image/*"}),
    )
    foto_estrutura = forms.ImageField(
        label="Foto da estrutura",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"id": "doc-estrutura", "accept": "image/*"}
        ),
    )

    def __init__(self, *args, ambulante=None, acao=None, **kwargs):
        self.ambulante = ambulante
        self.acao = acao
        super().__init__(*args, **kwargs)
        self.fields["validade_laudo_sanitario"].input_formats = ["%Y-%m-%d"]
        self.fields["validade_laudo_bombeiros"].input_formats = ["%Y-%m-%d"]
        if ambulante and not args:
            for tipo, campo in CAMPOS_VALIDADE.items():
                doc = ambulante.documentos.filter(tipo_documento=tipo).first()
                if doc and doc.data_validade:
                    self.fields[campo].initial = doc.data_validade
        self.categoria = categoria_do_ambulante(ambulante) if ambulante else None

    def save(self):
        ambulante = self.ambulante
        if self.cleaned_data.get("foto"):
            ambulante.foto = self.cleaned_data["foto"]
            ambulante.save(update_fields=["foto", "atualizado_em"])
        estrutura = ambulante.estruturas.order_by("id").first()
        if estrutura and self.cleaned_data.get("foto_estrutura"):
            estrutura.foto_estrutura = self.cleaned_data["foto_estrutura"]
            estrutura.save(update_fields=["foto_estrutura", "atualizado_em"])

        for campo, tipo in CAMPOS_ARQUIVO:
            arquivo = self.cleaned_data.get(campo)
            if not arquivo:
                continue
            validade_campo = CAMPOS_VALIDADE.get(tipo)
            validade = self.cleaned_data.get(validade_campo) if validade_campo else None
            registrar_documento(ambulante, tipo, arquivo, data_validade=validade)
        return ambulante


class ParecerLicencaForm(forms.Form):
    acao = forms.ChoiceField(
        choices=(
            ("deferir", "Deferir"),
            ("indeferir", "Indeferir"),
            ("pendencia", "Devolver com pendência"),
        )
    )
    motivo = forms.CharField(required=False, widget=forms.Textarea)
    categoria_produto = forms.ModelChoiceField(
        queryset=CategoriaProduto.objects.none(),
        required=False,
    )
    ponto_ocupacao = forms.ModelChoiceField(
        queryset=PontoOcupacao.objects.none(),
        required=False,
    )

    def __init__(self, *args, licenca=None, **kwargs):
        self.licenca = licenca
        super().__init__(*args, **kwargs)
        self.fields["categoria_produto"].queryset = CategoriaProduto.objects.filter(
            ativo=True
        ).order_by("nome_categoria")
        self.fields["ponto_ocupacao"].queryset = PontoOcupacao.objects.filter(
            ativo=True
        ).order_by("nome_identificacao")
        if licenca and not args:
            self.fields["categoria_produto"].initial = licenca.categoria_produto_id
            self.fields["ponto_ocupacao"].initial = licenca.ponto_ocupacao_id


class EmitirAlvaraForm(forms.Form):
    data_emissao = forms.DateField(
        label="Data de emissão",
        widget=forms.DateInput(
            attrs={"id": "data-emissao", "type": "date"},
            format="%Y-%m-%d",
        ),
    )
    data_vencimento = forms.DateField(
        label="Data de validade da licença",
        widget=forms.DateInput(
            attrs={"id": "validade-licenca", "type": "date"},
            format="%Y-%m-%d",
        ),
    )
    ponto_ocupacao = forms.ModelChoiceField(
        label="Ponto de ocupação",
        queryset=PontoOcupacao.objects.none(),
    )
    dias_semana = forms.MultipleChoiceField(
        label="Dias autorizados",
        choices=DIAS_SEMANA,
        widget=forms.CheckboxSelectMultiple,
    )
    horario_inicio = forms.TimeField(
        label="Horário de início",
        widget=forms.TimeInput(
            attrs={"id": "horario-inicio", "type": "time"},
            format="%H:%M",
        ),
        input_formats=["%H:%M", "%H:%M:%S"],
    )
    horario_termino = forms.TimeField(
        label="Horário de término",
        widget=forms.TimeInput(
            attrs={"id": "horario-termino", "type": "time"},
            format="%H:%M",
        ),
        input_formats=["%H:%M", "%H:%M:%S"],
    )
    observacoes = forms.CharField(
        label="Observações para o alvará",
        required=False,
        widget=forms.Textarea(
            attrs={
                "id": "obs-alvara",
                "rows": 3,
                "placeholder": (
                    "Insira restrições, recomendações ou observações "
                    "que constarão no documento do ambulante..."
                ),
            }
        ),
    )

    def __init__(self, *args, licenca=None, **kwargs):
        self.licenca = licenca
        super().__init__(*args, **kwargs)
        self.fields["data_emissao"].input_formats = ["%Y-%m-%d"]
        self.fields["data_vencimento"].input_formats = ["%Y-%m-%d"]
        pontos = PontoOcupacao.objects.filter(
            ativo=True, status_ocupacao=StatusOcupacao.LIVRE
        )
        if licenca and licenca.ponto_ocupacao_id:
            pontos = PontoOcupacao.objects.filter(
                Q(pk__in=pontos.values("pk")) | Q(pk=licenca.ponto_ocupacao_id),
                ativo=True,
            )
        self.fields["ponto_ocupacao"].queryset = pontos.order_by("nome_identificacao")
        self.fields["ponto_ocupacao"].widget.attrs.update({"class": "styled-select"})
        if not args:
            hoje = timezone.localdate()
            self.fields["data_emissao"].initial = hoje
            self.fields["data_vencimento"].initial = hoje + timedelta(days=365)
            self.fields["horario_inicio"].initial = time(6, 0)
            self.fields["horario_termino"].initial = time(18, 0)
            self.fields["dias_semana"].initial = list(DIAS_SEMANA_PADRAO)
            if licenca:
                self.fields["ponto_ocupacao"].initial = licenca.ponto_ocupacao_id

    def clean(self):
        dados = super().clean()
        emissao = dados.get("data_emissao")
        vencimento = dados.get("data_vencimento")
        if emissao and vencimento and vencimento <= emissao:
            self.add_error(
                "data_vencimento",
                "A validade deve ser posterior à data de emissão.",
            )
        inicio = dados.get("horario_inicio")
        termino = dados.get("horario_termino")
        if inicio and termino and termino <= inicio:
            self.add_error(
                "horario_termino",
                "O horário de término deve ser posterior ao de início.",
            )
        return dados
