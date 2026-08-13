from django import forms
from django.contrib import admin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .forms import normalizar_cpf
from .models import Administrador, Ambulante, Fiscal, Gestor, UsuarioBase

admin.site.site_header = "APAL — Administração"
admin.site.site_title = "APAL Admin"
admin.site.index_title = "Cadastro interno da prefeitura"


class SenhaCriacaoMixin:
    def clean_cpf(self):
        cpf = normalizar_cpf(self.cleaned_data.get("cpf", ""))
        if len(cpf) != 11:
            raise ValidationError("Informe um CPF com 11 dígitos.")
        if UsuarioBase.objects.filter(cpf=cpf).exists():
            raise ValidationError("Já existe um usuário com este CPF.")
        return cpf

    def clean_password2(self):
        senha = self.cleaned_data.get("password1")
        confirmacao = self.cleaned_data.get("password2")
        if senha and confirmacao and senha != confirmacao:
            raise ValidationError("As senhas não coincidem.")
        if confirmacao:
            validate_password(confirmacao)
        return confirmacao

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        usuario.is_staff = True
        if commit:
            usuario.save()
        return usuario


class SenhaAlteracaoMixin:
    def save(self, commit=True):
        usuario = super().save(commit=False)
        nova_senha = self.cleaned_data.get("nova_senha")
        if nova_senha:
            validate_password(nova_senha, usuario)
            usuario.set_password(nova_senha)
        if commit:
            usuario.save()
        return usuario


class FiscalCreationForm(SenhaCriacaoMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        help_text="A senha será armazenada como hash. Não é possível vê-la depois.",
    )
    password2 = forms.CharField(
        label="Confirmação da senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Fiscal
        fields = (
            "cpf",
            "nome",
            "sobrenome",
            "email",
            "telefone_whatsapp",
            "matricula_funcional",
            "zona_atuacao_primaria",
            "ativo",
        )


class FiscalChangeForm(SenhaAlteracaoMixin, forms.ModelForm):
    nova_senha = forms.CharField(
        label="Nova senha",
        required=False,
        widget=forms.PasswordInput,
        help_text="Preencha somente para trocar a senha. O valor será gravado como hash.",
    )

    class Meta:
        model = Fiscal
        fields = (
            "cpf",
            "nome",
            "sobrenome",
            "email",
            "telefone_whatsapp",
            "matricula_funcional",
            "zona_atuacao_primaria",
            "is_active",
            "ativo",
        )


class GestorCreationForm(SenhaCriacaoMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        help_text="A senha será armazenada como hash. Não é possível vê-la depois.",
    )
    password2 = forms.CharField(
        label="Confirmação da senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Gestor
        fields = (
            "cpf",
            "nome",
            "sobrenome",
            "email",
            "telefone_whatsapp",
            "matricula_funcional",
            "departamento",
            "cargo",
            "ativo",
        )


class GestorChangeForm(SenhaAlteracaoMixin, forms.ModelForm):
    nova_senha = forms.CharField(
        label="Nova senha",
        required=False,
        widget=forms.PasswordInput,
        help_text="Preencha somente para trocar a senha. O valor será gravado como hash.",
    )

    class Meta:
        model = Gestor
        fields = (
            "cpf",
            "nome",
            "sobrenome",
            "email",
            "telefone_whatsapp",
            "matricula_funcional",
            "departamento",
            "cargo",
            "is_active",
            "ativo",
        )


class ServidorAdmin(admin.ModelAdmin):
    add_form = None
    change_form = None
    add_fieldsets = ()

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = self.add_form if obj is None else self.change_form
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)


@admin.register(UsuarioBase)
class UsuarioBaseAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "sobrenome", "email", "is_active")
    search_fields = ("cpf", "nome", "email")
    list_filter = ("is_active", "is_staff")
    readonly_fields = ("password", "last_login", "criado_em", "atualizado_em")

    def has_add_permission(self, request):
        return False


@admin.register(Ambulante)
class AmbulanteAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "tipo_atuacao", "pontuacao", "ativo")
    search_fields = ("cpf", "nome", "cnpj", "apelido_nome_fantasia")
    list_filter = ("ativo",)


@admin.register(Fiscal)
class FiscalAdmin(ServidorAdmin):
    add_form = FiscalCreationForm
    change_form = FiscalChangeForm
    list_display = (
        "cpf",
        "nome",
        "matricula_funcional",
        "zona_atuacao_primaria",
        "ativo",
    )
    search_fields = ("matricula_funcional", "nome", "cpf")
    list_filter = ("ativo", "zona_atuacao_primaria")
    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "cpf",
                    "nome",
                    "sobrenome",
                    "email",
                    "telefone_whatsapp",
                )
            },
        ),
        ("Lotação", {"fields": ("matricula_funcional", "zona_atuacao_primaria")}),
        ("Acesso", {"fields": ("is_active", "ativo", "nova_senha")}),
    )
    add_fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "cpf",
                    "nome",
                    "sobrenome",
                    "email",
                    "telefone_whatsapp",
                )
            },
        ),
        ("Lotação", {"fields": ("matricula_funcional", "zona_atuacao_primaria")}),
        ("Acesso", {"fields": ("password1", "password2", "ativo")}),
    )


@admin.register(Gestor)
class GestorAdmin(ServidorAdmin):
    add_form = GestorCreationForm
    change_form = GestorChangeForm
    list_display = (
        "cpf",
        "nome",
        "matricula_funcional",
        "cargo",
        "departamento",
        "ativo",
    )
    search_fields = ("matricula_funcional", "nome", "cpf")
    list_filter = ("departamento", "ativo")
    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "cpf",
                    "nome",
                    "sobrenome",
                    "email",
                    "telefone_whatsapp",
                )
            },
        ),
        (
            "Lotação",
            {"fields": ("matricula_funcional", "departamento", "cargo")},
        ),
        ("Acesso", {"fields": ("is_active", "ativo", "nova_senha")}),
    )
    add_fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "cpf",
                    "nome",
                    "sobrenome",
                    "email",
                    "telefone_whatsapp",
                )
            },
        ),
        (
            "Lotação",
            {"fields": ("matricula_funcional", "departamento", "cargo")},
        ),
        ("Acesso", {"fields": ("password1", "password2", "ativo")}),
    )


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "acesso_master", "acesso_painel_tecnico", "ativo")
    list_filter = ("acesso_master", "acesso_painel_tecnico")
    readonly_fields = ("password",)
