import hashlib
import hmac

from django.conf import settings


def _chave_secreta():
    return (settings.SECRET_KEY or "apal-dev-qr").encode()


def gerar_codigo_qr(licenca):
    """Hash HMAC estável por licença (pk + número oficial)."""
    mensagem = f"apal:licenca:{licenca.pk}:{licenca.numero_licenca or ''}"
    return hmac.new(_chave_secreta(), mensagem.encode(), hashlib.sha256).hexdigest()


def validar_codigo_qr(codigo):
    """Retorna a licença Ativa correspondente, ou None se inválido/vencido/suspenso."""
    from apps.licenciamento.models import StatusLicenca
    from apps.licenciamento.services import marcar_licencas_vencidas
    from apps.usuarios.models import Ambulante

    codigo = (codigo or "").strip()
    if not codigo:
        return None

    marcar_licencas_vencidas()
    ambulante = Ambulante.objects.filter(codigo_qr_code=codigo).first()
    if ambulante is None:
        return None

    licenca = (
        ambulante.licencas.filter(status=StatusLicenca.ATIVO)
        .order_by("-data_emissao", "-pk")
        .first()
    )
    if licenca is None:
        return None
    if not hmac.compare_digest(gerar_codigo_qr(licenca), codigo):
        return None
    if not licenca.qr_valido:
        return None
    return licenca
