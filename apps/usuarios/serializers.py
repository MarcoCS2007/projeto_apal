from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from django.db import transaction

from .models import UsuarioBase, Ambulante


class LoginSerializer(TokenObtainPairSerializer):
    """Gera o par de tokens JWT com o claim customizado de perfil (role)."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.ativo:
            raise AuthenticationFailed(
                "Usuário inativo. Entre em contato com a administração."
            )

        data["role"] = self.user.role
        return data


class UsuarioMeSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = UsuarioBase
        fields = ("id", "cpf", "nome", "sobrenome", "email", "role")
        read_only_fields = fields


class RegisterAmbulanteSerializer(serializers.ModelSerializer):
    # Campo vindo do front-end para Nome Completo
    nome_completo = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    # Torna os campos da Etapa 2 opcionais na criação inicial da conta
    tipo_atuacao = serializers.CharField(required=False, allow_blank=True, default="Pendente")
    data_nasc = serializers.DateField(required=False, allow_null=True, default=None)
    escolaridade = serializers.CharField(required=False, allow_blank=True, default="Não informada")

    class Meta:
        model = Ambulante
        fields = [
            "nome_completo",
            "cpf",
            "email",
            "telefone_whatsapp",
            "password",
            "foto",
            "tipo_atuacao",
            "data_nasc",
            "escolaridade",
            "codigo_qr_code",
            "pontuacao",
        ]
        read_only_fields = ("codigo_qr_code", "pontuacao")

    def create(self, validated_data):
        # 1. Separa o nome completo em nome e sobrenome
        nome_completo = validated_data.pop("nome_completo", "").strip().split(" ", 1)
        nome = nome_completo[0]
        sobrenome = nome_completo[1] if len(nome_completo) > 1 else ""

        password = validated_data.pop("password")
        codigo_qr_code = str(uuid.uuid4())

        # 2. Criação atômica no banco de dados (Atende ao Critério de Aceite 2)
        with transaction.atomic():
            ambulante = Ambulante(
                nome=nome,
                sobrenome=sobrenome,
                codigo_qr_code=codigo_qr_code,
                **validated_data
            )
            ambulante.set_password(password)
            ambulante.save()

            return ambulante