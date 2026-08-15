from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from xhtml2pdf import pisa

from apps.espacos.models import PontoOcupacao
from apps.fiscalizacao.forms import AuditoriaOcorrenciaForm, FiltroOcorrenciaForm
from apps.fiscalizacao.models import (
    OcorrenciaInspecao,
    StatusOcorrencia,
    TipoOcorrencia,
)
from apps.fiscalizacao.services import auditar_ocorrencia, filtrar_ocorrencias
from apps.licenciamento.forms import EmitirAlvaraForm, ParecerLicencaForm
from apps.licenciamento.models import (
    STATUS_FILA,
    STATUS_LISTAGEM_GESTOR,
    DocumentoAnexo,
    LicencaAlvara,
    StatusAprovacaoDocumento,
    StatusLicenca,
    StatusSolicitacao,
)
from apps.licenciamento.services import (
    aplicar_parecer,
    emitir_alvara,
    marcar_licencas_vencidas,
)
from apps.usuarios.forms_gestor import EditarAmbulanteGestorForm
from apps.usuarios.models import Ambulante, Gestor, LogAcessoDossie
from apps.usuarios.permissoes import RequerModuloMixin
from apps.usuarios.views import AcessoBackofficeMixin


class PainelGestorMixin(LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin):
    """Views web do backoffice restritas a Gestor e Administrador."""


class GestorAmbulantesView(PainelGestorMixin, TemplateView):
    template_name = "gestor/ambulantes-cadastrados.html"
    modulo_permissao = "solicitacao_licenca"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busca = self.request.GET.get("q", "").strip()
        ambulantes = Ambulante.objects.prefetch_related(
            "enderecos", "estruturas", "licencas"
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


class GestorAmbulanteEditarView(PainelGestorMixin, View):
    template_name = "gestor/editar-ambulante.html"
    modulo_permissao = "solicitacao_licenca"

    def _ambulante(self, pk):
        return get_object_or_404(Ambulante, pk=pk)

    def get(self, request, pk):
        ambulante = self._ambulante(pk)
        form = EditarAmbulanteGestorForm(ambulante=ambulante)
        return render(
            request,
            self.template_name,
            {"form": form, "ambulante": ambulante},
        )

    def post(self, request, pk):
        ambulante = self._ambulante(pk)
        form = EditarAmbulanteGestorForm(request.POST, ambulante=ambulante)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "ambulante": ambulante},
            )
        form.save()
        messages.success(request, "Dados cadastrais atualizados.")
        return redirect("gestor_dossie", pk=ambulante.pk)


class GestorAmbulanteAcaoView(PainelGestorMixin, View):
    http_method_names = ("post",)
    modulo_permissao = "solicitacao_licenca"

    def post(self, request, pk):
        ambulante = get_object_or_404(Ambulante, pk=pk)
        acao = request.POST.get("acao")
        if acao == "suspender":
            ambulante.aplicar_situacao_conta("suspensa")
            ambulante.licencas.filter(status=StatusLicenca.ATIVO).update(
                status=StatusLicenca.SUSPENSO
            )
            from apps.usuarios.score import pontuar_licenca_suspensa

            pontuar_licenca_suspensa(ambulante)
            messages.success(request, "Conta e licença ativa suspensas.")
        elif acao == "ativar":
            ambulante.aplicar_situacao_conta("ativa")
            ambulante.licencas.filter(status=StatusLicenca.SUSPENSO).update(
                status=StatusLicenca.ATIVO
            )
            messages.success(request, "Conta reativada.")
        elif acao == "cancelar":
            ambulante.aplicar_situacao_conta("cancelada")
            ambulante.licencas.exclude(
                status__in=(StatusLicenca.CANCELADO, StatusSolicitacao.INDEFERIDO)
            ).update(status=StatusLicenca.CANCELADO)
            from apps.usuarios.score import pontuar_licenca_cancelada

            pontuar_licenca_cancelada(ambulante)
            messages.success(request, "Conta e licenças canceladas.")
        else:
            messages.error(request, "Ação inválida.")
            return redirect("gestor_ambulantes")
        proximo = request.POST.get("next") or reverse("gestor_ambulantes")
        return redirect(proximo)


