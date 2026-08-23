from django.core.exceptions import ValidationError

from apps.core.ia import consultar_conhecimento

from .models import LogAssistente

SUGESTOES_ASSISTENTE = (
    "quais documentos preciso para alimentos?",
    "quais os prazos de renovação?",
    "onde é proibido posicionar o carrinho?",
    "como funciona a credencial com QR Code?",
)


def responder_pergunta(ambulante, pergunta):
    """Gera resposta da base local e grava LogAssistente."""
    texto = (pergunta or "").strip()
    if not texto:
        raise ValidationError("Digite uma pergunta.")

    resultado = consultar_conhecimento(texto)
    return LogAssistente.objects.create(
        ambulante=ambulante,
        pergunta=texto,
        resposta=resultado.texto,
        fonte=resultado.fonte,
    )
