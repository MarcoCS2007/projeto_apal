from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.assistente.models import LogAssistente

from .forms import (
    CadastroAmbulanteForm,
    CadastroFiscalForm,
    CadastroGestorForm,
    LoginAmbulanteForm,
    LoginBackofficeForm,
    NovaSenhaForm,
    RecuperarSenhaForm,
)
from .models import Ambulante, Fiscal, Gestor, Perfil, UsuarioBase
from .serializers import LoginSerializer, UsuarioMeSerializer


def destino_pos_login(user):
    if user.role == Perfil.AMBULANTE:
        return reverse("ambulante_painel")
    if user.role == Perfil.ADMINISTRADOR:
        return reverse("master_admin")
    if user.role == Perfil.GESTOR:
        return reverse("backoffice_inicio")
    return reverse("index")


class LoginAPIView(TokenObtainPairView):
    """Login stateless para o aplicativo móvel. Não cria sessão Django."""

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()


class TokenRefreshAPIView(TokenRefreshView):
    permission_classes = (AllowAny,)
    authentication_classes = ()


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UsuarioMeSerializer(request.user)
        return Response(serializer.data)


class AcessoBackofficeMixin(UserPassesTestMixin):
    """Restringe views web a Gestores e Administradores."""

    def test_func(self):
        user = self.request.user
        return bool(
            user.is_authenticated and user.role in (Perfil.GESTOR, Perfil.ADMINISTRADOR)
        )

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.role == Perfil.AMBULANTE:
            return redirect("ambulante_painel")
        if user.is_authenticated:
            logout(self.request)
        return redirect("login")


class AcessoMasterMixin(UserPassesTestMixin):
    """Restringe views web a Administradores (Master)."""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role == Perfil.ADMINISTRADOR)

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.role == Perfil.GESTOR:
            return redirect("backoffice_inicio")
        if user.is_authenticated and user.role == Perfil.AMBULANTE:
            return redirect("ambulante_painel")
        if user.is_authenticated:
            logout(self.request)
        return redirect("login")


class AcessoAmbulanteMixin(UserPassesTestMixin):
    """Restringe views web a comerciantes ambulantes."""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role == Perfil.AMBULANTE)

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.role == Perfil.ADMINISTRADOR:
            return redirect("master_admin")
        if user.is_authenticated and user.role == Perfil.GESTOR:
            return redirect("backoffice_inicio")
        if user.is_authenticated:
            logout(self.request)
        return redirect("entrar")


class LoginBackofficeView(LoginView):
    """Login por sessão/cookie exclusivo do backoffice."""

    template_name = "login.html"
    authentication_form = LoginBackofficeForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.role == Perfil.ADMINISTRADOR:
            return reverse("master_admin")
        return reverse("backoffice_inicio")


class LogoutBackofficeView(LogoutView):
    next_page = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        role = None
        if request.user.is_authenticated:
            role = getattr(request.user, "role", None)
        self.next_page = (
            reverse("entrar") if role == Perfil.AMBULANTE else reverse("login")
        )
        return super().dispatch(request, *args, **kwargs)


class LoginAmbulanteView(LoginView):
    """Login por sessão para o trabalhador ambulante."""

    template_name = "entrar.html"
    authentication_form = LoginAmbulanteForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("ambulante_painel")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(destino_pos_login(request.user))
        return super().dispatch(request, *args, **kwargs)


class RegistroAmbulanteView(FormView):
    template_name = "registro.html"
    form_class = CadastroAmbulanteForm
    success_url = reverse_lazy("ambulante_painel")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(destino_pos_login(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        usuario = form.save()
        login(
            self.request,
            usuario,
            backend="apps.usuarios.backends.CPFOuEmailBackend",
        )
        messages.success(
            self.request,
            "Conta criada com sucesso. Complete seu cadastro para solicitar a licença.",
        )
        return super().form_valid(form)


class PainelAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, TemplateView):
    template_name = "ambulante/painel.html"
    login_url = reverse_lazy("entrar")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ambulante = Ambulante.objects.filter(pk=self.request.user.pk).first()
        context["ambulante"] = ambulante
        context["cadastro_completo"] = bool(
            ambulante and ambulante.cadastro_completo
        )
        context["tem_licenca"] = bool(ambulante and ambulante.licencas.exists())
        return context


class RecuperarSenhaView(PasswordResetView):
    template_name = "redefinir_senha.html"
    form_class = RecuperarSenhaForm
    email_template_name = "emails/redefinir_senha.txt"
    subject_template_name = "emails/redefinir_senha_assunto.txt"
    success_url = reverse_lazy("redefinir_senha")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Se o e-mail ou CPF estiver cadastrado, enviaremos as instruções "
            "para redefinir a senha.",
        )
        return super().form_valid(form)


