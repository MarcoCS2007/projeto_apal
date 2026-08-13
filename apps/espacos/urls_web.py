from django.urls import path

from .views import GestorPontoExcluirView, GestorPontosView

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
]
