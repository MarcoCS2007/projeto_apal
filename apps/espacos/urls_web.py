from django.urls import path

from .views import (
    GestorMapaCidadeJsonView,
    GestorMapaCidadeView,
    GestorPontoExcluirView,
    GestorPontosView,
)

urlpatterns = [
    path("gestor/pontos/", GestorPontosView.as_view(), name="gestor_pontos"),
    path(
        "gestor/pontos/<int:pk>/",
        GestorPontosView.as_view(),
        name="gestor_pontos_editar",
    ),
    path(
        "gestor/pontos/<int:pk>/excluir/",
        GestorPontoExcluirView.as_view(),
        name="gestor_pontos_excluir",
    ),
    path("gestor/mapa/", GestorMapaCidadeView.as_view(), name="gestor_mapa_cidade"),
    path(
        "gestor/mapa/dados.json",
        GestorMapaCidadeJsonView.as_view(),
        name="gestor_mapa_cidade_json",
    ),
]
