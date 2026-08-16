from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.usuarios.models import Fiscal
from apps.usuarios.permissoes import RequerModuloMixin
from apps.usuarios.views import AcessoFiscalMixin

from .forms import BuscaCampoForm, EncerrarRotaForm, OcorrenciaForm, RegistroVisitaForm
from .models import OcorrenciaInspecao, RotaFiscal, StatusRota, TipoOcorrencia
from .services import (
    consultar_campo,
    inspecionar_qr,
    registrar_ocorrencia,
    tipo_sugerido_para,
)
from .services_rotas import (
    concluir_rota,
    iniciar_rota,
    paradas_para_mapa,
    proxima_parada,
    registrar_visita_parada,
    vincular_ocorrencia_a_parada,
)


class FiscalizacaoView(LoginRequiredMixin, AcessoFiscalMixin, RequerModuloMixin, View):
    template_name = "fiscal/fiscalizacao.html"
    login_url = reverse_lazy("fiscal_entrar")
    modulo_permissao = "leitura_qr"

    def _contexto(self, request, resultado=None, termo=""):
        fiscal = Fiscal.objects.filter(pk=request.user.pk).first()
        rotas_ativas = 0
        if fiscal:
            rotas_ativas = RotaFiscal.objects.filter(
                fiscal=fiscal,
                status__in=(StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO),
            ).count()
        return {
            "fiscal": fiscal,
            "form_busca": BuscaCampoForm(initial={"q": termo}),
            "termo": termo,
            "resultado": resultado,
            "rotas_ativas": rotas_ativas,
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


class RegistrarOcorrenciaView(
    LoginRequiredMixin, AcessoFiscalMixin, RequerModuloMixin, FormView
):
    template_name = "fiscal/registrar-ocorrencia.html"
    form_class = OcorrenciaForm
    login_url = reverse_lazy("fiscal_entrar")
    modulo_permissao = "ocorrencias"

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
        local = self.request.GET.get("local")
        if local:
            initial["local_ocorrencia"] = local
        if resultado and resultado.mensagem:
            initial["descricao"] = resultado.mensagem
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resultado = self._resultado_preenchido()
        context["fiscal"] = Fiscal.objects.filter(pk=self.request.user.pk).first()
        context["resultado"] = resultado
        context["tipos"] = TipoOcorrencia
        context["retorno_rota"] = self.request.GET.get("retorno_rota") or ""
        context["parada_id"] = self.request.GET.get("parada") or ""
        return context

    def form_valid(self, form):
        ocorrencia = registrar_ocorrencia(
            self.request.user,
            form.cleaned_data.get("ambulante"),
            form.cleaned_data["tipo_ocorrencia"],
            form.cleaned_data["descricao"],
            local_ocorrencia=form.cleaned_data.get("local_ocorrencia") or "",
            evidencia_foto=form.cleaned_data.get("evidencia_foto"),
            infracao=form.cleaned_data.get("infracao"),
            data_ocorrencia=form.cleaned_data.get("data_ocorrencia"),
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
        retorno_rota = self.request.GET.get("retorno_rota") or self.request.POST.get(
            "retorno_rota"
        )
        parada_id = self.request.GET.get("parada") or self.request.POST.get("parada_id")
        if parada_id:
            fiscal = Fiscal.objects.filter(pk=self.request.user.pk).first()
            if fiscal:
                try:
                    registrar_visita_parada(
                        fiscal,
                        int(parada_id),
                        {
                            "encontrou_ambulante": True,
                            "foi_recebido": True,
                            "observacoes": "Visita com ocorrência registrada.",
                            "ocorrencia": ocorrencia,
                        },
                    )
                except (ValueError, TypeError):
                    try:
                        vincular_ocorrencia_a_parada(
                            int(parada_id), ocorrencia, fiscal
                        )
                    except (ValueError, TypeError):
                        pass
        if retorno_rota:
            return redirect("fiscal_rota_execucao", pk=retorno_rota)
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


class FiscalRotasView(LoginRequiredMixin, AcessoFiscalMixin, RequerModuloMixin, TemplateView):
    template_name = "fiscal/rotas.html"
    login_url = reverse_lazy("fiscal_entrar")
    modulo_permissao = "rotas_fiscais"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fiscal = Fiscal.objects.filter(pk=self.request.user.pk).first()
        context["fiscal"] = fiscal
        context["rotas"] = (
            RotaFiscal.objects.filter(fiscal=fiscal)
            .prefetch_related("paradas")
            .order_by("-criado_em")
            if fiscal
            else []
        )
        return context


class FiscalRotaExecucaoView(
    LoginRequiredMixin, AcessoFiscalMixin, RequerModuloMixin, View
):
    template_name = "fiscal/rota-execucao.html"
    login_url = reverse_lazy("fiscal_entrar")
    modulo_permissao = "rotas_fiscais"

    def _contexto_execucao(self, fiscal, rota, form_encerrar=None):
        proxima = proxima_parada(rota)
        return {
            "fiscal": fiscal,
            "rota": rota,
            "paradas_mapa": paradas_para_mapa(rota),
            "proxima_parada": proxima,
            "form_encerrar": form_encerrar or EncerrarRotaForm(),
            "pode_iniciar": rota.status == StatusRota.AGENDADA,
            "pode_encerrar": rota.status
            in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO),
            "rota_em_campo": rota.status
            in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO),
        }

    def get(self, request, pk):
        fiscal = get_object_or_404(Fiscal, pk=request.user.pk)
        rota = get_object_or_404(
            RotaFiscal.objects.prefetch_related(
                "paradas__ambulante", "paradas__ponto", "paradas__visita"
            ),
            pk=pk,
            fiscal=fiscal,
        )
        return render(
            request, self.template_name, self._contexto_execucao(fiscal, rota)
        )

    def post(self, request, pk):
        fiscal = get_object_or_404(Fiscal, pk=request.user.pk)
        acao = request.POST.get("acao")
        try:
            if acao == "iniciar":
                iniciar_rota(fiscal, pk)
                messages.success(request, "Rota iniciada. Siga a próxima parada no mapa.")
            elif acao == "encerrar":
                form = EncerrarRotaForm(request.POST)
                if not form.is_valid():
                    rota = get_object_or_404(
                        RotaFiscal.objects.prefetch_related(
                            "paradas__ambulante", "paradas__ponto", "paradas__visita"
                        ),
                        pk=pk,
                        fiscal=fiscal,
                    )
                    return render(
                        request,
                        self.template_name,
                        self._contexto_execucao(fiscal, rota, form),
                    )
                concluir_rota(
                    fiscal,
                    pk,
                    incompleta=form.cleaned_data.get("incompleta"),
                    relato=form.cleaned_data.get("relato") or "",
                )
                messages.success(
                    request, "Rota encerrada. O resumo foi enviado ao gestor."
                )
                return redirect("fiscal_rotas")
        except ValueError as erro:
            messages.error(request, str(erro))
        return redirect("fiscal_rota_execucao", pk=pk)


