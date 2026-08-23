from django.contrib import admin

from .models import LogAssistente


@admin.register(LogAssistente)
class LogAssistenteAdmin(admin.ModelAdmin):
    list_display = ("ambulante", "fonte", "criado_em")
    search_fields = ("ambulante__nome", "ambulante__cpf", "pergunta", "resposta")
