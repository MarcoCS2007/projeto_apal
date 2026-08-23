from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsFiscal
from apps.fiscalizacao.forms import OcorrenciaForm
from apps.fiscalizacao.services import (
    consultar_campo,
    inspecionar_qr,
    registrar_ocorrencia,
)
from apps.licenciamento.api import serializar_licenca


def serializar_ambulante_campo(ambulante):
    if ambulante is None:
        return None
    return {
        "id": ambulante.pk,
        "nome_completo": ambulante.nome_completo,
        "cpf": ambulante.cpf,
        "cpf_mascarado": ambulante.cpf_mascarado,
    }


def serializar_inspecao(resultado):
    return {
        "valido": resultado.valido,
        "motivo": resultado.motivo,
        "mensagem": resultado.mensagem,
        "fora_horario": resultado.fora_horario,
        "tipo_sugerido": resultado.tipo_sugerido,
        "ambulante": serializar_ambulante_campo(resultado.ambulante),
        "licenca": serializar_licenca(resultado.licenca),
        "candidatos": [
            serializar_ambulante_campo(item) for item in resultado.candidatos
        ],
    }


def serializar_ocorrencia(ocorrencia):
    return {
        "id": ocorrencia.pk,
        "tipo_ocorrencia": ocorrencia.tipo_ocorrencia,
        "descricao": ocorrencia.descricao,
        "local_ocorrencia": ocorrencia.local_ocorrencia,
        "status_ocorrencia": ocorrencia.status_ocorrencia,
        "tem_evidencia": bool(ocorrencia.evidencia_foto),
        "ambulante": serializar_ambulante_campo(ocorrencia.ambulante),
        "criado_em": ocorrencia.criado_em,
    }


class BuscaFiscalAPIView(APIView):
    permission_classes = (IsFiscal,)

    def get(self, request):
        termo = (request.query_params.get("q") or "").strip()
        if not termo:
            return Response(
                {
                    "detail": "Informe q com CPF, nome, número do alvará ou o código do QR."
                },
                status=400,
            )
        return Response(serializar_inspecao(consultar_campo(termo)))


class QrFiscalAPIView(APIView):
    permission_classes = (IsFiscal,)

    def get(self, request):
        codigo = (
            request.query_params.get("codigo") or request.query_params.get("qr") or ""
        ).strip()
        if not codigo:
            return Response({"detail": "Informe o código do QR em codigo."}, status=400)
        return Response(serializar_inspecao(inspecionar_qr(codigo)))


class OcorrenciaFiscalAPIView(APIView):
    permission_classes = (IsFiscal,)

    def post(self, request):
        form = OcorrenciaForm(data=request.data, files=request.FILES)
        if not form.is_valid():
            return Response(
                {
                    "detail": "Há erros no registro da ocorrência.",
                    "erros": {
                        campo: [str(erro) for erro in erros]
                        for campo, erros in form.errors.items()
                    },
                },
                status=400,
            )
        ocorrencia = registrar_ocorrencia(
            request.user,
            form.cleaned_data.get("ambulante"),
            form.cleaned_data["tipo_ocorrencia"],
            form.cleaned_data["descricao"],
            local_ocorrencia=form.cleaned_data.get("local_ocorrencia") or "",
            evidencia_foto=form.cleaned_data.get("evidencia_foto"),
        )
        return Response(serializar_ocorrencia(ocorrencia), status=201)
