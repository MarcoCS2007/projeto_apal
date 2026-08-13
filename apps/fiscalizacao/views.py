from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView

from apps.usuarios.models import Fiscal
from apps.usuarios.views import AcessoFiscalMixin

from .forms import BuscaCampoForm, OcorrenciaForm
from .models import TipoOcorrencia
from .services import (
    consultar_campo,
    inspecionar_qr,
    registrar_ocorrencia,
    tipo_sugerido_para,
)


class FiscalizacaoView(LoginRequiredMixin, AcessoFiscalMixin, View):
    template_name = "fiscal/fiscalizacao.html"
    login_url = reverse_lazy("fiscal_entrar")

    def _contexto(self, request, resultado=None, termo=""):
        fiscal = Fiscal.objects.filter(pk=request.user.pk).first()
        return {
            "fiscal": fiscal,
            "form_busca": BuscaCampoForm(initial={"q": termo}),
            "termo": termo,
            "resultado": resultado,
        }

    def get(self, request):
        qr = (request.GET.get("qr") or "").strip()
        termo = (request.GET.get("q") or "").strip()
        resultado = None
        if qr:
            resultado = inspecionar_qr(qr)
            termo = qr
        elif termo:
            resultado = consultar_campo(termo)
        return render(
            request, self.template_name, self._contexto(request, resultado, termo)
        )

    def post(self, request):
        form = BuscaCampoForm(request.POST)
        termo = ""
        if form.is_valid():
            termo = (form.cleaned_data.get("q") or "").strip()
        if not termo:
            termo = (request.POST.get("qr") or "").strip()
        if termo:
            return redirect(f"{reverse('fiscal_painel')}?q={termo}")
        return render(request, self.template_name, self._contexto(request))


class RegistrarOcorrenciaView(LoginRequiredMixin, AcessoFiscalMixin, FormView):
    template_name = "fiscal/registrar-ocorrencia.html"
    form_class = OcorrenciaForm
    login_url = reverse_lazy("fiscal_entrar")

    def get_initial(self):
        initial = super().get_initial()
        resultado = self._resultado_preenchido()
        if resultado and resultado.ambulante:
            initial["ambulante_id"] = resultado.ambulante.pk
            initial["identificacao"] = (
                resultado.licenca.numero_licenca
                if resultado.licenca and resultado.licenca.numero_licenca
                else resultado.ambulante.cpf_formatado
            )
        motivo = self.request.GET.get("motivo") or (
            resultado.motivo if resultado else ""
        )
        tipo = self.request.GET.get("tipo") or tipo_sugerido_para(motivo)
        if tipo:
            initial["tipo_ocorrencia"] = tipo
        if resultado and resultado.licenca and resultado.licenca.ponto_ocupacao:
            initial["local_ocorrencia"] = (
                resultado.licenca.ponto_ocupacao.nome_identificacao
            )
        if resultado and resultado.mensagem:
            initial["descricao"] = resultado.mensagem
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resultado = self._resultado_preenchido()
        context["fiscal"] = Fiscal.objects.filter(pk=self.request.user.pk).first()
        context["resultado"] = resultado
        context["tipos"] = TipoOcorrencia
        return context

    def form_valid(self, form):
        ocorrencia = registrar_ocorrencia(
            self.request.user,
            form.cleaned_data.get("ambulante"),
            form.cleaned_data["tipo_ocorrencia"],
            form.cleaned_data["descricao"],
            local_ocorrencia=form.cleaned_data.get("local_ocorrencia") or "",
            evidencia_foto=form.cleaned_data.get("evidencia_foto"),
        )
        alvo = (
            ocorrencia.ambulante.nome_completo
            if ocorrencia.ambulante
            else "infrator não identificado"
        )
        messages.success(
            self.request,
            f"Ocorrência #{ocorrencia.pk} registrada ({ocorrencia.tipo_ocorrencia}) — {alvo}.",
        )
        return redirect("fiscal_painel")

    def _resultado_preenchido(self):
        qr = (self.request.GET.get("qr") or "").strip()
        termo = (self.request.GET.get("q") or "").strip()
        ambulante_id = self.request.GET.get("ambulante") or self.request.POST.get(
            "ambulante_id"
        )
        if qr:
            return inspecionar_qr(qr)
        if termo:
            return consultar_campo(termo)
        if ambulante_id:
            return self._por_id(ambulante_id)
        return None

    def _por_id(self, ambulante_id):
        from apps.usuarios.models import Ambulante

        ambulante = Ambulante.objects.filter(pk=ambulante_id).first()
        if ambulante is None:
            return None
        return consultar_campo(ambulante.cpf)
