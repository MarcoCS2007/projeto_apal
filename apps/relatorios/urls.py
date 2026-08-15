from django.urls import path

from .views import DashboardInteligenciaView, ExportacaoRelatorioView

app_name = "relatorios"

urlpatterns = [
    path("inteligencia/", DashboardInteligenciaView.as_view(), name="dashboard"),
    path("exportar/", ExportacaoRelatorioView.as_view(), name="exportacao"),
]
