from django.contrib import admin

from .models import (
    CatalogoInfracao,
    OcorrenciaInspecao,
    ParadaRota,
    RegistroVisita,
    RotaFiscal,
)


@admin.register(CatalogoInfracao)
class CatalogoInfracaoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "gravidade", "pontos_desconto")
    search_fields = ("descricao",)
    list_filter = ("gravidade",)


@admin.register(OcorrenciaInspecao)
class OcorrenciaInspecaoAdmin(admin.ModelAdmin):
    list_display = (
        "fiscal",
        "ambulante",
        "tipo_ocorrencia",
        "status_ocorrencia",
        "criado_em",
    )
    search_fields = ("fiscal__nome", "ambulante__nome", "tipo_ocorrencia")
    list_filter = ("status_ocorrencia",)


class ParadaRotaInline(admin.TabularInline):
    model = ParadaRota
    extra = 0
    fields = ("ordem", "ambulante", "ponto", "status")


@admin.register(RotaFiscal)
class RotaFiscalAdmin(admin.ModelAdmin):
    list_display = ("titulo", "fiscal", "status", "data_prevista", "criado_em")
    list_filter = ("status",)
    search_fields = ("titulo", "fiscal__nome")
    inlines = (ParadaRotaInline,)


@admin.register(RegistroVisita)
class RegistroVisitaAdmin(admin.ModelAdmin):
    list_display = (
        "parada",
        "encontrou_ambulante",
        "foi_recebido",
        "ocorrencia",
        "registrado_em",
    )
    list_filter = ("encontrou_ambulante", "foi_recebido")