class GestorDossieView(PainelGestorMixin, TemplateView):
    template_name = "gestor/dossie.html"
    modulo_permissao = "solicitacao_licenca"

    def get(self, request, *args, **kwargs):
        ambulante = get_object_or_404(Ambulante, pk=self.kwargs["pk"])
        LogAcessoDossie.objects.create(usuario=request.user, ambulante=ambulante)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ambulante = get_object_or_404(
            Ambulante.objects.prefetch_related(
                "enderecos",
                "estruturas",
                "documentos",
                "licencas__categoria_produto",
                "licencas__ponto_ocupacao",
                "ocorrencias_recebidas__fiscal",
            ),
            pk=self.kwargs["pk"],
        )
        licenca_atual = ambulante.licencas.order_by("-criado_em").first()
        estrutura = ambulante.estruturas.order_by("id").first()
        endereco = ambulante.enderecos.order_by("id").first()
        context.update(
            {
                "ambulante": ambulante,
                "estrutura": estrutura,
                "endereco": endereco,
                "licenca_atual": licenca_atual,
                "licencas": ambulante.licencas.all(),
                "documentos": ambulante.documentos.order_by("-data_upload"),
                "ocorrencias": ambulante.ocorrencias_recebidas.select_related(
                    "fiscal"
                ).order_by("-criado_em"),
                "requerimento_aberto": ambulante.licencas.filter(
                    status__in=STATUS_FILA
                ).first(),
            }
        )
        from apps.usuarios.score import resumo_score

        context.update(resumo_score(ambulante))
        return context


class GestorFilaView(PainelGestorMixin, TemplateView):
    template_name = "gestor/em-analise.html"
    modulo_permissao = "solicitacao_licenca"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busca = self.request.GET.get("q", "").strip()
        processos = (
            LicencaAlvara.objects.filter(status__in=STATUS_FILA)
            .select_related(
                "ambulante",
                "categoria_produto",
                "ponto_ocupacao",
                "estrutura_trabalho",
            )
            .order_by("criado_em")
        )
        if busca:
            processos = processos.filter(
                Q(protocolo__icontains=busca)
                | Q(numero_licenca__icontains=busca)
                | Q(ambulante__nome__icontains=busca)
                | Q(ambulante__sobrenome__icontains=busca)
                | Q(ambulante__cpf__icontains=busca)
            )
        context["busca"] = busca
        context["processos"] = processos
        context["total_processos"] = processos.count()
        return context


class GestorAnalisarLicencaView(PainelGestorMixin, View):
    template_name = "gestor/analisar-licenca.html"
    modulo_permissao = "solicitacao_licenca"

    def _licenca(self, pk):
        return get_object_or_404(
            LicencaAlvara.objects.select_related(
                "ambulante",
                "categoria_produto",
                "ponto_ocupacao",
                "estrutura_trabalho",
                "gestor_responsavel",
            ),
            pk=pk,
        )

    def _contexto(self, licenca, form):
        ambulante = licenca.ambulante
        estrutura = (
            licenca.estrutura_trabalho or ambulante.estruturas.order_by("id").first()
        )
        ponto = licenca.ponto_ocupacao or ambulante.ponto_pretendido
        alerta_metragem = None
        if estrutura and ponto and estrutura.dimensoes_metragem > ponto.metragem_maxima:
            alerta_metragem = (
                f"Metragem da estrutura ({estrutura.dimensoes_metragem} m²) "
                f"maior que o limite do ponto ({ponto.metragem_maxima} m²)."
            )
        escalas = licenca.escalas.order_by("id")
        return {
            "licenca": licenca,
            "form": form,
            "ambulante": ambulante,
            "estrutura": estrutura,
            "ponto": ponto,
            "documentos": ambulante.documentos.order_by("-data_upload"),
            "alerta_metragem": alerta_metragem,
            "ponto_disponivel": bool(ponto and ponto.disponivel_para_nova_atribuicao()),
            "escalas": escalas,
            "na_fila": licenca.na_fila,
        }

    def get(self, request, pk):
        licenca = self._licenca(pk)
        form = ParecerLicencaForm(licenca=licenca)
        return render(request, self.template_name, self._contexto(licenca, form))

    def post(self, request, pk):
        licenca = self._licenca(pk)
        form = ParecerLicencaForm(request.POST, licenca=licenca)
        if not form.is_valid():
            return render(request, self.template_name, self._contexto(licenca, form))
        try:
            aplicar_parecer(
                licenca,
                request.user,
                form.cleaned_data["acao"],
                motivo=form.cleaned_data.get("motivo", ""),
                categoria=form.cleaned_data.get("categoria_produto"),
                ponto=form.cleaned_data.get("ponto_ocupacao"),
            )
        except ValidationError as erro:
            messages.error(request, erro.messages[0] if erro.messages else str(erro))
            return render(request, self.template_name, self._contexto(licenca, form))

        mensagens = {
            "deferir": "Requerimento deferido e encaminhado para emissão do alvará.",
            "indeferir": "Requerimento indeferido. O motivo foi registrado no dossiê.",
            "pendencia": "Processo devolvido com pendência documental.",
        }
        messages.success(request, mensagens[form.cleaned_data["acao"]])
        if form.cleaned_data["acao"] == "deferir":
            return redirect("gestor_emitir", pk=licenca.pk)
        return redirect("gestor_fila")


