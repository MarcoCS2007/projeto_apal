from django.urls import path

from apps.fiscalizacao.views import FiscalizacaoView, RegistrarOcorrenciaView

from .views import (
    BackofficeInicioView,
    CadastroCompletoAmbulanteView,
    LoginAmbulanteView,
    LoginBackofficeView,
    LoginFiscalView,
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
from .views_gestor import (
    GestorAmbulanteAcaoView,
    GestorAmbulanteEditarView,
    GestorAmbulantesView,
    GestorAnalisarLicencaView,
    GestorDashboardView,
    GestorDossieView,
    GestorEmitirAlvaraView,
    GestorFilaView,
    GestorLicencasAtivasView,
    GestorOcorrenciaDetalheView,
    GestorOcorrenciasView,
)

urlpatterns = [
    path("login/", LoginBackofficeView.as_view(), name="login"),
    path("logout/", LogoutBackofficeView.as_view(), name="logout"),
    path("entrar/", LoginAmbulanteView.as_view(), name="entrar"),
    path("fiscal/entrar/", LoginFiscalView.as_view(), name="fiscal_entrar"),
    path("fiscal/", FiscalizacaoView.as_view(), name="fiscal_painel"),
    path(
        "fiscal/ocorrencia/",
        RegistrarOcorrenciaView.as_view(),
        name="fiscal_ocorrencia",
    ),
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
    path("gestor/fila/", GestorFilaView.as_view(), name="gestor_fila"),
    path(
        "gestor/ambulantes/",
        GestorAmbulantesView.as_view(),
        name="gestor_ambulantes",
    ),
    path(
        "gestor/ambulantes/<int:pk>/dossie/",
        GestorDossieView.as_view(),
        name="gestor_dossie",
    ),
    path(
        "gestor/ambulantes/<int:pk>/editar/",
        GestorAmbulanteEditarView.as_view(),
        name="gestor_ambulante_editar",
    ),
    path(
        "gestor/ambulantes/<int:pk>/acao/",
        GestorAmbulanteAcaoView.as_view(),
        name="gestor_ambulante_acao",
    ),
    path(
        "gestor/analisar/<int:pk>/",
        GestorAnalisarLicencaView.as_view(),
        name="gestor_analisar",
    ),
    path(
        "gestor/emitir/<int:pk>/",
        GestorEmitirAlvaraView.as_view(),
        name="gestor_emitir",
    ),
    path(
        "gestor/licencas/",
        GestorLicencasAtivasView.as_view(),
        name="gestor_licencas",
    ),
    path(
        "gestor/ocorrencias/",
        GestorOcorrenciasView.as_view(),
        name="gestor_ocorrencias",
    ),
    path(
        "gestor/ocorrencias/<int:pk>/",
        GestorOcorrenciaDetalheView.as_view(),
        name="gestor_ocorrencia_detalhe",
    ),
    path("gestor/dashboard/", GestorDashboardView.as_view(), name="gestor_dashboard"),
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
