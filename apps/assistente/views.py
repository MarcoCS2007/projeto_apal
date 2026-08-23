from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from apps.usuarios.models import Ambulante
from apps.usuarios.views import AcessoAmbulanteMixin, AcessoBackofficeMixin

from .forms import PerguntaAssistenteForm
from .models import LogAssistente
from .services import SUGESTOES_ASSISTENTE, responder_pergunta


class AssistenteAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, FormView):
    template_name = "ambulante/assistente.html"
    form_class = PerguntaAssistenteForm
    login_url = reverse_lazy("entrar")
    success_url = reverse_lazy("ambulante_assistente")

    def _ambulante(self):
        return Ambulante.objects.get(pk=self.request.user.pk)

    def form_valid(self, form):
        responder_pergunta(self._ambulante(), form.cleaned_data["pergunta"])
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        historico = list(
            LogAssistente.objects.filter(ambulante=self._ambulante()).order_by(
                "-criado_em"
            )[:20]
        )
        historico.reverse()
        context["historico"] = historico
        context["sugestoes"] = SUGESTOES_ASSISTENTE
        return context


class AssistenteGestorView(LoginRequiredMixin, AcessoBackofficeMixin, TemplateView):
    """Demo de interface do copiloto do gestor (respostas hardcoded no front)."""

    template_name = "gestor/assistente.html"
    login_url = reverse_lazy("login")
