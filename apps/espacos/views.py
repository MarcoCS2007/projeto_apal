from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.licenciamento.models import LicencaAlvara, StatusLicenca
from apps.usuarios.models import Ambulante
from apps.usuarios.permissoes import RequerModuloMixin
from apps.usuarios.views import AcessoBackofficeMixin

from .forms import PontoOcupacaoForm
from .models import PontoOcupacao


def _parse_coordenadas(raw):
    texto = (raw or "").strip()
    partes = [p.strip() for p in texto.replace(";", ",").split(",") if p.strip()]
    if len(partes) < 2:
        return None
    try:
        return float(partes[0]), float(partes[1])
    except ValueError:
        return None


def _ambulantes_filtrados_origem(origem):
    qs = Ambulante.objects.filter(ativo=True, is_active=True)
    if origem == "fixo":
        return qs.filter(tipo_atuacao="fixo")
    if origem == "movel":
        return qs.filter(tipo_atuacao="movel")
    return qs


def _ids_ambulantes_ponto(ponto, situacao, ambulantes_qs):
    ids = set(ambulantes_qs.values_list("pk", flat=True))
    if not ids:
        return set(), set()

    ativos = set(
        LicencaAlvara.objects.filter(
            ponto_ocupacao=ponto,
            status=StatusLicenca.ATIVO,
            ambulante_id__in=ids,
        ).values_list("ambulante_id", flat=True)
    )
    pretendidos = set(
        Ambulante.objects.filter(
            pk__in=ids,
            ponto_pretendido=ponto,
        ).values_list("pk", flat=True)
    )
    sem_licenca = pretendidos - ativos

    if situacao == "ativos":
        return ativos, set()
    if situacao == "sem_licenca":
        return set(), sem_licenca
    return ativos, sem_licenca


def _serializar_ambulantes_ponto(ativos_ids, sem_licenca_ids):
    ids = ativos_ids | sem_licenca_ids
    if not ids:
        return []
    por_id = {
        a.pk: a
        for a in Ambulante.objects.filter(pk__in=ids).only(
            "pk",
            "nome",
            "sobrenome",
            "apelido_nome_fantasia",
            "tipo_atuacao",
        )
    }
    itens = []
    for pk in ids:
        amb = por_id.get(pk)
        if amb is None:
            continue
        situacao = "ativo" if pk in ativos_ids else "sem_licenca"
        itens.append(
            {
                "id": amb.pk,
                "nome": amb.nome_completo,
                "apelido": amb.apelido_nome_fantasia or "",
                "tipo_atuacao": amb.tipo_atuacao or "",
                "situacao": situacao,
                "situacao_label": (
                    "Licença ativa" if situacao == "ativo" else "Sem licença"
                ),
                "dossie_url": reverse("gestor_dossie", kwargs={"pk": amb.pk}),
            }
        )
    itens.sort(key=lambda item: (item["nome"] or "").lower())
    return itens


def pontos_para_mapa_cidade(bairro="", situacao="todos", origem=""):
    situacao = situacao or "todos"
    if situacao not in ("todos", "ativos", "sem_licenca"):
        situacao = "todos"

    pontos_qs = PontoOcupacao.objects.filter(ativo=True).order_by(
        "bairro", "nome_identificacao"
    )
    if bairro:
        pontos_qs = pontos_qs.filter(bairro__iexact=bairro)

    ambulantes_qs = _ambulantes_filtrados_origem(origem)
    itens = []
    volumes = []
    for ponto in pontos_qs:
        coords = _parse_coordenadas(ponto.coordenadas)
        ativos_ids, sem_ids = _ids_ambulantes_ponto(ponto, situacao, ambulantes_qs)
        ambulantes = _serializar_ambulantes_ponto(ativos_ids, sem_ids)
        volume = len(ambulantes)
        volumes.append(volume)
        itens.append(
            {
                "id": ponto.pk,
                "nome": ponto.nome_identificacao,
                "bairro": ponto.bairro or "",
                "logradouro": ponto.logradouro or "",
                "status_ocupacao": ponto.status_ocupacao or "",
                "lat": coords[0] if coords else None,
                "lng": coords[1] if coords else None,
                "volume": volume,
                "ambulantes": ambulantes,
            }
        )

    volume_max = max(volumes) if volumes else 0
    return {
        "pontos": itens,
        "volume_max": volume_max,
        "total_ambulantes": sum(volumes),
        "pontos_visiveis": len(itens),
        "filtros": {
            "bairro": bairro or "",
            "situacao": situacao,
            "origem": origem or "",
        },
    }


class GestorPontosView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    template_name = "gestor/gerenciar-pontos.html"
    modulo_permissao = "mapa_vagas"

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


class GestorPontoExcluirView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    http_method_names = ("post", "options")
    modulo_permissao = "mapa_vagas"

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


class GestorMapaCidadeView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, TemplateView
):
    template_name = "gestor/mapa-cidade.html"
    modulo_permissao = "mapa_vagas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bairros = (
            PontoOcupacao.objects.filter(ativo=True)
            .exclude(Q(bairro__isnull=True) | Q(bairro=""))
            .values_list("bairro", flat=True)
            .distinct()
            .order_by("bairro")
        )
        context["bairros_disponiveis"] = list(bairros)
        context["mapa_dados_url"] = reverse("gestor_mapa_cidade_json")
        return context


class GestorMapaCidadeJsonView(
    LoginRequiredMixin, AcessoBackofficeMixin, RequerModuloMixin, View
):
    modulo_permissao = "mapa_vagas"

    def get(self, request):
        dados = pontos_para_mapa_cidade(
            bairro=(request.GET.get("bairro") or "").strip(),
            situacao=(request.GET.get("situacao") or "todos").strip(),
            origem=(request.GET.get("origem") or "").strip(),
        )
        return JsonResponse(dados)
