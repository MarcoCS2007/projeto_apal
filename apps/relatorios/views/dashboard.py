import json

from django.views.generic import TemplateView

from apps.relatorios import services
from apps.relatorios.filters import filtrar_ambulantes, filtros_do_request
from apps.usuarios.views_gestor import PainelGestorMixin


def _format_chart_js(labels, data, label="Dataset"):
    return {
        "labels": labels,
        "datasets": [
            {
                "label": label,
                "data": data,
                "backgroundColor": [
                    "rgba(54, 162, 235, 0.6)",
                    "rgba(255, 99, 132, 0.6)",
                    "rgba(255, 206, 86, 0.6)",
                    "rgba(75, 192, 192, 0.6)",
                    "rgba(153, 102, 255, 0.6)",
                    "rgba(255, 159, 64, 0.6)",
                ],
                "borderWidth": 1,
            }
        ],
    }


class DashboardInteligenciaView(PainelGestorMixin, TemplateView):
    """
    Renderiza a base HTML onde o Vue ou Vanilla JS com Chart.js será montado.
    """

    template_name = "relatorios/dashboard_inteligencia.html"
    modulo_permissao = "relatorios"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filtros = filtros_do_request(self.request)
        qs = filtrar_ambulantes(**filtros)

        from apps.espacos.models import PontoOcupacao

        bairros = (
            PontoOcupacao.objects.exclude(bairro__isnull=True)
            .exclude(bairro="")
            .values_list("bairro", flat=True)
            .distinct()
            .order_by("bairro")
        )
        context["bairros_disponiveis"] = list(bairros)

        # A. Dados Únicos
        dist_etaria = services.get_distribuicao_etaria(qs)
        dist_genero = services.get_distribuicao_genero(qs)
        instrucao = services.get_grau_instrucao(qs)
        vulnerabilidade = services.get_vulnerabilidade_social(qs)
        renda = services.get_estimativa_renda(qs)

        # B. Cruzamentos
        evolucao = services.get_evolucao_regularizacao(qs)

        # Formatação para Chart.js
        chart_etaria = _format_chart_js(
            labels=[item["faixa"] for item in dist_etaria],
            data=[item["total"] for item in dist_etaria],
            label="Ambulantes por Idade",
        )

        chart_genero = _format_chart_js(
            labels=[item["genero"] for item in dist_genero],
            data=[item["total"] for item in dist_genero],
            label="Distribuição de Gênero",
        )

        chart_instrucao = _format_chart_js(
            labels=[item["escolaridade"] for item in instrucao],
            data=[item["total"] for item in instrucao],
            label="Grau de Instrução",
        )

        chart_vulnerabilidade = _format_chart_js(
            labels=["Com NIS", "Sem NIS"],
            data=[vulnerabilidade["com_nis"], vulnerabilidade["sem_nis"]],
            label="Vulnerabilidade Social",
        )

        labels_evolucao = [item["periodo"] for item in evolucao]
        dataset_fixo = [item["fixo"] for item in evolucao]
        dataset_movel = [item["movel"] for item in evolucao]

        chart_evolucao = {
            "labels": labels_evolucao,
            "datasets": [
                {
                    "label": "Fixo",
                    "data": dataset_fixo,
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "fill": False,
                },
                {
                    "label": "Móvel",
                    "data": dataset_movel,
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "fill": False,
                },
            ],
        }

        chart_renda = _format_chart_js(
            labels=[item["categoria"] for item in renda],
            data=[item["renda_media"] for item in renda],
            label="Renda Média por Categoria (R$)",
        )

        from django.core.serializers.json import DjangoJSONEncoder

        context["chart_etaria_json"] = json.dumps(chart_etaria, cls=DjangoJSONEncoder)
        context["chart_genero_json"] = json.dumps(chart_genero, cls=DjangoJSONEncoder)
        context["chart_instrucao_json"] = json.dumps(
            chart_instrucao, cls=DjangoJSONEncoder
        )
        context["chart_vulnerabilidade_json"] = json.dumps(
            chart_vulnerabilidade, cls=DjangoJSONEncoder
        )
        context["chart_renda_json"] = json.dumps(chart_renda, cls=DjangoJSONEncoder)
        context["chart_evolucao_json"] = json.dumps(
            chart_evolucao, cls=DjangoJSONEncoder
        )

        # Filtros atuais para manter no form e botao de exportar
        context["bairro_atual"] = self.request.GET.get("bairro", "")
        context["origem_atual"] = self.request.GET.get("origem", "")
        context["query_string"] = self.request.GET.urlencode()

        return context
