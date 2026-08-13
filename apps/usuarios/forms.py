from typing import ClassVar

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Ambulante, Fiscal, Gestor, Perfil, UsuarioBase


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
        "invalid_login": "CPF/e-mail ou senha inválidos.",
        "inactive": "Esta conta está inativa.",
        "sem_acesso_backoffice": (
            "Este perfil não possui acesso ao backoffice. "
            "O acesso web é exclusivo para Gestores e Administradores."
        ),
        "usuario_inativo": "Usuário inativo. Entre em contato com a administração.",
    }

    username = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs={
                "id": "user-login",
                "placeholder": "Digite seu CPF ou e-mail",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "id": "user-password",
                "placeholder": "Digite sua senha",
                "autocomplete": "current-password",
            }
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
        "invalid_login": "CPF/e-mail ou senha inválidos.",
        "inactive": "Esta conta está inativa.",
        "sem_acesso_ambulante": (
            "Este acesso é exclusivo para comerciantes ambulantes. "
            "Gestores e administradores devem usar o backoffice."
        ),
        "usuario_inativo": "Usuário inativo. Entre em contato com a administração.",
    }

    username = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs={
                "id": "user-login",
                "placeholder": "Digite seu CPF ou e-mail",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "id": "user-password",
                "placeholder": "Digite sua senha",
                "autocomplete": "current-password",
            }
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


class RecuperarSenhaForm(PasswordResetForm):
    email = forms.CharField(
        label="E-mail ou CPF",
        widget=forms.TextInput(
            attrs={
                "id": "recovery-email",
                "placeholder": "seu-email@dominio.com ou CPF",
                "autocomplete": "username",
            }
        ),
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
            {
                "id": "nova-senha",
                "placeholder": "Digite a nova senha",
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].widget.attrs.update(
            {
                "id": "nova-senha-confirmacao",
                "placeholder": "Repita a nova senha",
                "autocomplete": "new-password",
            }
        )


class CadastroUsuarioMasterMixin:
    def clean_cpf(self):
        cpf = normalizar_cpf(self.cleaned_data.get("cpf", ""))
        if len(cpf) != 11:
            raise ValidationError("Informe um CPF com 11 dígitos.")
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
            attrs={
                "id": "reg-nome",
                "placeholder": "Digite seu nome completo",
                "autocomplete": "name",
            }
        ),
    )
    email = forms.EmailField(
        label="E-mail de Acesso",
        widget=forms.EmailInput(
            attrs={
                "id": "reg-email",
                "placeholder": "seu-email@dominio.com",
                "autocomplete": "email",
            }
        ),
    )
    cpf = forms.CharField(
        label="CPF",
        widget=forms.TextInput(
            attrs={
                "id": "cpf-cadastro",
                "placeholder": "000.000.000-00",
                "autocomplete": "username",
            }
        ),
    )
    telefone_whatsapp = forms.CharField(
        label="Telefone / WhatsApp",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "id": "reg-telefone",
                "placeholder": "(77) 99999-0000",
                "autocomplete": "tel",
            }
        ),
    )
    password = forms.CharField(
        label="Senha de Acesso",
        widget=forms.PasswordInput(
            attrs={
                "id": "reg-password",
                "placeholder": "Mínimo de 8 caracteres",
                "autocomplete": "new-password",
            }
        ),
    )
    password_confirm = forms.CharField(
        label="Confirmar Senha",
        widget=forms.PasswordInput(
            attrs={
                "id": "reg-confirm-password",
                "placeholder": "Repita a senha",
                "autocomplete": "new-password",
            }
        ),
    )
    foto = forms.ImageField(
        label="Foto (opcional)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"id": "reg-foto", "accept": "image/*"}),
    )

    def clean(self):
        dados = super().clean()
        senha = dados.get("password")
        confirmacao = dados.get("password_confirm")
        if senha and confirmacao and senha != confirmacao:
            self.add_error("password_confirm", "As senhas não coincidem.")
        return dados

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
            foto=dados.get("foto") or None,
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
            attrs={
                "id": "gestor-cpf",
                "placeholder": "000.000.000-00",
            }
        ),
    )
    email = forms.EmailField(
        label="E-mail Institucional",
        widget=forms.EmailInput(
            attrs={
                "id": "gestor-email",
                "placeholder": "gestor.nome@pmvc.ba.gov.br",
            }
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
            attrs={
                "id": "gestor-senha",
                "placeholder": "Crie uma senha provisória de acesso",
                "autocomplete": "new-password",
            }
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
            attrs={
                "id": "fiscal-cpf",
                "placeholder": "000.000.000-00",
            }
        ),
    )
    email = forms.EmailField(
        label="E-mail Institucional",
        widget=forms.EmailInput(
            attrs={
                "id": "fiscal-email",
                "placeholder": "fiscal.nome@pmvc.ba.gov.br",
            }
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
            attrs={
                "id": "fiscal-senha",
                "placeholder": "Crie uma senha provisória",
                "autocomplete": "new-password",
            }
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
