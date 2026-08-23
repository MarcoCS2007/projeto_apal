from django.contrib import admin

from .models import CategoriaProduto, DocumentoAnexo, LicencaAlvara


@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "nome_categoria",
        "exige_laudo_sanitario",
        "exige_laudo_bombeiros",
        "ativo",
    )
    list_filter = ("exige_laudo_sanitario", "exige_laudo_bombeiros", "ativo")
    search_fields = ("nome_categoria", "descricao")


@admin.register(DocumentoAnexo)
class DocumentoAnexoAdmin(admin.ModelAdmin):
    list_display = (
        "ambulante",
        "tipo_documento",
        "status_aprovacao",
        "data_upload",
    )
    list_filter = ("status_aprovacao",)
    search_fields = ("ambulante__nome", "ambulante__cpf", "tipo_documento")


@admin.register(LicencaAlvara)
class LicencaAlvaraAdmin(admin.ModelAdmin):
    list_display = (
        "protocolo",
        "numero_licenca",
        "ambulante",
        "ponto_ocupacao",
        "categoria_produto",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "protocolo",
        "numero_licenca",
        "ambulante__nome",
        "ambulante__cpf",
    )
