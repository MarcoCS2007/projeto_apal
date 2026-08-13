from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAmbulante
from apps.licenciamento.services import abrir_requerimento
from apps.usuarios.models import Ambulante
from apps.usuarios.score import resumo_score
from apps.usuarios.views import ETAPAS_CADASTRO


def ambulante_autenticado(user):
    return Ambulante.objects.filter(pk=user.pk).first()


def _erros(form):
    return {
        campo: [str(erro) for erro in erros] for campo, erros in form.errors.items()
    }


def snapshot_cadastro(ambulante):
    extras = ambulante.dados_complementares or {}
    endereco = ambulante.enderecos.order_by("id").first()
    estrutura = ambulante.estruturas.order_by("id").first()
    return {
        "cadastro_completo": ambulante.cadastro_completo,
        "situacao_conta": ambulante.situacao_conta,
        "cpf": ambulante.cpf,
        "email": ambulante.email,
        "nome_completo": ambulante.nome_completo,
        "data_nasc": ambulante.data_nasc,
        "telefone_whatsapp": ambulante.telefone_whatsapp,
        "telefone_2": ambulante.telefone_2 or "",
        "nis": ambulante.nis or "",
        "escolaridade": ambulante.escolaridade,
        "num_funcionarios": ambulante.num_funcionarios,
        "tipo_atuacao": ambulante.tipo_atuacao,
        "cnpj": ambulante.cnpj or "",
        "apelido_nome_fantasia": ambulante.apelido_nome_fantasia or "",
        "rg": extras.get("rg", ""),
        "ponto_pretendido_id": ambulante.ponto_pretendido_id,
        "categoria_pretendida_id": extras.get("categoria_id"),
        "endereco": (
            {
                "cep": endereco.cep,
                "logradouro": endereco.logradouro,
                "numero": endereco.numero,
                "complemento": endereco.complemento or "",
                "bairro": endereco.bairro,
                "cidade": endereco.cidade,
                "estado_uf": endereco.estado_uf,
            }
            if endereco
            else None
        ),
        "estrutura": (
            {
                "tipo_estrutura": estrutura.tipo_estrutura,
                "dimensoes_metragem": str(estrutura.dimensoes_metragem),
                "descricao": estrutura.descricao,
            }
            if estrutura
            else None
        ),
    }


def serializar_score(ambulante):
    resumo = resumo_score(ambulante)
    faixa = resumo["faixa"]
    return {
        "pontuacao": resumo["pontuacao"],
        "maximo": resumo["maximo"],
        "faixa": {
            "nome": faixa["nome"],
            "descricao": faixa["descricao"],
            "pontos": faixa["pontos"],
            "proxima": faixa["proxima"],
            "faltam": faixa["faltam"],
            "percentual": faixa["percentual"],
        },
        "eventos": [
            {
                "tipo": evento.tipo,
                "pontos": evento.pontos,
                "saldo_apos": evento.saldo_apos,
                "descricao": evento.descricao,
                "criado_em": evento.criado_em,
            }
            for evento in resumo["eventos"]
        ],
        "dicas": resumo["dicas"],
        "regras": resumo["regras"],
    }


class CadastroAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        return Response(snapshot_cadastro(ambulante))

    def patch(self, request):
        ambulante = ambulante_autenticado(request.user)
        try:
            etapa = int(request.data.get("etapa") or 1)
        except (TypeError, ValueError):
            etapa = 0
        if etapa not in ETAPAS_CADASTRO:
            return Response({"detail": "Etapa inválida. Use 1 a 6."}, status=400)

        form_kwargs = {"ambulante": ambulante}
        if etapa == 6:
            form_kwargs["acao"] = request.data.get("acao") or "salvar"
        form = ETAPAS_CADASTRO[etapa](request.data, request.FILES, **form_kwargs)
        if not form.is_valid():
            return Response(
                {
                    "detail": "Há erros no cadastro.",
                    "erros": _erros(form),
                },
                status=400,
            )
        form.save()
        ambulante.refresh_from_db()
        return Response(snapshot_cadastro(ambulante))

    def post(self, request):
        ambulante = ambulante_autenticado(request.user)
        if (request.data.get("acao") or "") != "enviar":
            return self.patch(request)
        if not ambulante.cadastro_completo:
            return Response(
                {
                    "detail": (
                        "Ainda faltam dados obrigatórios (pessoais, endereço, "
                        "atuação e estrutura) para concluir o cadastro."
                    )
                },
                status=400,
            )
        licenca, _criada = abrir_requerimento(ambulante)
        return Response(
            {
                "detail": "Cadastro concluído. Acompanhe a solicitação pelo protocolo.",
                "protocolo": licenca.protocolo,
                "status": licenca.status,
            }
        )


class ScoreAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        return Response(serializar_score(ambulante_autenticado(request.user)))
