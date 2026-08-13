from django.urls import path

from .api import (
    CredencialAmbulanteAPIView,
    CredencialQrPngAPIView,
    DocumentosAmbulanteAPIView,
    SolicitacaoAmbulanteAPIView,
)

urlpatterns = [
    path(
        "ambulante/documentos/",
        DocumentosAmbulanteAPIView.as_view(),
        name="api_ambulante_documentos",
    ),
    path(
        "ambulante/solicitacao/",
        SolicitacaoAmbulanteAPIView.as_view(),
        name="api_ambulante_solicitacao",
    ),
    path(
        "ambulante/credencial/",
        CredencialAmbulanteAPIView.as_view(),
        name="api_ambulante_credencial",
    ),
    path(
        "ambulante/credencial/qr.png",
        CredencialQrPngAPIView.as_view(),
        name="api_ambulante_credencial_qr",
    ),
]
