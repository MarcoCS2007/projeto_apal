from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistente.forms import PerguntaAssistenteForm
from apps.assistente.models import LogAssistente
from apps.assistente.services import SUGESTOES_ASSISTENTE, responder_pergunta
from apps.core.permissions import IsAmbulante
from apps.usuarios.api import ambulante_autenticado


def serializar_log(log):
    return {
        "id": log.pk,
        "pergunta": log.pergunta,
        "resposta": log.resposta,
        "fonte": log.fonte,
        "criado_em": log.criado_em,
    }


class AssistenteAmbulanteAPIView(APIView):
    permission_classes = (IsAmbulante,)

    def get(self, request):
        ambulante = ambulante_autenticado(request.user)
        historico = list(
            LogAssistente.objects.filter(ambulante=ambulante).order_by("-criado_em")[
                :20
            ]
        )
        historico.reverse()
        return Response(
            {
                "sugestoes": list(SUGESTOES_ASSISTENTE),
                "historico": [serializar_log(item) for item in historico],
            }
        )

    def post(self, request):
        ambulante = ambulante_autenticado(request.user)
        form = PerguntaAssistenteForm(data=request.data)
        if not form.is_valid():
            return Response(
                {
                    "detail": "Digite uma pergunta.",
                    "erros": {
                        campo: [str(erro) for erro in erros]
                        for campo, erros in form.errors.items()
                    },
                },
                status=400,
            )
        try:
            log = responder_pergunta(ambulante, form.cleaned_data["pergunta"])
        except ValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=400)
        return Response(serializar_log(log), status=201)
