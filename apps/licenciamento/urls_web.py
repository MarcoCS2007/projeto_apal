from django.urls import path

from .views import (
    AprovarDocumentoView,
    GestorCategoriaExcluirView,
    GestorCategoriasView,
    GestorTriagemView,
    RejeitarDocumentoView,
)

urlpatterns = [
    path(
        "gestor/categorias/",
        GestorCategoriasView.as_view(),
        name="gestor_categorias",
    ),
    path(
        "gestor/categorias/<int:pk>/",
        GestorCategoriasView.as_view(),
        name="gestor_categorias_editar",
    ),
    path(
        "gestor/categorias/<int:pk>/excluir/",
        GestorCategoriaExcluirView.as_view(),
        name="gestor_categorias_excluir",
    ),
    path("gestor/triagem/", GestorTriagemView.as_view(), name="gestor_triagem"),
    path(
        "api/documentos/<int:pk>/aprovar/",
        AprovarDocumentoView.as_view(),
        name="documento_aprovar",
    ),
    path(
        "api/documentos/<int:pk>/rejeitar/",
        RejeitarDocumentoView.as_view(),
        name="documento_rejeitar",
    ),
]
