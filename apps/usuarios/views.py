from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
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
    ConfiguracaoSegurancaForm,
    LoginAmbulanteForm,
    LoginBackofficeForm,
    NovaSenhaForm,
    RecuperarSenhaForm,
)
from .forms_cadastro import (
    AnexosCadastroForm,
    DadosPessoaisCadastroForm,
    EmpresaCadastroForm,
    EnderecoCadastroForm,
    EstruturaCadastroForm,
    PontoCadastroForm,
)
from .models import (
    Ambulante,
    ConfiguracaoSeguranca,
    Fiscal,
    Gestor,
    Perfil,
    UsuarioBase,
)
from .serializers import LoginSerializer, UsuarioMeSerializer


def destino_pos_login(user):
    if user.role == Perfil.AMBULANTE:
        return reverse("ambulante_painel")
    if user.role == Perfil.ADMINISTRADOR:
        return reverse("master_admin")
    if user.role == Perfil.GESTOR:
        return reverse("backoffice_inicio")
    return reverse("index")


def aplicar_tempo_sessao(request):
    minutos = ConfiguracaoSeguranca.carregar().tempo_sessao_minutos
    request.session.set_expiry(minutos * 60)


def apagar_cookie_sessao(response):
    kwargs = {
        "path": settings.SESSION_COOKIE_PATH,
        "samesite": settings.SESSION_COOKIE_SAMESITE,
    }
    if settings.SESSION_COOKIE_DOMAIN:
        kwargs["domain"] = settings.SESSION_COOKIE_DOMAIN
    response.delete_cookie(settings.SESSION_COOKIE_NAME, **kwargs)
    return response


def destino_pos_logout(role):
    if role == Perfil.AMBULANTE:
        return reverse("entrar")
    return f"{reverse('login')}?encerrado=1"


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

    def form_valid(self, form):
        response = super().form_valid(form)
        aplicar_tempo_sessao(self.request)
        return response

    def get_success_url(self):
        if self.request.user.role == Perfil.ADMINISTRADOR:
            return reverse("master_admin")
        return reverse("backoffice_inicio")


class LogoutBackofficeView(View):
    """Encerra o expediente web: invalida a sessão e apaga o cookie."""

    http_method_names = ("post", "options")

    def post(self, request, *args, **kwargs):
        role = None
        if request.user.is_authenticated:
            role = getattr(request.user, "role", None)
        logout(request)
        return apagar_cookie_sessao(redirect(destino_pos_logout(role)))


class LoginAmbulanteView(LoginView):
    """Login por sessão para o trabalhador ambulante."""

    template_name = "entrar.html"
    authentication_form = LoginAmbulanteForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        aplicar_tempo_sessao(self.request)
        return response

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


ETAPAS_CADASTRO = {
    1: DadosPessoaisCadastroForm,
    2: EnderecoCadastroForm,
    3: EmpresaCadastroForm,
    4: EstruturaCadastroForm,
    5: PontoCadastroForm,
    6: AnexosCadastroForm,
}


class CadastroCompletoAmbulanteView(
    LoginRequiredMixin, AcessoAmbulanteMixin, View
):
    login_url = reverse_lazy("entrar")
    template_name = "ambulante/cadastro.html"

    def _ambulante(self):
        return Ambulante.objects.get(pk=self.request.user.pk)

    def _etapa(self, origem):
        try:
            etapa = int(origem.get("etapa", 1))
        except (TypeError, ValueError):
            etapa = 1
        if etapa not in ETAPAS_CADASTRO:
            return 1
        return etapa

    def _contexto(self, ambulante, etapa, form, concluido=False):
        return {
            "ambulante": ambulante,
            "etapa": etapa,
            "form": form,
            "cadastro_completo": ambulante.cadastro_completo,
            "concluido": concluido,
            "stepper_percent": int(((etapa - 1) / 5) * 100),
            "pontos_catalogo": form.fields["ponto_pretendido"].queryset
            if etapa == 5
            else None,
        }

    def get(self, request):
        ambulante = self._ambulante()
        concluido = request.GET.get("concluido") == "1"
        etapa = 6 if concluido else self._etapa(request.GET)
        form = ETAPAS_CADASTRO[etapa](ambulante=ambulante)
        return render(
            request,
            self.template_name,
            self._contexto(ambulante, etapa, form, concluido=concluido),
        )

    def post(self, request):
        ambulante = self._ambulante()
        etapa = self._etapa(request.POST)
        form_class = ETAPAS_CADASTRO[etapa]
        form = form_class(request.POST, request.FILES, ambulante=ambulante)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._contexto(ambulante, etapa, form),
            )

        form.save()
        ambulante.refresh_from_db()
        acao = request.POST.get("acao", "proxima")
        if acao == "enviar":
            if ambulante.cadastro_completo:
                messages.success(
                    request,
                    "Cadastro concluído. Você ainda não possui licença; "
                    "o gestor já consegue ver o seu registro.",
                )
                return redirect(f"{reverse('ambulante_cadastro')}?concluido=1")
            messages.error(
                request,
                "Ainda faltam dados obrigatórios (pessoais, endereço, "
                "empresa/atuação e estrutura) para concluir o cadastro.",
            )
            return redirect(f"{reverse('ambulante_cadastro')}?etapa={etapa}")

        proxima = min(etapa + 1, 6)
        messages.success(request, "Etapa salva. Você pode continuar sem perder os dados.")
        return redirect(f"{reverse('ambulante_cadastro')}?etapa={proxima}")


class GestorAmbulantesView(
    LoginRequiredMixin, AcessoBackofficeMixin, TemplateView
):
    template_name = "gestor/ambulantes-cadastrados.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busca = self.request.GET.get("q", "").strip()
        ambulantes = Ambulante.objects.prefetch_related(
            "enderecos", "estruturas"
        ).order_by("-criado_em", "nome")
        if busca:
            ambulantes = ambulantes.filter(
                Q(nome__icontains=busca)
                | Q(sobrenome__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(email__icontains=busca)
                | Q(apelido_nome_fantasia__icontains=busca)
            )
        context["busca"] = busca
        context["ambulantes"] = ambulantes
        context["total_ambulantes"] = ambulantes.count()
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


class MasterPermissoesView(LoginRequiredMixin, AcessoMasterMixin, FormView):
    template_name = "master/gerenciar-permissoes.html"
    form_class = ConfiguracaoSegurancaForm
    success_url = reverse_lazy("master_permissoes")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = ConfiguracaoSeguranca.carregar()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Permissões e políticas globais de segurança atualizadas com sucesso.",
        )
        return super().form_valid(form)


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
