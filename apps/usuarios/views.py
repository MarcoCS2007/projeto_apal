from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied
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
from apps.core.qrcode import validar_codigo_qr
from apps.licenciamento.models import StatusLicenca
from apps.licenciamento.services import (
    categoria_do_ambulante,
    licenca_ativa,
    licenca_atual,
    pode_avancar_solicitacao,
    tipos_faltando_aprovacao,
    tipos_faltando_envio,
    tipos_obrigatorios,
)

from .forms import (
    CadastroAmbulanteForm,
    CadastroFiscalForm,
    CadastroGestorForm,
    ConfiguracaoSegurancaForm,
    LoginAmbulanteForm,
    LoginBackofficeForm,
    LoginFiscalForm,
    NovaSenhaForm,
    RecuperarSenhaForm,
)
from .forms_cadastro import (
    ESCOLARIDADE_CHOICES,
    TIPO_COMERCIO_CHOICES,
    TIPO_ESTRUTURA_CHOICES,
    AnexosCadastroForm,
    DadosPessoaisCadastroForm,
    EmpresaCadastroForm,
    EnderecoCadastroForm,
    EstruturaCadastroForm,
    PerfilAmbulanteForm,
    PontoCadastroForm,
    rotulo_escolha,
)
from .models import (
    Administrador,
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
    if user.role == Perfil.FISCAL:
        return reverse("fiscal_painel")
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
    if role == Perfil.FISCAL:
        return reverse("fiscal_entrar")
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
        if user.is_authenticated and user.role == Perfil.FISCAL:
            return redirect("fiscal_painel")
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
        if user.is_authenticated and user.role == Perfil.FISCAL:
            return redirect("fiscal_painel")
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
        if user.is_authenticated and user.role == Perfil.FISCAL:
            return redirect("fiscal_painel")
        if user.is_authenticated:
            logout(self.request)
        return redirect("entrar")


class AcessoFiscalMixin(UserPassesTestMixin):
    """Restringe views web a fiscais de campo."""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role == Perfil.FISCAL)

    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.role == Perfil.ADMINISTRADOR:
            return redirect("master_admin")
        if user.is_authenticated and user.role == Perfil.GESTOR:
            return redirect("backoffice_inicio")
        if user.is_authenticated and user.role == Perfil.AMBULANTE:
            return redirect("ambulante_painel")
        if user.is_authenticated:
            logout(self.request)
        return redirect("fiscal_entrar")


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


class LoginFiscalView(LoginView):
    """Login por sessão para o fiscal de campo."""

    template_name = "fiscal/entrar.html"
    authentication_form = LoginFiscalForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        aplicar_tempo_sessao(self.request)
        return response

    def get_success_url(self):
        return reverse("fiscal_painel")

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
        context["cadastro_completo"] = bool(ambulante and ambulante.cadastro_completo)
        context["tem_licenca"] = bool(ambulante and ambulante.licencas.exists())
        context["licenca"] = licenca_atual(ambulante) if ambulante else None
        documentos = ambulante.documentos.all() if ambulante else None
        context["documentos_rejeitados"] = (
            list(documentos.filter(status_aprovacao="Rejeitado"))
            if documentos is not None
            else []
        )
        context["documentos_pendentes"] = (
            list(documentos.filter(status_aprovacao="Pendente"))
            if documentos is not None
            else []
        )
        context.update(
            _resumo_status_painel(
                ambulante,
                context["licenca"],
                cadastro_completo=context["cadastro_completo"],
                documentos_rejeitados=context["documentos_rejeitados"],
            )
        )
        context.update(
            _stepper_painel(
                ambulante,
                context["licenca"],
                cadastro_completo=context["cadastro_completo"],
                documentos_rejeitados=context["documentos_rejeitados"],
            )
        )
        context.update(_card_protocolo_prazos(context["licenca"]))
        if ambulante:
            from .score import resumo_score

            context.update(resumo_score(ambulante))
            ativa = licenca_ativa(ambulante)
            licenca_suspensa = (
                ambulante.licencas.filter(status="Suspenso")
                .order_by("-data_emissao")
                .first()
            )
            licenca_cred = ativa or licenca_suspensa

            qr_liberado = bool(
                licenca_cred
                and licenca_cred.qr_valido
                and ambulante.codigo_qr_code
                and validar_codigo_qr(ambulante.codigo_qr_code) is not None
            )
            context["qr_liberado"] = qr_liberado
            context["licenca_ativa"] = ativa
            context["licenca_credencial"] = (
                licenca_cred if qr_liberado else context["licenca"]
            )
            context["historico_licencas"] = list(
                ambulante.licencas.order_by("-criado_em")
            )
            context["categoria"] = categoria_do_ambulante(ambulante)
        else:
            context["qr_liberado"] = False
            context["licenca_ativa"] = None
            context["licenca_credencial"] = None
            context["historico_licencas"] = []
            context["categoria"] = None
        return context


class PerfilAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, View):
    template_name = "ambulante/perfil.html"
    login_url = reverse_lazy("entrar")

    def _ambulante(self):
        return Ambulante.objects.get(pk=self.request.user.pk)

    def _contexto(self, ambulante, form, *, modo_edicao=False):
        extras = ambulante.dados_complementares or {}
        estrutura = ambulante.estruturas.order_by("id").first()
        situacao = ambulante.situacao_conta
        situacao_rotulos = {
            "cancelada": "Cancelada",
            "suspensa": "Suspensa",
            "completa": "Completa",
            "pendente": "Pendente",
        }
        return {
            "form": form,
            "ambulante": ambulante,
            "endereco": ambulante.enderecos.order_by("id").first(),
            "estrutura": estrutura,
            "extras": extras,
            "categoria": categoria_do_ambulante(ambulante),
            "licenca": licenca_atual(ambulante),
            "escolaridade_label": rotulo_escolha(
                ESCOLARIDADE_CHOICES, ambulante.escolaridade
            ),
            "tipo_atuacao_label": rotulo_escolha(
                TIPO_COMERCIO_CHOICES, ambulante.tipo_atuacao
            ),
            "tipo_estrutura_label": rotulo_escolha(
                TIPO_ESTRUTURA_CHOICES,
                estrutura.tipo_estrutura if estrutura else "",
            ),
            "situacao_conta_label": situacao_rotulos.get(situacao, situacao.title()),
            "modo_edicao": modo_edicao,
        }

    def get(self, request):
        ambulante = self._ambulante()
        form = PerfilAmbulanteForm(ambulante=ambulante)
        return render(
            request,
            self.template_name,
            self._contexto(
                ambulante,
                form,
                modo_edicao=request.GET.get("editar") == "1",
            ),
        )

    def post(self, request):
        ambulante = self._ambulante()
        form = PerfilAmbulanteForm(request.POST, request.FILES, ambulante=ambulante)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._contexto(ambulante, form, modo_edicao=True),
            )
        form.save()
        if form.cleaned_data.get("senha_nova"):
            update_session_auth_hash(request, ambulante)
            messages.success(
                request,
                "Perfil atualizado. A senha foi alterada com sucesso.",
            )
        else:
            messages.success(
                request,
                "Perfil atualizado. Os dados foram salvos com sucesso.",
            )
        return redirect("ambulante_perfil")


class ScoreAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, TemplateView):
    template_name = "ambulante/score.html"
    login_url = reverse_lazy("entrar")

    def get_context_data(self, **kwargs):
        from .score import resumo_score

        context = super().get_context_data(**kwargs)
        ambulante = Ambulante.objects.filter(pk=self.request.user.pk).first()
        context["ambulante"] = ambulante
        context.update(resumo_score(ambulante))
        return context


ETAPAS_CADASTRO = {
    1: DadosPessoaisCadastroForm,
    2: EnderecoCadastroForm,
    3: EmpresaCadastroForm,
    4: EstruturaCadastroForm,
    5: PontoCadastroForm,
    6: AnexosCadastroForm,
}


