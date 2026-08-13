from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.espacos.models import Endereco, EstruturaTrabalho, PontoOcupacao
from apps.licenciamento.forms import AnexosDocumentosForm
from apps.licenciamento.models import CategoriaProduto
from apps.licenciamento.services import (
    categoria_do_ambulante,
    gravar_categoria_pretendida,
)

from .forms import separar_nome
from .models import Ambulante

ESCOLARIDADE_CHOICES = (
    ("", "Selecione..."),
    ("fundamental_incompleto", "Ensino Fundamental Incompleto"),
    ("fundamental_completo", "Ensino Fundamental Completo"),
    ("medio_incompleto", "Ensino Médio Incompleto"),
    ("medio_completo", "Ensino Médio Completo"),
    ("superior", "Ensino Superior (Incompleto / Completo)"),
)

TIPO_COMERCIO_CHOICES = (
    ("", "Selecione..."),
    ("fixo", "Ambulante Fixo (Ponto Autorizado)"),
    ("movel", "Ambulante Móvel (Itinerante)"),
    ("eventual", "Eventual / Temporário (Festas)"),
)

TIPO_ESTRUTURA_CHOICES = (
    ("", "Selecione..."),
    ("carrinho", "Carrinho"),
    ("banca", "Banca"),
    ("tabuleiro", "Tabuleiro"),
    ("veiculo", "Veículo / Reboque / Food Truck"),
)


def normalizar_cnpj(valor):
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def _incluir_valor_atual(choices, valor):
    opcoes = list(choices)
    if valor and valor not in {item[0] for item in opcoes}:
        opcoes.append((valor, valor))
    return opcoes


def atualizar_complementares(ambulante, **campos):
    dados = dict(ambulante.dados_complementares or {})
    for chave, valor in campos.items():
        if valor in (None, ""):
            dados.pop(chave, None)
        else:
            dados[chave] = valor
    ambulante.dados_complementares = dados
    ambulante.save(update_fields=["dados_complementares"])


