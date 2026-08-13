from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings


class JWTAuthenticationComPerfil(JWTAuthentication):
    """Carrega o usuário do JWT já com o perfil (MTI) para evitar consultas extras."""

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as exc:
            raise InvalidToken(
                "Token não contém identificação de usuário reconhecível."
            ) from exc

        try:
            user = self.user_model.objects.select_related(
                "ambulante",
                "fiscal",
                "gestor",
                "administrador",
            ).get(**{api_settings.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist as exc:
            raise AuthenticationFailed(
                "Usuário não encontrado.", code="user_not_found"
            ) from exc

        if not user.is_active or not user.ativo:
            raise AuthenticationFailed(
                "Usuário inativo ou não autorizado.", code="user_not_found"
            )

        return user