class FiscalParadaRegistroView(
    LoginRequiredMixin, AcessoFiscalMixin, RequerModuloMixin, View
):
    template_name = "fiscal/parada-registro.html"
    login_url = reverse_lazy("fiscal_entrar")
    modulo_permissao = "rotas_fiscais"

    def _parada(self, request, pk, parada_id):
        from .models import ParadaRota

        fiscal = get_object_or_404(Fiscal, pk=request.user.pk)
        parada = get_object_or_404(
            ParadaRota.objects.select_related(
                "rota", "ambulante", "ponto"
            ).prefetch_related("visita"),
            pk=parada_id,
            rota_id=pk,
            rota__fiscal=fiscal,
        )
        return fiscal, parada

    def _contexto_parada(self, fiscal, parada, form=None, resultado=None, termo=""):
        identificacao_bate = False
        if resultado and resultado.ambulante:
            identificacao_bate = resultado.ambulante.pk == parada.ambulante_id
        if form is None:
            initial = {}
            if identificacao_bate:
                initial["encontrou_ambulante"] = True
            form = RegistroVisitaForm(initial=initial)
        return {
            "fiscal": fiscal,
            "parada": parada,
            "rota": parada.rota,
            "form": form,
            "resultado": resultado,
            "termo": termo,
            "identificacao_bate": identificacao_bate,
        }

    def _resultado_identificacao(self, request):
        qr = (request.GET.get("qr") or "").strip()
        termo = (request.GET.get("q") or "").strip()
        if qr:
            return inspecionar_qr(qr), qr
        if termo:
            return consultar_campo(termo), termo
        return None, ""

    def get(self, request, pk, parada_id):
        fiscal, parada = self._parada(request, pk, parada_id)
        atual = proxima_parada(parada.rota)
        if (
            parada.rota.status in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO)
            and atual
            and atual.pk != parada.pk
            and parada.status == "PENDENTE"
        ):
            messages.warning(
                request,
                f"Siga a ordem da rota. A próxima parada é a #{atual.ordem} — {atual.ambulante.nome_completo}.",
            )
            return redirect("fiscal_rota_execucao", pk=pk)
        resultado, termo = self._resultado_identificacao(request)
        return render(
            request,
            self.template_name,
            self._contexto_parada(fiscal, parada, resultado=resultado, termo=termo),
        )

    def post(self, request, pk, parada_id):
        fiscal, parada = self._parada(request, pk, parada_id)
        atual = proxima_parada(parada.rota)
        if (
            parada.rota.status in (StatusRota.AGENDADA, StatusRota.EM_ANDAMENTO)
            and atual
            and atual.pk != parada.pk
            and parada.status == "PENDENTE"
        ):
            messages.warning(
                request,
                f"Siga a ordem da rota. A próxima parada é a #{atual.ordem}.",
            )
            return redirect("fiscal_rota_execucao", pk=pk)
        form = RegistroVisitaForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._contexto_parada(fiscal, parada, form=form),
            )
        dados = form.cleaned_data
        if dados.get("houve_ocorrencia"):
            local = ""
            if parada.ponto:
                local = parada.ponto.nome_identificacao
            from urllib.parse import quote

            url = reverse("fiscal_ocorrencia")
            params = (
                f"?ambulante={parada.ambulante_id}"
                f"&parada={parada.pk}"
                f"&retorno_rota={parada.rota_id}"
                f"&local={quote(local)}"
            )
            try:
                registrar_visita_parada(
                    fiscal,
                    parada.pk,
                    {
                        "encontrou_ambulante": dados.get("encontrou_ambulante"),
                        "foi_recebido": dados.get("foi_recebido"),
                        "observacoes": dados.get("observacoes") or "",
                    },
                )
            except ValueError as erro:
                messages.error(request, str(erro))
                return redirect("fiscal_rota_execucao", pk=pk)
            return redirect(url + params)
        try:
            registrar_visita_parada(
                fiscal,
                parada.pk,
                {
                    "encontrou_ambulante": dados.get("encontrou_ambulante"),
                    "foi_recebido": dados.get("foi_recebido"),
                    "observacoes": dados.get("observacoes") or "",
                },
            )
            messages.success(request, f"Parada #{parada.ordem} registrada.")
        except ValueError as erro:
            messages.error(request, str(erro))
        return redirect("fiscal_rota_execucao", pk=pk)


class AprovarOcorrenciaGestorView(LoginRequiredMixin, RequerModuloMixin, View):
    """
    View de Gestor para Aprovação: altera o status_gestor para 'Aprovada'
    e invoca imediatamente a função processar_ocorrencia.
    """

    modulo_permissao = "ocorrencias"

    def post(self, request, *args, **kwargs):
        from apps.usuarios.score import processar_ocorrencia

        ocorrencia_id = kwargs.get("pk")
        ocorrencia = get_object_or_404(OcorrenciaInspecao, pk=ocorrencia_id)

        ocorrencia.status_gestor = "APROVADA"
        ocorrencia.save(update_fields=["status_gestor"])

        processar_ocorrencia(ocorrencia.id)

        messages.success(request, "Ocorrência aprovada com sucesso.")
        return redirect("fiscal_painel")
