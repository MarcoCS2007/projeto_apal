from django.contrib import admin

from .models import Endereco, EstruturaTrabalho, PontoOcupacao


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = (
        "ambulante",
        "logradouro",
        "numero",
        "bairro",
        "cidade",
        "estado_uf",
    )
    search_fields = ("logradouro", "cep", "ambulante__nome", "ambulante__cpf")
    list_filter = ("estado_uf", "cidade")


@admin.register(EstruturaTrabalho)
class EstruturaTrabalhoAdmin(admin.ModelAdmin):
    list_display = ("ambulante", "tipo_estrutura", "dimensoes_metragem", "ativo")
    search_fields = ("ambulante__nome", "ambulante__cpf", "tipo_estrutura")


@admin.register(PontoOcupacao)
class PontoOcupacaoAdmin(admin.ModelAdmin):
    list_display = (
        "nome_identificacao",
        "bairro",
        "status_ocupacao",
        "metragem_maxima",
        "ativo",
    )
    search_fields = ("nome_identificacao", "logradouro", "bairro")
    list_filter = ("status_ocupacao",)