def _etapas_pendentes_cadastro(ambulante):
    extras = ambulante.dados_complementares or {}
    pendentes = 0
    pais = extras.get("pais_origem")
    naturalidade_ok = bool(pais) and (
        pais != "Brasil"
        or (extras.get("uf_nascimento") and extras.get("cidade_nascimento"))
    )
    dados_pessoais_ok = bool(
        ambulante.data_nasc
        and ambulante.escolaridade
        and ambulante.genero
        and ambulante.renda_mensal_estimada is not None
        and naturalidade_ok
    )
    if not dados_pessoais_ok:
        pendentes += 1
    if not ambulante.enderecos.exists():
        pendentes += 1
    if not (ambulante.cnpj or extras.get("sem_cnpj")):
        pendentes += 1
    estrutura = ambulante.estruturas.order_by("id").first()
    tem_estrutura = bool(
        estrutura
        and estrutura.tipo_estrutura
        and estrutura.dimensoes_metragem
        and estrutura.dimensoes_metragem > 0
    )
    if not (tem_estrutura and ambulante.tipo_atuacao):
        pendentes += 1
    if not ambulante.ponto_pretendido_id:
        pendentes += 1
    if not ambulante.documentos.exists():
        pendentes += 1
    return pendentes


def _resumo_status_painel(
    ambulante, licenca, *, cadastro_completo, documentos_rejeitados
):
    if not ambulante:
        return {
            "status_rotulo": "Sem conta",
            "status_badge": "danger",
            "status_com_alvara": False,
            "proximo_passo": "Faça login novamente para continuar.",
        }

    if not cadastro_completo:
        faltam = _etapas_pendentes_cadastro(ambulante)
        if faltam <= 0:
            proximo = (
                "Complete os dados pendentes do cadastro para solicitar a licença."
            )
        elif faltam == 1:
            proximo = "Falta 1 etapa para você emitir sua licença."
        else:
            proximo = f"Faltam {faltam} etapas para você emitir sua licença."
        return {
            "status_rotulo": "Cadastro Incompleto",
            "status_badge": "warning",
            "status_com_alvara": False,
            "proximo_passo": proximo,
        }

    if licenca:
        mensagens = {
            StatusLicenca.EM_ANALISE: "",
            StatusLicenca.PENDENCIA_DOCUMENTAL: (
                "Há pendência documental. Reenvie os anexos solicitados."
            ),
            StatusLicenca.APROVADO: (
                "Sua solicitação foi aprovada. Confira se falta pagar a taxa ou emitir o alvará."
            ),
            StatusLicenca.AGUARDANDO_PAGAMENTO: (
                "Pague a taxa de licenciamento para emitir seu alvará."
            ),
            StatusLicenca.ATIVO: (
                "Sua licença está ativa. Use a credencial digital quando for fiscalizado."
            ),
            StatusLicenca.VENCIDO: (
                "Sua licença venceu. Inicie a renovação pelo painel."
            ),
            StatusLicenca.SUSPENSO: (
                "Sua licença está suspensa. Fale com a prefeitura para regularizar."
            ),
            StatusLicenca.INDEFERIDO: (
                "Sua solicitação foi indeferida. Veja o motivo e corrija o cadastro."
            ),
            StatusLicenca.CANCELADO: (
                "Sua licença foi cancelada. Procure a prefeitura se precisar de orientação."
            ),
        }
        return {
            "status_rotulo": licenca.status,
            "status_badge": licenca.classe_badge,
            "status_com_alvara": True,
            "proximo_passo": mensagens.get(
                licenca.status,
                "Acompanhe o andamento da sua solicitação neste painel.",
            ),
        }

    if documentos_rejeitados:
        return {
            "status_rotulo": "Pendência Documental",
            "status_badge": "purple",
            "status_com_alvara": False,
            "proximo_passo": (
                "Reenvie os documentos rejeitados para a fiscalização retomar a análise."
            ),
        }

    return {
        "status_rotulo": "Cadastro Completo",
        "status_badge": "success",
        "status_com_alvara": False,
        "proximo_passo": (
            "Envie seus documentos na etapa de anexos para solicitar a licença."
        ),
    }


