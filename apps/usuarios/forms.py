from typing import ClassVar

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .lgpd import BASE_LEGAL_LGPD
from .models import (
    Ambulante,
    ConfiguracaoSeguranca,
    Fiscal,
    Gestor,
    Perfil,
    UsuarioBase,
)
from .seguranca import (
    CELULAS_EDITAVEIS,
    MODULOS_PERMISSAO,
    PERFIS_MATRIZ,
    campo_matriz,
    matriz_padrao,
)

LOGIN_INVALIDO = (
    "CPF/e-mail ou senha inválidos. Confira os dados ou use Esqueci minha senha."
)


def attrs_campo(base, *, hint="", **extra):
    attrs = dict(base)
    if hint:
        attrs["data-hint"] = hint
    attrs.update(extra)
    return attrs


def normalizar_cpf(valor):
    return "".join(ch for ch in valor if ch.isdigit())


def separar_nome(nome_completo):
    partes = nome_completo.strip().split()
    if not partes:
        return "", ""
    if len(partes) == 1:
        return partes[0], partes[0]
    return partes[0], " ".join(partes[1:])


SECRETARIA_CHOICES = (
    (
        "SESEP - Serviços Públicos (Posturas)",
        "SESEP - Serviços Públicos (Posturas)",
    ),
    (
        "Vigilância Sanitária Municipal",
        "Vigilância Sanitária Municipal",
    ),
    (
        "SEFIN - Secretaria de Finanças / Tributos",
        "SEFIN - Secretaria de Finanças / Tributos",
    ),
    (
        "SEINFRA - Infraestrutura Urbana",
        "SEINFRA - Infraestrutura Urbana",
    ),
    (
        "Gabinete da Prefeita / Governo",
        "Gabinete da Prefeita / Governo",
    ),
)

ZONA_CHOICES = (
    (
        "Centro Comercial / Praça 9 de Novembro",
        "Centro Comercial / Praça 9 de Novembro",
    ),
    (
        "Feira do Bairro Brasil / Zona Oeste",
        "Feira do Bairro Brasil / Zona Oeste",
    ),
    ("Terminal Lauro de Freitas", "Terminal Lauro de Freitas"),
    (
        "Região do Ceasa / Centro Histórico",
        "Região do Ceasa / Centro Histórico",
    ),
    (
        "Fiscalização Itinerante / Eventos",
        "Fiscalização Itinerante / Eventos",
    ),
)


class LoginBackofficeForm(AuthenticationForm):
    """Login web exclusivo para Gestores e Administradores."""

    error_messages: ClassVar[dict[str, str]] = {
        "invalid_login": LOGIN_INVALIDO,
        "inactive": "Esta conta está inativa. Fale com a administração da prefeitura.",
        "sem_acesso_backoffice": (
            "Este perfil não acessa o backoffice. "
            "Ambulantes devem entrar em /entrar/ e fiscais em /fiscal/entrar/."
        ),
        "usuario_inativo": (
            "Usuário inativo. Fale com a administração para reativar o acesso."
        ),
    }

    username = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "user-login",
                    "placeholder": "Digite seu CPF ou e-mail",
                    "autocomplete": "username",
                    "autofocus": True,
                },
                hint="Use o e-mail institucional ou o CPF com 11 dígitos.",
            )
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "user-password",
                    "placeholder": "Digite sua senha",
                    "autocomplete": "current-password",
                },
                hint="A senha diferencia maiúsculas e minúsculas.",
            )
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.ativo:
            raise ValidationError(
                self.error_messages["usuario_inativo"],
                code="usuario_inativo",
            )
        if user.role not in (Perfil.GESTOR, Perfil.ADMINISTRADOR):
            raise ValidationError(
                self.error_messages["sem_acesso_backoffice"],
                code="sem_acesso_backoffice",
            )


class LoginAmbulanteForm(AuthenticationForm):
    """Login web exclusivo para comerciantes ambulantes."""

    error_messages: ClassVar[dict[str, str]] = {
        "invalid_login": LOGIN_INVALIDO,
        "inactive": "Esta conta está inativa. Fale com a administração da prefeitura.",
        "sem_acesso_ambulante": (
            "Este acesso é exclusivo para comerciantes ambulantes. "
            "Gestores entram no backoffice e fiscais em /fiscal/entrar/."
        ),
        "usuario_inativo": (
            "Usuário inativo. Fale com a administração para reativar o acesso."
        ),
    }

    username = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "user-login",
                    "placeholder": "Digite seu CPF ou e-mail",
                    "autocomplete": "username",
                    "autofocus": True,
                },
                hint="Use o e-mail cadastrado ou o CPF com 11 dígitos.",
            )
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "user-password",
                    "placeholder": "Digite sua senha",
                    "autocomplete": "current-password",
                },
                hint="A senha diferencia maiúsculas e minúsculas.",
            )
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.ativo:
            raise ValidationError(
                self.error_messages["usuario_inativo"],
                code="usuario_inativo",
            )
        if user.role != Perfil.AMBULANTE:
            raise ValidationError(
                self.error_messages["sem_acesso_ambulante"],
                code="sem_acesso_ambulante",
            )