class DadosPessoaisCadastroForm(forms.Form):
    nome_completo = forms.CharField(
        label="Nome Completo",
        max_length=300,
        widget=forms.TextInput(
            attrs={"id": "req-nome", "placeholder": "Nome completo do requerente"}
        ),
    )
    data_nasc = forms.DateField(
        label="Data de Nascimento",
        widget=forms.DateInput(
            attrs={"id": "req-data-nasc", "type": "date"},
            format="%Y-%m-%d",
        ),
    )
    telefone_whatsapp = forms.CharField(
        label="Telefone Principal (WhatsApp)",
        max_length=20,
        widget=forms.TextInput(
            attrs={"id": "req-tel", "placeholder": "(77) 90000-0000", "maxlength": "15"}
        ),
    )
    telefone_2 = forms.CharField(
        label="Telefone Secundário / Recado",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "req-tel-2",
                "placeholder": "(77) 90000-0000",
                "maxlength": "15",
            }
        ),
    )
    nis = forms.CharField(
        label="NIS (CadÚnico)",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"id": "req-nis", "placeholder": "Digite o número do NIS"}
        ),
    )
    sem_nis = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"id": "check-no-nis"}),
    )
    escolaridade = forms.ChoiceField(
        label="Grau de Escolaridade",
        choices=ESCOLARIDADE_CHOICES,
        widget=forms.Select(attrs={"id": "req-escolaridade", "class": "styled-select"}),
    )
    num_funcionarios = forms.IntegerField(
        label="Qtd de Auxiliares",
        min_value=0,
        max_value=20,
        initial=0,
        widget=forms.NumberInput(attrs={"id": "req-num-funcionarios", "min": "0"}),
    )
    foto = forms.ImageField(
        label="Foto 3x4 (opcional)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"id": "req-foto", "accept": "image/*"}),
    )
    rg = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"id": "req-rg", "placeholder": "Número do RG"}),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        if ambulante:
            extras = ambulante.dados_complementares or {}
            self.fields["escolaridade"].choices = _incluir_valor_atual(
                ESCOLARIDADE_CHOICES, ambulante.escolaridade
            )
            self.fields["data_nasc"].input_formats = ["%Y-%m-%d"]
            if not args:
                self.fields["nome_completo"].initial = (
                    f"{ambulante.nome} {ambulante.sobrenome}".strip()
                )
                self.fields["data_nasc"].initial = ambulante.data_nasc
                self.fields["telefone_whatsapp"].initial = ambulante.telefone_whatsapp
                self.fields["telefone_2"].initial = ambulante.telefone_2 or ""
                self.fields["nis"].initial = ambulante.nis or ""
                self.fields["sem_nis"].initial = extras.get("sem_nis", False)
                self.fields["escolaridade"].initial = ambulante.escolaridade
                self.fields["num_funcionarios"].initial = ambulante.num_funcionarios
                self.fields["rg"].initial = extras.get("rg", "")

    def clean(self):
        dados = super().clean()
        if dados.get("sem_nis"):
            dados["nis"] = ""
        return dados

    def save(self):
        ambulante = self.ambulante
        nome, sobrenome = separar_nome(self.cleaned_data["nome_completo"])
        ambulante.nome = nome
        ambulante.sobrenome = sobrenome
        ambulante.data_nasc = self.cleaned_data["data_nasc"]
        ambulante.telefone_whatsapp = self.cleaned_data["telefone_whatsapp"]
        ambulante.telefone_2 = self.cleaned_data.get("telefone_2") or None
        ambulante.nis = self.cleaned_data.get("nis") or None
        ambulante.escolaridade = self.cleaned_data["escolaridade"]
        ambulante.num_funcionarios = self.cleaned_data["num_funcionarios"]
        if self.cleaned_data.get("foto"):
            ambulante.foto = self.cleaned_data["foto"]
        ambulante.save()
        atualizar_complementares(
            ambulante,
            rg=self.cleaned_data.get("rg", ""),
            sem_nis=self.cleaned_data.get("sem_nis", False),
        )
        return ambulante


class EnderecoCadastroForm(forms.Form):
    cep = forms.CharField(
        label="CEP",
        max_length=9,
        widget=forms.TextInput(
            attrs={"id": "cep-input", "placeholder": "00000-000", "maxlength": "9"}
        ),
    )
    logradouro = forms.CharField(
        label="Endereço",
        max_length=255,
        widget=forms.TextInput(
            attrs={"id": "endereco-input", "placeholder": "Nome da rua ou avenida"}
        ),
    )
    numero = forms.CharField(
        label="Número",
        max_length=20,
        widget=forms.TextInput(attrs={"id": "numero-input", "placeholder": "Nº"}),
    )
    complemento = forms.CharField(
        label="Complemento",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"id": "complemento-input", "placeholder": "Apto, Bloco, Casa 2..."}
        ),
    )
    bairro = forms.CharField(
        label="Bairro",
        max_length=100,
        widget=forms.TextInput(
            attrs={"id": "bairro-input", "placeholder": "Nome do bairro"}
        ),
    )
    estado_uf = forms.CharField(
        label="Estado (UF)",
        max_length=2,
        widget=forms.Select(
            attrs={"id": "estado-input", "class": "styled-select", "name": "estado_uf"}
        ),
    )
    cidade = forms.CharField(
        label="Cidade",
        max_length=100,
        widget=forms.Select(
            attrs={"id": "cidade-input", "class": "styled-select", "name": "cidade"}
        ),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        endereco = (
            ambulante.enderecos.order_by("id").first()
            if ambulante and ambulante.pk
            else None
        )
        if endereco and not args:
            for campo in (
                "cep",
                "logradouro",
                "numero",
                "complemento",
                "bairro",
                "estado_uf",
                "cidade",
            ):
                self.fields[campo].initial = getattr(endereco, campo) or ""

    def save(self):
        dados = self.cleaned_data
        endereco = self.ambulante.enderecos.order_by("id").first()
        if endereco is None:
            endereco = Endereco(ambulante=self.ambulante)
        endereco.cep = dados["cep"]
        endereco.logradouro = dados["logradouro"]
        endereco.numero = dados["numero"]
        endereco.complemento = dados.get("complemento") or None
        endereco.bairro = dados["bairro"]
        endereco.estado_uf = dados["estado_uf"].upper()
        endereco.cidade = dados["cidade"]
        endereco.save()
        return endereco


class EmpresaCadastroForm(forms.Form):
    sem_cnpj = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"id": "check-no-cnpj"}),
    )
    cnpj = forms.CharField(
        label="CNPJ",
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "pj-cnpj",
                "placeholder": "00.000.000/0001-00",
                "maxlength": "18",
            }
        ),
    )
    apelido_nome_fantasia = forms.CharField(
        label="Nome Fantasia / Apelido",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"id": "pj-fantasia", "placeholder": "Nome do ponto/comércio"}
        ),
    )
    razao_social = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"id": "pj-razao", "placeholder": "Nome empresarial"}
        ),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        if ambulante and not args:
            extras = ambulante.dados_complementares or {}
            self.fields["cnpj"].initial = ambulante.cnpj or ""
            self.fields["sem_cnpj"].initial = extras.get("sem_cnpj", not ambulante.cnpj)
            self.fields["apelido_nome_fantasia"].initial = (
                ambulante.apelido_nome_fantasia or ""
            )
            self.fields["razao_social"].initial = extras.get("razao_social", "")

    def clean_cnpj(self):
        return normalizar_cnpj(self.cleaned_data.get("cnpj", ""))

    def clean(self):
        dados = super().clean()
        if dados.get("sem_cnpj"):
            dados["cnpj"] = ""
            return dados
        cnpj = dados.get("cnpj") or ""
        if cnpj and len(cnpj) != 14:
            self.add_error("cnpj", "Informe um CNPJ com 14 dígitos.")
        elif cnpj:
            duplicado = (
                Ambulante.objects.filter(cnpj=cnpj)
                .exclude(pk=self.ambulante.pk)
                .exists()
            )
            if duplicado:
                self.add_error("cnpj", "Já existe um ambulante com este CNPJ.")
        return dados

    def save(self):
        ambulante = self.ambulante
        ambulante.cnpj = self.cleaned_data.get("cnpj") or None
        ambulante.apelido_nome_fantasia = (
            self.cleaned_data.get("apelido_nome_fantasia") or None
        )
        ambulante.save(update_fields=["cnpj", "apelido_nome_fantasia", "atualizado_em"])
        atualizar_complementares(
            ambulante,
            sem_cnpj=self.cleaned_data.get("sem_cnpj", False),
            razao_social=self.cleaned_data.get("razao_social", ""),
        )
        return ambulante


class EstruturaCadastroForm(forms.Form):
    tipo_atuacao = forms.ChoiceField(
        label="Tipo de Comércio",
        choices=TIPO_COMERCIO_CHOICES,
        widget=forms.Select(attrs={"id": "tipo-comercio", "class": "styled-select"}),
    )
    tipo_estrutura = forms.ChoiceField(
        label="Tipo de Estrutura",
        choices=TIPO_ESTRUTURA_CHOICES,
        widget=forms.Select(
            attrs={"id": "categoria-equipamento", "class": "styled-select"}
        ),
    )
    descricao = forms.CharField(
        label="Descrição / mercadoria",
        widget=forms.TextInput(
            attrs={
                "id": "especie-mercadoria",
                "placeholder": "Lanches, vestuário...",
            }
        ),
    )
    dimensoes_metragem = forms.DecimalField(
        label="Metragem utilizada (m²)",
        min_value=Decimal("0.01"),
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "id": "metragem-utilizada",
                "placeholder": "Ex: 2.50",
                "step": "0.01",
                "min": "0.01",
            }
        ),
    )
    foto_estrutura = forms.ImageField(
        label="Foto da estrutura (opcional)",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"id": "foto-estrutura", "accept": "image/*"}
        ),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        estrutura = (
            ambulante.estruturas.order_by("id").first()
            if ambulante and ambulante.pk
            else None
        )
        if ambulante:
            self.fields["tipo_atuacao"].choices = _incluir_valor_atual(
                TIPO_COMERCIO_CHOICES, ambulante.tipo_atuacao
            )
            if estrutura:
                self.fields["tipo_estrutura"].choices = _incluir_valor_atual(
                    TIPO_ESTRUTURA_CHOICES, estrutura.tipo_estrutura
                )
            if not args:
                self.fields["tipo_atuacao"].initial = ambulante.tipo_atuacao
                if estrutura:
                    self.fields["tipo_estrutura"].initial = estrutura.tipo_estrutura
                    self.fields["descricao"].initial = estrutura.descricao
                    self.fields["dimensoes_metragem"].initial = (
                        estrutura.dimensoes_metragem
                    )

    def clean_dimensoes_metragem(self):
        metragem = self.cleaned_data["dimensoes_metragem"]
        if metragem is None or metragem <= 0:
            raise ValidationError("Informe uma metragem positiva.")
        return metragem

    def save(self):
        ambulante = self.ambulante
        ambulante.tipo_atuacao = self.cleaned_data["tipo_atuacao"]
        ambulante.save(update_fields=["tipo_atuacao", "atualizado_em"])
        estrutura = ambulante.estruturas.order_by("id").first()
        if estrutura is None:
            estrutura = EstruturaTrabalho(ambulante=ambulante)
        estrutura.tipo_estrutura = self.cleaned_data["tipo_estrutura"]
        estrutura.descricao = self.cleaned_data["descricao"]
        estrutura.dimensoes_metragem = self.cleaned_data["dimensoes_metragem"]
        if self.cleaned_data.get("foto_estrutura"):
            estrutura.foto_estrutura = self.cleaned_data["foto_estrutura"]
        estrutura.save()
        return estrutura


class CategoriaCatalogoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        extras = []
        if obj.exige_laudo_sanitario:
            extras.append("laudo sanitário")
        if obj.exige_laudo_bombeiros:
            extras.append("bombeiros")
        if extras:
            return f"{obj.nome_categoria} ({', '.join(extras)})"
        return obj.nome_categoria


class PontoCadastroForm(forms.Form):
    categoria_pretendida = CategoriaCatalogoChoiceField(
        label="Categoria de produto",
        queryset=CategoriaProduto.objects.none(),
        required=False,
        empty_label="Selecione a categoria (opcional)",
        widget=forms.Select(
            attrs={"id": "categoria-pretendida", "class": "styled-select"}
        ),
    )
    ponto_pretendido = forms.ModelChoiceField(
        label="Ponto desejado",
        queryset=PontoOcupacao.objects.none(),
        required=False,
        empty_label="Selecione um ponto do catálogo (opcional)",
        widget=forms.Select(attrs={"id": "ponto-pretendido", "class": "styled-select"}),
    )

    def __init__(self, *args, ambulante=None, **kwargs):
        self.ambulante = ambulante
        super().__init__(*args, **kwargs)
        categorias = CategoriaProduto.objects.filter(ativo=True).order_by(
            "nome_categoria"
        )
        self.fields["categoria_pretendida"].queryset = categorias
        pontos = PontoOcupacao.objects.livres().order_by("nome_identificacao")
        if ambulante and ambulante.ponto_pretendido_id:
            pontos = PontoOcupacao.objects.filter(
                Q(pk__in=pontos.values("pk")) | Q(pk=ambulante.ponto_pretendido_id)
            ).order_by("nome_identificacao")
        self.fields["ponto_pretendido"].queryset = pontos
        if ambulante and not args:
            self.fields["ponto_pretendido"].initial = ambulante.ponto_pretendido_id
            categoria = categoria_do_ambulante(ambulante)
            if categoria:
                self.fields["categoria_pretendida"].initial = categoria.pk

    def clean_ponto_pretendido(self):
        ponto = self.cleaned_data.get("ponto_pretendido")
        if not ponto:
            return ponto
        atual_id = getattr(self.ambulante, "ponto_pretendido_id", None)
        if ponto.pk != atual_id and not ponto.disponivel_para_nova_atribuicao():
            raise ValidationError("Este ponto não está livre para nova ocupação.")
        estrutura = None
        if self.ambulante:
            estrutura = self.ambulante.estruturas.order_by("id").first()
        if (
            estrutura
            and estrutura.dimensoes_metragem
            and not ponto.metragem_compativel(estrutura.dimensoes_metragem)
        ):
            raise ValidationError(
                "A metragem da sua estrutura "
                f"({estrutura.dimensoes_metragem} m²) ultrapassa o máximo "
                f"deste ponto ({ponto.metragem_maxima} m²)."
            )
        return ponto

    def save(self):
        self.ambulante.ponto_pretendido = self.cleaned_data.get("ponto_pretendido")
        self.ambulante.save(update_fields=["ponto_pretendido", "atualizado_em"])
        categoria = self.cleaned_data.get("categoria_pretendida")
        gravar_categoria_pretendida(self.ambulante, categoria)
        return self.ambulante


class AnexosCadastroForm(AnexosDocumentosForm):
    """Etapa 6 do cadastro: upload e reenvio de documentos."""
