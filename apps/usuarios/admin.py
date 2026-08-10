from django.contrib import admin

from .models import Administrador, Ambulante, Fiscal, Gestor, UsuarioBase


@admin.register(UsuarioBase)
class UsuarioBaseAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "sobrenome", "email", "is_active")
    search_fields = ("cpf", "nome", "email")
    list_filter = ("is_active", "is_staff")


@admin.register(Ambulante)
class AmbulanteAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "tipo_atuacao", "pontuacao", "ativo")
    search_fields = ("cpf", "nome", "cnpj", "apelido_nome_fantasia")
    list_filter = ("ativo",)


@admin.register(Fiscal)
class FiscalAdmin(admin.ModelAdmin):
    list_display = (
        "cpf",
        "nome",
        "matricula_funcional",
        "zona_atuacao_primaria",
        "ativo",
    )
    search_fields = ("matricula_funcional", "nome", "cpf")


@admin.register(Gestor)
class GestorAdmin(admin.ModelAdmin):
    list_display = (
        "cpf",
        "nome",
        "matricula_funcional",
        "cargo",
        "departamento",
        "ativo",
    )
    search_fields = ("matricula_funcional", "nome", "cpf")
    list_filter = ("departamento",)


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ("cpf", "nome", "acesso_master", "acesso_painel_tecnico", "ativo")
    list_filter = ("acesso_master", "acesso_painel_tecnico")