class RedefinirSenhaConfirmView(PasswordResetConfirmView):
    template_name = "redefinir_senha_nova.html"
    form_class = NovaSenhaForm
    success_url = reverse_lazy("entrar")

    def form_valid(self, form):
        messages.success(
            self.request, "Senha redefinida com sucesso. Faça login para continuar."
        )
        return super().form_valid(form)


class BackofficeInicioView(LoginRequiredMixin, AcessoBackofficeMixin, TemplateView):
    template_name = "backoffice_inicio.html"


class MasterTemplateView(LoginRequiredMixin, AcessoMasterMixin, TemplateView):
    """Base das telas do painel Master."""


class MasterAdminView(MasterTemplateView):
    template_name = "master/admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_gestores_ativos"] = Gestor.objects.filter(ativo=True).count()
        context["total_fiscais"] = Fiscal.objects.count()
        context["total_ambulantes"] = Ambulante.objects.count()
        context["atividade_recente"] = UsuarioBase.objects.filter(
            last_login__isnull=False
        ).order_by("-last_login")[:8]
        return context


class MasterGestoresView(MasterTemplateView):
    template_name = "master/controlar-gestores.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busca = self.request.GET.get("q", "").strip()
        gestores = Gestor.objects.order_by("nome", "sobrenome")
        if busca:
            gestores = gestores.filter(
                Q(nome__icontains=busca)
                | Q(sobrenome__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(email__icontains=busca)
                | Q(departamento__icontains=busca)
                | Q(cargo__icontains=busca)
            )
        context["busca"] = busca
        context["gestores"] = gestores
        context["total_gestores"] = gestores.count()
        return context


class MasterFiscaisView(MasterTemplateView):
    template_name = "master/gerenciar-fiscais.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busca = self.request.GET.get("q", "").strip()
        fiscais = Fiscal.objects.order_by("nome", "sobrenome")
        if busca:
            fiscais = fiscais.filter(
                Q(nome__icontains=busca)
                | Q(sobrenome__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(email__icontains=busca)
                | Q(matricula_funcional__icontains=busca)
                | Q(zona_atuacao_primaria__icontains=busca)
            )
        context["busca"] = busca
        context["fiscais"] = fiscais
        context["total_fiscais"] = fiscais.count()
        return context


class MasterLogsIAView(MasterTemplateView):
    template_name = "master/logs-ia.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = LogAssistente.objects.select_related("ambulante").order_by("-criado_em")
        hoje = timezone.localdate()
        context["logs"] = logs[:50]
        context["consultas_hoje"] = logs.filter(criado_em__date=hoje).count()
        context["total_logs"] = logs.count()
        context["ambulantes_com_consulta"] = (
            logs.values("ambulante_id").distinct().count()
        )
        return context


class MasterCadastrarGestorView(LoginRequiredMixin, AcessoMasterMixin, FormView):
    template_name = "master/cadastrar-gestor.html"
    form_class = CadastroGestorForm
    success_url = reverse_lazy("master_gestores")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Gestor cadastrado com sucesso.")
        return super().form_valid(form)


class MasterCadastrarFiscalView(LoginRequiredMixin, AcessoMasterMixin, FormView):
    template_name = "master/cadastrar-fiscal.html"
    form_class = CadastroFiscalForm
    success_url = reverse_lazy("master_fiscais")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Fiscal cadastrado com sucesso.")
        return super().form_valid(form)
