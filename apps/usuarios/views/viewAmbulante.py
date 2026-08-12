from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers.ambulanteSerializers import RegisterAmbulante
from rest_framework.permissions import AllowAny


class RegisterAmbulanteView(APIView):
    # (Critério 1) Rota pública acessível sem restrição (AllowAny)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterAmbulante(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"mensagem": "Ambulante cadastrado com sucesso!"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)