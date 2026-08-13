from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
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

from .forms import CadastroFiscalForm, CadastroGestorForm, LoginBackofficeForm
from .models import Ambulante, Fiscal, Gestor, Perfil, UsuarioBase
from .serializers import LoginSerializer, UsuarioMeSerializer


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
        if self.request.user.is_authenticated:
            logout(self.request)
        return redirect("login")


class AcessoMasterMixin(UserPassesTestMixin):
    """Restringe views web a Administradores (Master)."""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role == Perfil.ADMINISTRADOR)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect("backoffice_inicio")
        return redirect("login")


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
