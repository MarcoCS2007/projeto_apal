from django.contrib import admin

from .models import OcorrenciaInspecao


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
