"""Aplica a matriz de módulos × perfil em menus, views e recortes de secretaria."""

from __future__ import annotations

import unicodedata

from django.core.exceptions import PermissionDenied

from apps.usuarios.seguranca import MODULOS_PERMISSAO


def _perfil_do_usuario(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return "cidadao"
    role = getattr(user, "role", None)
    if role is None:
        return "cidadao"
    return role.value if hasattr(role, "value") else str(role)


def usuario_pode(user, modulo, config=None):
    """True se o perfil do usuário tem o módulo na matriz (Master sempre pode)."""
    from apps.usuarios.models import ConfiguracaoSeguranca, Perfil

    perfil = _perfil_do_usuario(user)
    if perfil == Perfil.ADMINISTRADOR.value:
        return True
    if config is None:
        config = ConfiguracaoSeguranca.carregar()
    return config.perfil_pode(perfil, modulo)


def gestor_recorte_sanitario(user):
    """Gestor da Vigilância Sanitária só trata laudo sanitário na triagem."""
    from apps.usuarios.models import Gestor, Perfil

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) == Perfil.ADMINISTRADOR:
        return False
    gestor = Gestor.objects.filter(pk=getattr(user, "pk", None)).first()
    if gestor is None:
        return False
    texto = unicodedata.normalize("NFD", (gestor.departamento or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return "vigilancia sanitaria" in texto


class PodeModulos:
    def __init__(self, mapping):
        self._mapping = mapping

    def __getattr__(self, modulo):
        if modulo.startswith("_"):
            raise AttributeError(modulo)
        return bool(self._mapping.get(modulo, False))

    def __contains__(self, modulo):
        return bool(self._mapping.get(modulo, False))


def permissoes_context(request):
    from apps.usuarios.models import ConfiguracaoSeguranca

    user = getattr(request, "user", None)
    config = ConfiguracaoSeguranca.carregar()
    mapping = {
        modulo: usuario_pode(user, modulo, config)
        for modulo, _rotulo in MODULOS_PERMISSAO
    }
    return {
        "pode": PodeModulos(mapping),
        "recorte_sanitario": gestor_recorte_sanitario(user),
    }


class RequerModuloMixin:
    """Bloqueia a view se a matriz não liberar `modulo_permissao` para o perfil."""

    modulo_permissao = None

    def dispatch(self, request, *args, **kwargs):
        modulo = self.modulo_permissao
        if modulo and not usuario_pode(request.user, modulo):
            raise PermissionDenied("Módulo não liberado para o seu perfil.")
        return super().dispatch(request, *args, **kwargs)


def pode_ver_documento(user, documento):
    from apps.licenciamento.models import TipoDocumento
    from apps.usuarios.models import Perfil

    if user is None or not user.is_authenticated:
        return False
    role = user.role
    if role == Perfil.ADMINISTRADOR:
        return True
    if role == Perfil.AMBULANTE:
        return documento.ambulante_id == user.pk
    if role in (Perfil.GESTOR, Perfil.FISCAL):
        recorte = (
            role == Perfil.GESTOR
            and gestor_recorte_sanitario(user)
            and documento.tipo_documento != TipoDocumento.LAUDO_SANITARIO
        )
        return not recorte
    return False
