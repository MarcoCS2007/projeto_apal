from django.urls import path

from .views import (
    BackofficeInicioView,
    LoginBackofficeView,
    LogoutBackofficeView,
    MasterAdminView,
    MasterCadastrarFiscalView,
    MasterCadastrarGestorView,
    MasterFiscaisView,
    MasterGestoresView,
    MasterLogsIAView,
    MasterTemplateView,
)

urlpatterns = [
    path("login/", LoginBackofficeView.as_view(), name="login"),
    path("logout/", LogoutBackofficeView.as_view(), name="logout"),
    path("backoffice/", BackofficeInicioView.as_view(), name="backoffice_inicio"),
    path("master/", MasterAdminView.as_view(), name="master_admin"),
    path("master/gestores/", MasterGestoresView.as_view(), name="master_gestores"),
    path(
        "master/gestores/cadastrar/",
        MasterCadastrarGestorView.as_view(),
        name="master_cadastrar_gestor",
    ),
    path("master/fiscais/", MasterFiscaisView.as_view(), name="master_fiscais"),
    path(
        "master/fiscais/cadastrar/",
        MasterCadastrarFiscalView.as_view(),
        name="master_cadastrar_fiscal",
    ),
    path(
        "master/permissoes/",
        MasterTemplateView.as_view(template_name="master/gerenciar-permissoes.html"),
        name="master_permissoes",
    ),
    path("master/logs-ia/", MasterLogsIAView.as_view(), name="master_logs_ia"),
]