class GestorEmitirAlvaraView(PainelGestorMixin, View):
    template_name = "gestor/emitir-alvara.html"
    modulo_permissao = "emissao_alvara"

    def _licenca(self, pk):
        return get_object_or_404(
            LicencaAlvara.objects.select_related(
                "ambulante",
                "categoria_produto",
                "ponto_ocupacao",
                "estrutura_trabalho",
                "gestor_responsavel",
            ),
            pk=pk,
        )

    def _contexto(self, licenca, form):
        ambulante = licenca.ambulante
        return {
            "licenca": licenca,
            "form": form,
            "ambulante": ambulante,
            "estrutura": licenca.estrutura_trabalho
            or ambulante.estruturas.order_by("id").first(),
            "escalas": licenca.escalas.order_by("id"),
            "pode_emitir": licenca.pode_emitir,
        }

    def get(self, request, pk):
        licenca = self._licenca(pk)
        form = EmitirAlvaraForm(licenca=licenca) if licenca.pode_emitir else None
        return render(request, self.template_name, self._contexto(licenca, form))

    def post(self, request, pk):
        licenca = self._licenca(pk)
        form = EmitirAlvaraForm(request.POST, licenca=licenca)
        if not form.is_valid():
            return render(request, self.template_name, self._contexto(licenca, form))
        try:
            licenca = emitir_alvara(
                licenca,
                request.user,
                data_emissao=form.cleaned_data["data_emissao"],
                data_vencimento=form.cleaned_data["data_vencimento"],
                ponto=form.cleaned_data["ponto_ocupacao"],
                dias_semana=form.cleaned_data["dias_semana"],
                horario_inicio=form.cleaned_data["horario_inicio"],
                horario_termino=form.cleaned_data["horario_termino"],
                observacoes=form.cleaned_data.get("observacoes", ""),
            )
        except ValidationError as erro:
            messages.error(request, erro.messages[0] if erro.messages else str(erro))
            return render(request, self.template_name, self._contexto(licenca, form))
        messages.success(
            request,
            f"Alvará {licenca.numero_licenca} emitido. O ponto foi ocupado e o QR Code "
            "já está vinculado ao ambulante.",
        )
        return redirect("gestor_licencas")


class GestorLicencasAtivasView(PainelGestorMixin, TemplateView):
    template_name = "gestor/licencas-ativas.html"
    modulo_permissao = "emissao_alvara"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        marcar_licencas_vencidas()
        status = self.request.GET.get("status", "").strip()
        ponto_id = self.request.GET.get("ponto", "").strip()
        vencimento_proximo = self.request.GET.get("vencimento_proximo") == "1"
        licencas = LicencaAlvara.objects.filter(
            status__in=STATUS_LISTAGEM_GESTOR
        ).select_related("ambulante", "ponto_ocupacao", "categoria_produto")
        if status in STATUS_LISTAGEM_GESTOR:
            licencas = licencas.filter(status=status)
        if ponto_id.isdigit():
            licencas = licencas.filter(ponto_ocupacao_id=int(ponto_id))
        if vencimento_proximo:
            hoje = timezone.localdate()
            licencas = licencas.filter(
                status=StatusLicenca.ATIVO,
                data_vencimento__gte=hoje,
                data_vencimento__lte=hoje + timedelta(days=30),
            )
        context.update(
            {
                "licencas": licencas.order_by("-atualizado_em"),
                "filtro_status": status,
                "filtro_ponto": ponto_id,
                "filtro_vencimento_proximo": vencimento_proximo,
                "status_opcoes": STATUS_LISTAGEM_GESTOR,
                "pontos": PontoOcupacao.objects.filter(ativo=True).order_by(
                    "nome_identificacao"
                ),
            }
        )
        return context


