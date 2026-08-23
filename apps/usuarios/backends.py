from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CPFOuEmailBackend(ModelBackend):
    """Autentica o backoffice com CPF (USERNAME_FIELD) ou e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identificador = (username or kwargs.get(User.USERNAME_FIELD) or "").strip()
        if not identificador or password is None:
            return None

        try:
            user = self._buscar_usuario(User, identificador)
        except User.DoesNotExist:
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _buscar_usuario(self, User, identificador):
        if "@" in identificador:
            return User.objects.get(email__iexact=identificador)
        cpf = "".join(ch for ch in identificador if ch.isdigit()) or identificador
        return User.objects.get(cpf=cpf)
