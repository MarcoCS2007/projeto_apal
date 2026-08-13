from typing import ClassVar

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Perfil


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
