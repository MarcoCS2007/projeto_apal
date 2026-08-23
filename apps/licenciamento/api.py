from datetime import date

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAmbulante
from apps.core.qr_imagem import renderizar_qr_png
from apps.core.qrcode import validar_codigo_qr
from apps.licenciamento.models import TipoDocumento
from apps.licenciamento.services import (
    categoria_do_ambulante,
    licenca_ativa,
    licenca_atual,
    licencas_do_ambulante,
    registrar_documento,
    tipos_faltando_aprovacao,
    tipos_faltando_envio,
)
from apps.usuarios.api import ambulante_autenticado


def serializar_licenca(licenca):
    if licenca is None:
        return None
    ponto = licenca.ponto_ocupacao
    categoria = licenca.categoria_produto
    return {
        "id": licenca.pk,
        "protocolo": licenca.protocolo,
        "numero_licenca": licenca.numero_licenca,
        "status": licenca.status,
        "data_emissao": licenca.data_emissao,
        "data_vencimento": licenca.data_vencimento,
        "taxa_paga": licenca.taxa_paga,
        "aguardando_taxa": licenca.aguardando_taxa,
        "qr_valido": licenca.qr_valido,
        "horario_autorizado": licenca.texto_horario_autorizado,
        "ponto": ponto.nome_identificacao if ponto else None,
        "bairro": ponto.bairro if ponto else None,
        "categoria": categoria.nome_categoria if categoria else None,
        "motivo_parecer": licenca.motivo_parecer or "",
    }


def serializar_documento(documento):
    return {
        "id": documento.pk,
        "tipo": documento.tipo_documento,
        "tipo_label": documento.get_tipo_documento_display(),
        "status": documento.status_aprovacao,
        "motivo_rejeicao": documento.motivo_rejeicao or "",
        "data_validade": documento.data_validade,
        "data_upload": documento.data_upload,
        "tem_arquivo": bool(documento.arquivo),
    }


class DocumentosAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        categoria = categoria_do_ambulante(ambulante)
        documentos = ambulante.documentos.order_by("tipo_documento")
        return Response(
            {
                "documentos": [serializar_documento(item) for item in documentos],
                "faltando_envio": list(tipos_faltando_envio(ambulante, categoria)),
                "faltando_aprovacao": list(
                    tipos_faltando_aprovacao(ambulante, categoria)
                ),
            }
        )

    def post(self, request):
        ambulante = ambulante_autenticado(request.user)
        tipo = (request.data.get("tipo_documento") or "").strip()
        arquivo = request.FILES.get("arquivo")
        if tipo not in TipoDocumento.values:
            return Response(
                {
                    "detail": "Tipo de documento inválido.",
                    "tipos": list(TipoDocumento.values),
                },
                status=400,
            )
        if arquivo is None:
            return Response({"detail": "Envie o arquivo no campo arquivo."}, status=400)
        validade = request.data.get("data_validade") or None
        if isinstance(validade, str) and validade:
            try:
                validade = date.fromisoformat(validade)
            except ValueError:
                return Response(
                    {"detail": "data_validade deve estar no formato AAAA-MM-DD."},
                    status=400,
                )
        documento = registrar_documento(
            ambulante, tipo, arquivo, data_validade=validade
        )
        return Response(serializar_documento(documento), status=201)


class SolicitacaoAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        historico = list(licencas_do_ambulante(ambulante))
        atual = historico[0] if historico else None
        return Response(
            {
                "licenca": serializar_licenca(atual),
                "historico": [serializar_licenca(item) for item in historico],
            }
        )


class CredencialAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        ativa = licenca_ativa(ambulante)
        qr_liberado = bool(
            ativa
            and ativa.qr_valido
            and ambulante.codigo_qr_code
            and validar_codigo_qr(ambulante.codigo_qr_code) is not None
        )
        return Response(
            {
                "qr_liberado": qr_liberado,
                "codigo_qr": ambulante.codigo_qr_code if qr_liberado else None,
                "qr_png": "/api/ambulante/credencial/qr.png" if qr_liberado else None,
                "licenca": serializar_licenca(
                    ativa if qr_liberado else licenca_atual(ambulante)
                ),
            }
        )


class CredencialQrPngAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        licenca = licenca_ativa(ambulante)
        codigo = ambulante.codigo_qr_code
        if (
            licenca is None
            or not licenca.qr_valido
            or not codigo
            or validar_codigo_qr(codigo) is None
        ):
            return Response(
                {"detail": "Não há QR Code válido para esta credencial."},
                status=404,
            )
        png = renderizar_qr_png(codigo)
        response = HttpResponse(png, content_type="image/png")
        nome = f"credencial-{licenca.numero_licenca or licenca.pk}.png"
        if request.GET.get("download"):
            response["Content-Disposition"] = f'attachment; filename="{nome}"'
        else:
            response["Content-Disposition"] = "inline"
        return response