class GestorOcorrenciasView(PainelGestorMixin, TemplateView):
    template_name = "gestor/ocorrencias.html"
    modulo_permissao = "ocorrencias"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = FiltroOcorrenciaForm(self.request.GET)
        busca = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        ocorrencias = filtrar_ocorrencias(q=busca, status=status, tipo=tipo)
        context.update(
            {
                "form": form,
                "ocorrencias": ocorrencias,
                "total_ocorrencias": ocorrencias.count(),
                "filtro_q": busca,
                "filtro_status": status,
                "filtro_tipo": tipo,
                "status_opcoes": StatusOcorrencia.values,
                "tipo_opcoes": TipoOcorrencia.values,
            }
        )
        return context


class GestorOcorrenciaDetalheView(PainelGestorMixin, View):
    template_name = "gestor/ocorrencia-detalhe.html"
    modulo_permissao = "ocorrencias"

    def _ocorrencia(self, pk):
        return get_object_or_404(
            OcorrenciaInspecao.objects.select_related("fiscal", "ambulante"),
            pk=pk,
        )

    def _licenca(self, ocorrencia):
        if ocorrencia.ambulante is None:
            return None
        return (
            ocorrencia.ambulante.licencas.exclude(
                status__in=(StatusLicenca.INDEFERIDO,)
            )
            .order_by("-data_emissao", "-pk")
            .first()
        )

    def _contexto(self, ocorrencia, form):
        return {
            "ocorrencia": ocorrencia,
            "form": form,
            "licenca": self._licenca(ocorrencia),
        }

    def get(self, request, pk):
        ocorrencia = self._ocorrencia(pk)
        form = AuditoriaOcorrenciaForm(
            ocorrencia=ocorrencia,
            initial={"status_ocorrencia": ocorrencia.status_ocorrencia},
        )
        return render(request, self.template_name, self._contexto(ocorrencia, form))

    def post(self, request, pk):
        ocorrencia = self._ocorrencia(pk)
        form = AuditoriaOcorrenciaForm(request.POST, ocorrencia=ocorrencia)
        if not form.is_valid():
            return render(request, self.template_name, self._contexto(ocorrencia, form))
        try:
            ocorrencia, efeito = auditar_ocorrencia(
                ocorrencia,
                form.cleaned_data["status_ocorrencia"],
                form.cleaned_data.get("acao_licenca") or "",
            )
        except ValueError as erro:
            messages.error(request, str(erro))
            return render(request, self.template_name, self._contexto(ocorrencia, form))
        mensagem = f"Ocorrência #{ocorrencia.pk} atualizada para {ocorrencia.status_ocorrencia}."
        if efeito == "suspenso":
            mensagem = (
                f"Ocorrência #{ocorrencia.pk} marcada como {ocorrencia.status_ocorrencia}. "
                "A licença do ambulante passou a Suspenso."
            )
        elif efeito == "cancelado":
            mensagem = (
                f"Ocorrência #{ocorrencia.pk} atualizada. "
                "A licença do ambulante foi cancelada."
            )
        messages.success(request, mensagem)
        return redirect("gestor_ocorrencia_detalhe", pk=ocorrencia.pk)


def contexto_inicio_gestor(user):
    return {
        "fila_analise": LicencaAlvara.objects.filter(status__in=STATUS_FILA).count(),
        "total_ambulantes": Ambulante.objects.count(),
        "docs_pendentes": DocumentoAnexo.objects.filter(
            status_aprovacao=StatusAprovacaoDocumento.PENDENTE
        ).count(),
        "licencas_aprovadas": LicencaAlvara.objects.filter(
            status=StatusSolicitacao.APROVADO
        ).count(),
        "eh_gestor": Gestor.objects.filter(pk=user.pk).exists(),
    }


class GestorDossieExportPDFView(PainelGestorMixin, View):
    modulo_permissao = "solicitacao_licenca"

    def get(self, request, pk):
        ambulante = get_object_or_404(
            Ambulante.objects.select_related("ponto_pretendido").prefetch_related(
                "licencas", "estruturas", "ocorrencias_recebidas"
            ),
            pk=pk,
        )

        LogAcessoDossie.objects.create(usuario=request.user, ambulante=ambulante)

        html_string = render_to_string(
            "gestor/dossie_export.html", {"ambulante": ambulante}
        )
        buffer = BytesIO()
        pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), buffer)
        pdf_file = buffer.getvalue()

        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="dossie_{ambulante.cpf}.pdf"'
        )
        return response
