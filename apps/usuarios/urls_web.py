from django.urls import path

from .views import (
    BackofficeInicioView,
    CadastroCompletoAmbulanteView,
    GestorAmbulantesView,
    LoginAmbulanteView,
    LoginBackofficeView,
    LogoutBackofficeView,
    MasterAdminView,
    MasterCadastrarFiscalView,
    MasterCadastrarGestorView,
    MasterFiscaisView,
    MasterGestoresView,
    MasterLogsIAView,
    MasterPermissoesView,
    PainelAmbulanteView,
    RecuperarSenhaView,
    RedefinirSenhaConfirmView,
    RegistroAmbulanteView,
)

urlpatterns = [
    path("login/", LoginBackofficeView.as_view(), name="login"),
    path("logout/", LogoutBackofficeView.as_view(), name="logout"),
    path("entrar/", LoginAmbulanteView.as_view(), name="entrar"),
    path("registro/", RegistroAmbulanteView.as_view(), name="registro"),
    path("redefinir-senha/", RecuperarSenhaView.as_view(), name="redefinir_senha"),
    path(
        "redefinir-senha/<uidb64>/<token>/",
        RedefinirSenhaConfirmView.as_view(),
        name="redefinir_senha_confirmar",
    ),
    path("ambulante/", PainelAmbulanteView.as_view(), name="ambulante_painel"),
    path(
        "ambulante/cadastro/",
        CadastroCompletoAmbulanteView.as_view(),
        name="ambulante_cadastro",
    ),
    path("backoffice/", BackofficeInicioView.as_view(), name="backoffice_inicio"),
    path(
        "gestor/ambulantes/",
        GestorAmbulantesView.as_view(),
        name="gestor_ambulantes",
    ),
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
        MasterPermissoesView.as_view(),
        name="master_permissoes",
    ),
    path("master/logs-ia/", MasterLogsIAView.as_view(), name="master_logs_ia"),
]
