import csv

from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from apps.relatorios.filters import filtrar_ambulantes, filtros_do_request
from apps.usuarios.views_gestor import PainelGestorMixin


class ExportacaoRelatorioView(PainelGestorMixin, View):
    modulo_permissao = "relatorios"

    def get(self, request, *args, **kwargs):
        filtros = filtros_do_request(request)
        qs = filtrar_ambulantes(**filtros).prefetch_related("enderecos")

        response = HttpResponse(
            content_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="relatorio_ambulantes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            },
        )
        # Adicionar o BOM (Byte Order Mark) para o Excel em português entender a acentuação
        response.write("\ufeff".encode("utf8"))

        # Usar ponto e vírgula como delimitador (padrão brasileiro)
        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "Nome",
                "CPF",
                "Telefone",
                "Bairro",
                "Gênero",
                "Escolaridade",
                "Tem NIS",
                "Pontuação",
            ]
        )

        from apps.relatorios.filters import _grupo_escolaridade

        for amb in qs:
            bairro = (
                amb.enderecos.first().bairro
                if amb.enderecos.first()
                else "Não informado"
            )
            tem_nis = "Sim" if amb.nis else "Não"
            writer.writerow(
                [
                    amb.nome_completo,
                    amb.cpf,
                    amb.telefone_whatsapp,
                    bairro,
                    (
                        amb.get_genero_display()
                        if hasattr(amb, "get_genero_display")
                        else (amb.genero or "Não informado")
                    ),
                    _grupo_escolaridade(amb.escolaridade),
                    tem_nis,
                    amb.pontuacao,
                ]
            )

        return response