def _stepper_painel(ambulante, licenca, *, cadastro_completo, documentos_rejeitados):
    """Linha do tempo do painel: conta → dados → documentos → análise → licença."""
    etapas = [
        {"chave": "conta", "rotulo": "Conta Criada"},
        {"chave": "dados", "rotulo": "Dados do Ponto e Atividade"},
        {"chave": "documentos", "rotulo": "Documentos Anexados"},
        {"chave": "analise", "rotulo": "Análise da Prefeitura"},
        {"chave": "licenca", "rotulo": "Licença Liberada"},
    ]

    tem_documentos = bool(ambulante and ambulante.documentos.exists())
    docs_ok = tem_documentos and not documentos_rejeitados
    status = getattr(licenca, "status", None) if licenca else None

    if status == StatusLicenca.ATIVO:
        atual = 6
    elif status in (
        StatusLicenca.APROVADO,
        StatusLicenca.AGUARDANDO_PAGAMENTO,
    ):
        atual = 5
    elif status in (
        StatusLicenca.EM_ANALISE,
        StatusLicenca.PENDENCIA_DOCUMENTAL,
    ):
        atual = 4
    elif status in (
        StatusLicenca.VENCIDO,
        StatusLicenca.SUSPENSO,
        StatusLicenca.INDEFERIDO,
        StatusLicenca.CANCELADO,
    ):
        atual = 5
    elif docs_ok and cadastro_completo:
        atual = 4
    elif cadastro_completo or documentos_rejeitados:
        atual = 3
    else:
        atual = 2

    for indice, etapa in enumerate(etapas, start=1):
        if indice < atual:
            etapa["estado"] = "completed"
        elif indice == atual:
            etapa["estado"] = "active"
        else:
            etapa["estado"] = "pending"

    total = len(etapas)
    if atual > total:
        percent = 100
    else:
        percent = int(((atual - 1) / max(total - 1, 1)) * 100)

    return {
        "painel_stepper": etapas,
        "painel_stepper_percent": percent,
    }


def _card_protocolo_prazos(licenca):
    if not licenca:
        return {"mostrar_protocolo": False}

    status_visiveis = (
        StatusLicenca.EM_ANALISE,
        StatusLicenca.PENDENCIA_DOCUMENTAL,
        StatusLicenca.APROVADO,
        StatusLicenca.AGUARDANDO_PAGAMENTO,
        StatusLicenca.ATIVO,
    )
    if licenca.status not in status_visiveis:
        return {"mostrar_protocolo": False}

    return {
        "mostrar_protocolo": True,
        "protocolo_numero": licenca.protocolo,
        "protocolo_data_solicitacao": licenca.criado_em,
        "protocolo_prazo_texto": "Prazo estimado de até 5 dias úteis.",
        "protocolo_validade": licenca.data_vencimento,
        "protocolo_mostra_validade": bool(
            licenca.data_vencimento
            and licenca.status
            in (
                StatusLicenca.APROVADO,
                StatusLicenca.AGUARDANDO_PAGAMENTO,
                StatusLicenca.ATIVO,
            )
        ),
    }


class CadastroCompletoAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, View):
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
        categoria = categoria_do_ambulante(ambulante) if etapa == 6 else None
        return {
            "ambulante": ambulante,
            "etapa": etapa,
            "form": form,
            "cadastro_completo": ambulante.cadastro_completo,
            "concluido": concluido,
            "stepper_percent": int(((etapa - 1) / 5) * 100),
            "pontos_catalogo": (
                form.fields["ponto_pretendido"].queryset if etapa == 5 else None
            ),
            "categorias_catalogo": (
                form.fields["categoria_pretendida"].queryset if etapa == 5 else None
            ),
            "documentos": (
                ambulante.documentos.order_by("tipo_documento") if etapa == 6 else None
            ),
            "categoria_documentos": categoria,
            "tipos_obrigatorios": (
                tipos_obrigatorios(ambulante, categoria) if etapa == 6 else ()
            ),
            "tipos_faltando_envio": (
                tipos_faltando_envio(ambulante, categoria) if etapa == 6 else ()
            ),
            "tipos_faltando_aprovacao": (
                tipos_faltando_aprovacao(ambulante, categoria) if etapa == 6 else ()
            ),
            "pode_avancar_solicitacao": (
                pode_avancar_solicitacao(ambulante, categoria) if etapa == 6 else False
            ),
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
        acao = request.POST.get("acao", "proxima")
        form_kwargs = {"ambulante": ambulante}
        if etapa == 6:
            form_kwargs["acao"] = acao
        form = form_class(request.POST, request.FILES, **form_kwargs)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._contexto(ambulante, etapa, form),
            )

        form.save()
        ambulante.refresh_from_db()
        if acao == "salvar":
            messages.success(
                request,
                "Documentos salvos. O gestor verá os anexos pendentes na triagem.",
            )
            return redirect(f"{reverse('ambulante_cadastro')}?etapa=6")
        if acao == "enviar":
            if ambulante.cadastro_completo:
                from apps.licenciamento.services import abrir_requerimento

                abrir_requerimento(ambulante)
                messages.success(
                    request,
                    "Cadastro concluído. A solicitação entrou na fila de análise "
                    "da prefeitura. Acompanhe pelo protocolo em Meu Alvará.",
                )
                return redirect("ambulante_credencial")
            messages.error(
                request,
                "Ainda faltam dados obrigatórios (pessoais, endereço, "
                "empresa/atuação e estrutura) para concluir o cadastro.",
            )
            return redirect(f"{reverse('ambulante_cadastro')}?etapa={etapa}")

        proxima = min(etapa + 1, 6)
        messages.success(request, "Etapa salva...")
        return redirect(f"{reverse('ambulante_cadastro')}?etapa={proxima}")


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

    def get_context_data(self, **kwargs):
        from .views_gestor import contexto_inicio_gestor

        context = super().get_context_data(**kwargs)
        context.update(contexto_inicio_gestor(self.request.user))
        return context


class MasterTemplateView(LoginRequiredMixin, AcessoMasterMixin, TemplateView):
    """Base das telas do painel Master."""


class MasterAdminView(MasterTemplateView):
    template_name = "master/admin.html"

    def get_context_data(self, **kwargs):
        from apps.core.backup import listar_backups

        context = super().get_context_data(**kwargs)
        context["total_gestores_ativos"] = Gestor.objects.filter(ativo=True).count()
        context["total_fiscais"] = Fiscal.objects.count()
        context["total_ambulantes"] = Ambulante.objects.count()
        context["atividade_recente"] = UsuarioBase.objects.filter(
            last_login__isnull=False
        ).order_by("-last_login")[:8]
        backups = listar_backups()
        context["backups"] = backups[:5]
        context["ultimo_backup"] = backups[0] if backups else None
        admin = Administrador.objects.filter(pk=self.request.user.pk).first()
        context["pode_backup"] = bool(admin and admin.acesso_painel_tecnico)
        return context


class MasterBackupView(LoginRequiredMixin, AcessoMasterMixin, View):
    http_method_names = ("post", "options")

    def post(self, request, *args, **kwargs):
        from apps.core.backup import gerar_backup

        admin = Administrador.objects.filter(pk=request.user.pk).first()
        if not admin or not admin.acesso_painel_tecnico:
            raise PermissionDenied
        caminho = gerar_backup()
        messages.success(request, f"Backup restaurável gravado: {caminho.name}")
        return redirect("master_admin")


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
