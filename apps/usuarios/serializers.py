from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UsuarioBase


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
