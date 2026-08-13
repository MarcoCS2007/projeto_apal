from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.usuarios.views import AcessoBackofficeMixin

from .forms import CategoriaProdutoForm
from .models import CategoriaProduto, DocumentoAnexo, StatusAprovacaoDocumento


class GestorCategoriasView(LoginRequiredMixin, AcessoBackofficeMixin, View):
    template_name = "gestor/gerenciar-categorias.html"

    def _categoria(self, pk):
        if not pk:
            return None
        return get_object_or_404(CategoriaProduto, pk=pk, ativo=True)

    def _contexto(self, form, categoria=None):
        return {
            "form": form,
            "categoria_editando": categoria,
            "categorias": CategoriaProduto.objects.filter(ativo=True).order_by(
                "nome_categoria"
            ),
        }

    def get(self, request, pk=None):
        categoria = self._categoria(pk)
        form = CategoriaProdutoForm(instance=categoria)
        return render(request, self.template_name, self._contexto(form, categoria))

    def post(self, request, pk=None):
        categoria = self._categoria(pk)
        form = CategoriaProdutoForm(request.POST, instance=categoria)
        if not form.is_valid():
            return render(
                request, self.template_name, self._contexto(form, categoria)
            )
        form.save()
        if categoria:
            messages.success(request, "Categoria atualizada com sucesso.")
        else:
            messages.success(request, "Categoria cadastrada com sucesso.")
        return redirect("gestor_categorias")


class GestorCategoriaExcluirView(LoginRequiredMixin, AcessoBackofficeMixin, View):
    http_method_names = ("post", "options")

    def post(self, request, pk):
        categoria = get_object_or_404(CategoriaProduto, pk=pk, ativo=True)
        if categoria.licencas.filter(ativo=True).exists():
            messages.error(
                request,
                "Não é possível excluir uma categoria vinculada a licenças ativas.",
            )
            return redirect("gestor_categorias")
        categoria.ativo = False
        categoria.save(update_fields=["ativo", "atualizado_em"])
        messages.success(request, "Categoria excluída.")
        return redirect("gestor_categorias")


class GestorTriagemView(LoginRequiredMixin, AcessoBackofficeMixin, View):
    template_name = "gestor/triagem.html"

    def get(self, request):
        documentos = (
            DocumentoAnexo.objects.select_related("ambulante")
            .filter(status_aprovacao=StatusAprovacaoDocumento.PENDENTE)
            .order_by("data_upload", "id")
        )
        return render(
            request,
            self.template_name,
            {
                "documentos": documentos,
                "total_pendentes": documentos.count(),
            },
        )


class DocumentoHtmxMixin:
    template_name = "gestor/_documento_row.html"

    def _responder(self, request, documento):
        if request.headers.get("HX-Request"):
            return render(request, self.template_name, {"documento": documento})
        return redirect("gestor_triagem")


class AprovarDocumentoView(
    LoginRequiredMixin, AcessoBackofficeMixin, DocumentoHtmxMixin, View
):
    http_method_names = ("post", "options")

    def post(self, request, pk):
        documento = get_object_or_404(DocumentoAnexo, pk=pk)
        documento.aprovar()
        return self._responder(request, documento)


class RejeitarDocumentoView(
    LoginRequiredMixin, AcessoBackofficeMixin, DocumentoHtmxMixin, View
):
    http_method_names = ("post", "options")

    def post(self, request, pk):
        documento = get_object_or_404(DocumentoAnexo, pk=pk)
        motivo = request.POST.get("justificativa") or request.POST.get(
            "motivo_rejeicao", ""
        )
        try:
            documento.rejeitar(motivo)
        except ValidationError as exc:
            if request.headers.get("HX-Request"):
                return HttpResponseBadRequest(exc.messages[0])
            messages.error(request, exc.messages[0])
            return redirect("gestor_triagem")
        return self._responder(request, documento)
