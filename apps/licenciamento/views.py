from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.core.qr_imagem import renderizar_qr_png
from apps.core.qrcode import validar_codigo_qr
from apps.usuarios.models import Ambulante
from apps.usuarios.permissoes import (
    RequerModuloMixin,
    gestor_recorte_sanitario,
    pode_ver_documento,
)
from apps.usuarios.views import AcessoAmbulanteMixin, AcessoBackofficeMixin

from .forms import CategoriaProdutoForm
from .models import (
    CategoriaProduto,
    DocumentoAnexo,
    LicencaAlvara,
    StatusAprovacaoDocumento,
    TipoDocumento,
)
from .services import (
    licenca_ativa,
    licenca_atual,
    licencas_do_ambulante,
    renovar_licenca,
    simular_pagamento_taxa,
)


class GestorCategoriasView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    template_name = "gestor/gerenciar-categorias.html"
    modulo_permissao = "solicitacao_licenca"

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
            return render(request, self.template_name, self._contexto(form, categoria))
        form.save()
        if categoria:
            messages.success(request, "Categoria atualizada com sucesso.")
        else:
            messages.success(request, "Categoria cadastrada com sucesso.")
        return redirect("gestor_categorias")


class GestorCategoriaExcluirView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    http_method_names = ("post", "options")
    modulo_permissao = "solicitacao_licenca"

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


class GestorTriagemView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    template_name = "gestor/triagem.html"
    modulo_permissao = "solicitacao_licenca"

    def get(self, request):
        documentos = (
            DocumentoAnexo.objects.select_related("ambulante")
            .filter(status_aprovacao=StatusAprovacaoDocumento.PENDENTE)
            .order_by("data_upload", "id")
        )
        if gestor_recorte_sanitario(request.user):
            documentos = documentos.filter(
                tipo_documento=TipoDocumento.LAUDO_SANITARIO
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
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, DocumentoHtmxMixin, View
):
    http_method_names = ("post", "options")
    modulo_permissao = "solicitacao_licenca"

    def post(self, request, pk):
        documento = get_object_or_404(DocumentoAnexo, pk=pk)
        if not pode_ver_documento(request.user, documento):
            raise PermissionDenied
        documento.aprovar()
        return self._responder(request, documento)


class RejeitarDocumentoView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, DocumentoHtmxMixin, View
):
    http_method_names = ("post", "options")
    modulo_permissao = "solicitacao_licenca"

    def post(self, request, pk):
        documento = get_object_or_404(DocumentoAnexo, pk=pk)
        if not pode_ver_documento(request.user, documento):
            raise PermissionDenied
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


class CredencialAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, TemplateView):
    template_name = "ambulante/credencial.html"
    login_url = "entrar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ambulante = get_object_or_404(Ambulante, pk=self.request.user.pk)
        ativa = licenca_ativa(ambulante)
        qr_liberado = bool(
            ativa
            and ativa.qr_valido
            and ambulante.codigo_qr_code
            and validar_codigo_qr(ambulante.codigo_qr_code) is not None
        )
        context.update(
            {
                "ambulante": ambulante,
                "licenca": ativa if qr_liberado else licenca_atual(ambulante),
                "qr_liberado": qr_liberado,
            }
        )
        return context


class CredencialQrPngView(LoginRequiredMixin, AcessoAmbulanteMixin, View):
    login_url = "entrar"
    http_method_names = ("get", "head", "options")

    def get(self, request):
        ambulante = get_object_or_404(Ambulante, pk=request.user.pk)
        licenca = licenca_ativa(ambulante)
        codigo = ambulante.codigo_qr_code
        if (
            licenca is None
            or not licenca.qr_valido
            or not codigo
            or validar_codigo_qr(codigo) is None
        ):
            raise Http404("Não há QR Code válido para esta credencial.")
        png = renderizar_qr_png(codigo)
        response = HttpResponse(png, content_type="image/png")
        nome = f"credencial-{licenca.numero_licenca or licenca.pk}.png"
        if request.GET.get("download"):
            response["Content-Disposition"] = f'attachment; filename="{nome}"'
        else:
            response["Content-Disposition"] = "inline"
        return response