class LoginFiscalForm(AuthenticationForm):
    """Login web exclusivo para fiscais de campo."""

    error_messages: ClassVar[dict[str, str]] = {
        "invalid_login": LOGIN_INVALIDO,
        "inactive": "Esta conta está inativa. Fale com a administração da prefeitura.",
        "sem_acesso_fiscal": (
            "Este acesso é exclusivo para fiscais. "
            "Ambulantes entram em /entrar/ e a prefeitura no backoffice."
        ),
        "usuario_inativo": (
            "Usuário inativo. Fale com a administração para reativar o acesso."
        ),
    }

    username = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "user-login",
                    "placeholder": "Digite seu CPF ou e-mail",
                    "autocomplete": "username",
                    "autofocus": True,
                },
                hint="Use o e-mail institucional ou o CPF com 11 dígitos.",
            )
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "user-password",
                    "placeholder": "Digite sua senha",
                    "autocomplete": "current-password",
                },
                hint="A senha diferencia maiúsculas e minúsculas.",
            )
        ),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.ativo:
            raise ValidationError(
                self.error_messages["usuario_inativo"],
                code="usuario_inativo",
            )
        if user.role != Perfil.FISCAL:
            raise ValidationError(
                self.error_messages["sem_acesso_fiscal"],
                code="sem_acesso_fiscal",
            )


class RecuperarSenhaForm(PasswordResetForm):
    email = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "recovery-email",
                    "placeholder": "seu-email@dominio.com ou CPF",
                    "autocomplete": "username",
                },
                hint="Informe o mesmo e-mail ou CPF usado no cadastro. O link chega no e-mail da conta.",
            )
        ),
        error_messages={
            "required": "Informe o e-mail ou o CPF da conta para enviar o link.",
        },
    )

    def get_users(self, email):
        identificador = (email or "").strip()
        if not identificador:
            return []
        if "@" in identificador:
            usuarios = UsuarioBase.objects.filter(
                email__iexact=identificador,
                is_active=True,
                ativo=True,
            )
        else:
            usuarios = UsuarioBase.objects.filter(
                cpf=normalizar_cpf(identificador),
                is_active=True,
                ativo=True,
            )
        return (usuario for usuario in usuarios if usuario.has_usable_password())


class NovaSenhaForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            attrs_campo(
                {
                    "id": "nova-senha",
                    "placeholder": "Digite a nova senha",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Use no mínimo 8 caracteres, misturando letras. Evite senhas só numéricas.",
            )
        )
        self.fields["new_password2"].widget.attrs.update(
            attrs_campo(
                {
                    "id": "nova-senha-confirmacao",
                    "placeholder": "Repita a nova senha",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Repita a mesma senha para confirmar.",
            )
        )


class CadastroUsuarioMasterMixin:
    def clean_cpf(self):
        cpf = normalizar_cpf(self.cleaned_data.get("cpf", ""))
        if len(cpf) != 11:
            raise ValidationError(
                "Informe os 11 dígitos do CPF. Exemplo: 000.000.000-00."
            )
        if UsuarioBase.objects.filter(cpf=cpf).exists():
            raise ValidationError("Já existe um usuário com este CPF.")
        return cpf

    def clean_email(self):
        email = UsuarioBase.objects.normalize_email(self.cleaned_data["email"])
        if UsuarioBase.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe um usuário com este e-mail.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class CadastroAmbulanteForm(CadastroUsuarioMasterMixin, forms.Form):
    nome_completo = forms.CharField(
        label="Nome Completo",
        max_length=300,
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "reg-nome",
                    "placeholder": "Digite seu nome completo",
                    "autocomplete": "name",
                },
                hint="Informe nome e sobrenome, como no documento.",
            )
        ),
    )
    email = forms.EmailField(
        label="E-mail de Acesso",
        error_messages={
            "invalid": "Digite um e-mail no formato nome@dominio.com.",
            "required": "Informe um e-mail para receber avisos e recuperar a senha.",
        },
        widget=forms.EmailInput(
            attrs=attrs_campo(
                {
                    "id": "reg-email",
                    "placeholder": "seu-email@dominio.com",
                    "autocomplete": "email",
                },
                hint="Este e-mail será o login e o destino da recuperação de senha.",
            )
        ),
    )
    cpf = forms.CharField(
        label="CPF",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "cpf-cadastro",
                    "placeholder": "000.000.000-00",
                    "autocomplete": "username",
                    "inputmode": "numeric",
                    "maxlength": "14",
                },
                hint="Digite só os números; a máscara é aplicada automaticamente.",
            )
        ),
    )
    telefone_whatsapp = forms.CharField(
        label="Telefone / WhatsApp",
        max_length=20,
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "reg-telefone",
                    "placeholder": "(77) 99999-0000",
                    "autocomplete": "tel",
                    "inputmode": "numeric",
                    "maxlength": "15",
                },
                hint="DDD + número. Exemplo: (77) 99999-0000.",
            )
        ),
    )
    password = forms.CharField(
        label="Senha de Acesso",
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "reg-password",
                    "placeholder": "Mínimo de 8 caracteres",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Mínimo de 8 caracteres. Evite senha só com números.",
            )
        ),
    )
    password_confirm = forms.CharField(
        label="Confirmar Senha",
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "reg-confirm-password",
                    "placeholder": "Repita a senha",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Repita a mesma senha do campo anterior.",
            )
        ),
    )
    aceite_lgpd = forms.BooleanField(
        label=(
            "Li e aceito o tratamento dos meus dados pessoais para o licenciamento "
            "e a fiscalização do comércio ambulante, nos termos da LGPD."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"id": "aceite-lgpd"}),
    )

    def clean(self):
        dados = super().clean()
        senha = dados.get("password")
        confirmacao = dados.get("password_confirm")
        if senha and confirmacao and senha != confirmacao:
            self.add_error(
                "password_confirm",
                "As senhas não coincidem. Digite a mesma senha nos dois campos.",
            )
        return dados

    def clean_telefone_whatsapp(self):
        numeros = "".join(
            ch for ch in (self.cleaned_data.get("telefone_whatsapp") or "") if ch.isdigit()
        )
        if len(numeros) < 10:
            raise ValidationError(
                "Informe DDD e número, só com dígitos. Exemplo: (77) 99999-0000."
            )
        return numeros

    def save(self):
        dados = self.cleaned_data
        nome, sobrenome = separar_nome(dados["nome_completo"])
        return Ambulante.objects.create_user(
            cpf=dados["cpf"],
            email=dados["email"],
            password=dados["password"],
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp=dados["telefone_whatsapp"],
            aceite_lgpd=True,
            aceite_lgpd_em=timezone.now(),
            base_legal_lgpd=BASE_LEGAL_LGPD,
        )


class CadastroGestorForm(CadastroUsuarioMasterMixin, forms.Form):
    nome_completo = forms.CharField(
        label="Nome Completo do Gestor",
        max_length=300,
        widget=forms.TextInput(
            attrs={
                "id": "gestor-nome",
                "placeholder": "Ex: Dra. Mariana Almeida",
            }
        ),
    )
    cpf = forms.CharField(
        label="CPF do Servidor",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "gestor-cpf",
                    "placeholder": "000.000.000-00",
                    "inputmode": "numeric",
                    "maxlength": "14",
                },
                hint="Digite os 11 números do CPF do servidor.",
            )
        ),
    )
    email = forms.EmailField(
        label="E-mail Institucional",
        error_messages={
            "invalid": "Digite um e-mail no formato nome@dominio.com.",
        },
        widget=forms.EmailInput(
            attrs=attrs_campo(
                {
                    "id": "gestor-email",
                    "placeholder": "gestor.nome@pmvc.ba.gov.br",
                },
                hint="Use o e-mail institucional da prefeitura.",
            )
        ),
    )
    telefone_whatsapp = forms.CharField(
        label="Telefone / Ramal de Contato",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "id": "gestor-telefone",
                "placeholder": "(77) 3229-0000",
            }
        ),
    )
    departamento = forms.ChoiceField(
        label="Secretaria / Órgão Vinculado",
        choices=(("", "Selecione a secretaria..."),) + SECRETARIA_CHOICES,
        widget=forms.Select(attrs={"id": "gestor-secretaria"}),
    )
    cargo = forms.CharField(
        label="Cargo / Função Institucional",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "id": "gestor-cargo",
                "placeholder": "Ex: Coordenadora de Licenciamento",
            }
        ),
    )
    password = forms.CharField(
        label="Senha Provisória de Acesso",
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "gestor-senha",
                    "placeholder": "Crie uma senha provisória de acesso",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Mínimo de 8 caracteres. O gestor poderá alterar depois.",
            )
        ),
    )

    def save(self):
        dados = self.cleaned_data
        nome, sobrenome = separar_nome(dados["nome_completo"])
        cpf = dados["cpf"]
        return Gestor.objects.create_user(
            cpf=cpf,
            email=dados["email"],
            password=dados["password"],
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp=dados["telefone_whatsapp"],
            matricula_funcional=f"GES-{cpf}",
            cargo=dados["cargo"],
            departamento=dados["departamento"],
            is_staff=True,
        )


