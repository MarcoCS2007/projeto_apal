from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.usuarios.views import AcessoBackofficeMixin

from .forms import PontoOcupacaoForm
from .models import PontoOcupacao


class GestorPontosView(LoginRequiredMixin, AcessoBackofficeMixin, View):
    template_name = "gestor/gerenciar-pontos.html"

    def _ponto(self, pk):
        if not pk:
            return None
        return get_object_or_404(PontoOcupacao, pk=pk, ativo=True)

    def _contexto(self, form, ponto=None):
        return {
            "form": form,
            "ponto_editando": ponto,
            "pontos": PontoOcupacao.objects.filter(ativo=True).order_by(
                "bairro", "nome_identificacao"
            ),
        }

    def get(self, request, pk=None):
        ponto = self._ponto(pk)
        form = PontoOcupacaoForm(instance=ponto)
        return render(request, self.template_name, self._contexto(form, ponto))

    def post(self, request, pk=None):
        ponto = self._ponto(pk)
        form = PontoOcupacaoForm(request.POST, instance=ponto)
        if not form.is_valid():
            return render(request, self.template_name, self._contexto(form, ponto))
        form.save()
        if ponto:
            messages.success(request, "Ponto de ocupação atualizado com sucesso.")
        else:
            messages.success(request, "Ponto de ocupação cadastrado com sucesso.")
        return redirect("gestor_pontos")


class GestorPontoExcluirView(LoginRequiredMixin, AcessoBackofficeMixin, View):
    http_method_names = ("post", "options")

    def post(self, request, pk):
        ponto = get_object_or_404(PontoOcupacao, pk=pk, ativo=True)
        if ponto.tem_licenca_ativa():
            messages.error(
                request,
                "Não é possível excluir um ponto com licença ativa.",
            )
            return redirect("gestor_pontos")
        ponto.ativo = False
        ponto.save(update_fields=["ativo", "atualizado_em"])
        messages.success(request, "Ponto de ocupação excluído.")
        return redirect("gestor_pontos")