class AlvaraAmbulanteView(
    LoginRequiredMixin, AcessoAmbulanteMixin, RequerModuloMixin, TemplateView
):
    template_name = "ambulante/alvara.html"
    login_url = "entrar"
    modulo_permissao = "solicitacao_licenca"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ambulante = get_object_or_404(Ambulante, pk=self.request.user.pk)
        historico = licencas_do_ambulante(ambulante)
        context.update(
            {
                "ambulante": ambulante,
                "licenca": historico.first(),
                "historico": historico,
            }
        )
        return context


class SimularPagamentoAlvaraView(LoginRequiredMixin, AcessoAmbulanteMixin, View):
    template_name = "ambulante/_painel_taxa.html"
    http_method_names = ("post", "options")
    login_url = "entrar"

    def post(self, request, pk):
        ambulante = get_object_or_404(Ambulante, pk=request.user.pk)
        licenca = get_object_or_404(LicencaAlvara, pk=pk, ambulante=ambulante)
        try:
            simular_pagamento_taxa(licenca, ambulante)
        except ValidationError as exc:
            if request.headers.get("HX-Request"):
                return HttpResponseBadRequest(exc.messages[0])
            messages.error(request, exc.messages[0])
            return redirect("ambulante_alvara")
        licenca.refresh_from_db()
        contexto = {"licenca": licenca, "oob_badge": True}
        if request.headers.get("HX-Request"):
            return render(request, self.template_name, contexto)
        messages.success(request, "Pagamento da taxa municipal confirmado.")
        return redirect("ambulante_alvara")


class RenovarLicencaView(
    LoginRequiredMixin, AcessoAmbulanteMixin, RequerModuloMixin, View
):
    http_method_names = ("post", "options")
    login_url = "entrar"
    modulo_permissao = "solicitacao_licenca"

    def post(self, request, pk):
        ambulante = get_object_or_404(Ambulante, pk=request.user.pk)
        licenca = get_object_or_404(LicencaAlvara, pk=pk, ambulante=ambulante)
        try:
            nova, criada = renovar_licenca(licenca, ambulante)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("ambulante_alvara")
        if criada:
            messages.success(
                request,
                f"Renovação aberta com o protocolo {nova.protocolo}. "
                "Acompanhe a análise da prefeitura.",
            )
        else:
            messages.info(
                request,
                f"Já existe um requerimento em aberto ({nova.protocolo}).",
            )
        return redirect("ambulante_alvara")


class RelatorioOcupacaoView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    """HTMX (HTML) e JSON de ocupação/indicadores para o dashboard do gestor."""

    template_name = "gestor/_indicadores.html"
    modulo_permissao = "relatorios"

    def get(self, request):
        from .relatorios import indicadores_gerenciais, indicadores_json

        dados = indicadores_gerenciais(
            bairro=request.GET.get("bairro", ""),
            origem=request.GET.get("origem", ""),
            periodo_dias=request.GET.get("periodo", 30),
        )
        html = request.headers.get("HX-Request") or request.GET.get("formato") == "html"
        if html:
            return render(request, self.template_name, dados)
        return JsonResponse(indicadores_json(dados))


class DocumentoArquivoView(LoginRequiredMixin, View):
    """Entrega o anexo só para quem tem direito de ver (storage controlado)."""

    def get(self, request, pk):
        documento = get_object_or_404(DocumentoAnexo, pk=pk)
        if not pode_ver_documento(request.user, documento):
            raise PermissionDenied
        if not documento.arquivo:
            raise Http404
        return FileResponse(
            documento.arquivo.open("rb"),
            as_attachment=False,
            filename=documento.arquivo.name.rsplit("/", 1)[-1],
        )