class CadastroFiscalForm(CadastroUsuarioMasterMixin, forms.Form):
    nome_completo = forms.CharField(
        label="Nome Completo do Agente",
        max_length=300,
        widget=forms.TextInput(
            attrs={
                "id": "fiscal-nome",
                "placeholder": "Ex: Carlos Eduardo Moreira",
            }
        ),
    )
    matricula_funcional = forms.CharField(
        label="Número da Matrícula",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "id": "fiscal-matricula",
                "placeholder": "Ex: #4599",
            }
        ),
    )
    cpf = forms.CharField(
        label="CPF do Agente",
        widget=forms.TextInput(
            attrs=attrs_campo(
                {
                    "id": "fiscal-cpf",
                    "placeholder": "000.000.000-00",
                    "inputmode": "numeric",
                    "maxlength": "14",
                },
                hint="Digite os 11 números do CPF do agente.",
            )
        ),
    )
    email = forms.EmailField(
        label="E-mail Institucional",
        error_messages={
            "invalid": "Digite um e-mail no formato nome@dominio.com.",
        },
        widget=forms.EmailInput(
            attrs=attrs_campo(
                {
                    "id": "fiscal-email",
                    "placeholder": "fiscal.nome@pmvc.ba.gov.br",
                },
                hint="Use o e-mail institucional da prefeitura.",
            )
        ),
    )
    zona_atuacao_primaria = forms.ChoiceField(
        label="Zona / Setor de Atuação Principal",
        choices=(("", "Selecione a zona..."),) + ZONA_CHOICES,
        widget=forms.Select(attrs={"id": "fiscal-zona"}),
    )
    password = forms.CharField(
        label="Senha Provisória",
        widget=forms.PasswordInput(
            attrs=attrs_campo(
                {
                    "id": "fiscal-senha",
                    "placeholder": "Crie uma senha provisória",
                    "autocomplete": "new-password",
                    "minlength": "8",
                },
                hint="Mínimo de 8 caracteres. O fiscal poderá alterar depois.",
            )
        ),
    )

    def clean_matricula_funcional(self):
        matricula = self.cleaned_data["matricula_funcional"].strip()
        if Fiscal.objects.filter(matricula_funcional=matricula).exists():
            raise ValidationError("Já existe um fiscal com esta matrícula.")
        return matricula

    def save(self):
        dados = self.cleaned_data
        nome, sobrenome = separar_nome(dados["nome_completo"])
        return Fiscal.objects.create_user(
            cpf=dados["cpf"],
            email=dados["email"],
            password=dados["password"],
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp="",
            matricula_funcional=dados["matricula_funcional"],
            zona_atuacao_primaria=dados["zona_atuacao_primaria"],
            is_staff=True,
        )


class ConfiguracaoSegurancaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoSeguranca
        fields = (
            "tempo_sessao_minutos",
            "tentativas_bloqueio",
            "exigencia_2fa",
            "retencao_logs_meses",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tempo_sessao_minutos"].widget.attrs["id"] = "tempo-sessao"
        self.fields["tentativas_bloqueio"].widget.attrs["id"] = "tentativas-login"
        self.fields["exigencia_2fa"].widget.attrs["id"] = "autenticacao-2fa"
        self.fields["retencao_logs_meses"].widget.attrs["id"] = "retencao-logs"
        matriz = self.instance.matriz or matriz_padrao()
        for modulo, perfis in CELULAS_EDITAVEIS.items():
            for perfil in perfis:
                nome = campo_matriz(modulo, perfil)
                self.fields[nome] = forms.BooleanField(
                    required=False,
                    initial=bool(matriz.get(modulo, {}).get(perfil, False)),
                )

    @property
    def linhas_matriz(self):
        linhas = []
        for modulo, rotulo in MODULOS_PERMISSAO:
            celulas = []
            for perfil, _rotulo_perfil in PERFIS_MATRIZ:
                nome = campo_matriz(modulo, perfil)
                if nome in self.fields:
                    celulas.append({"editavel": True, "campo": self[nome]})
                else:
                    celulas.append({"editavel": False})
            linhas.append({"rotulo": rotulo, "celulas": celulas})
        return linhas

    def save(self, commit=True):
        instancia = super().save(commit=False)
        matriz = {}
        for modulo, perfis in CELULAS_EDITAVEIS.items():
            matriz[modulo] = {
                perfil: bool(self.cleaned_data.get(campo_matriz(modulo, perfil)))
                for perfil in perfis
            }
        instancia.matriz = matriz
        if commit:
            instancia.save()
        return instancia
