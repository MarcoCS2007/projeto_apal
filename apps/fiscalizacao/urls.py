from django.urls import path

from .api import BuscaFiscalAPIView, OcorrenciaFiscalAPIView, QrFiscalAPIView

urlpatterns = [
    path("fiscal/busca/", BuscaFiscalAPIView.as_view(), name="api_fiscal_busca"),
    path("fiscal/qr/", QrFiscalAPIView.as_view(), name="api_fiscal_qr"),
    path(
        "fiscal/ocorrencias/",
        OcorrenciaFiscalAPIView.as_view(),
        name="api_fiscal_ocorrencias",
    ),
]
