from rest_framework.permissions import BasePermission

from apps.usuarios.models import Perfil


class TemPerfil(BasePermission):
    perfis_permitidos = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in self.perfis_permitidos
        )


class IsAmbulante(TemPerfil):
    perfis_permitidos = (Perfil.AMBULANTE,)


class IsFiscal(TemPerfil):
    perfis_permitidos = (Perfil.FISCAL,)


class IsGestor(TemPerfil):
    perfis_permitidos = (Perfil.GESTOR,)


class IsAdministrador(TemPerfil):
    perfis_permitidos = (Perfil.ADMINISTRADOR,)
