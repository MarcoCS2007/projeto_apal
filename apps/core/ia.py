"""Consulta educativa local (RAG) para o assistente do ambulante.

A base é o FAQ institucional e as regras de documentos/prazos/zona.
Não depende de API externa: testes e o ambiente de hackathon funcionam offline.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_STOPWORDS = frozenset(
    {
        "a",
        "ao",
        "aos",
        "as",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "eu",
        "me",
        "meu",
        "minha",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "pra",
        "preciso",
        "qual",
        "quais",
        "que",
        "se",
        "um",
        "uma",
    }
)

_FALLBACK = (
    "Não encontrei essa dúvida na base do APAL. Pergunte sobre documentos "
    "exigidos (inclusive para alimentos), prazos de renovação, zona permitida, "
    "credencial com QR Code ou direitos do ambulante."
)


@dataclass(frozen=True)
class TrechoConhecimento:
    id: str
    titulo: str
    tags: tuple[str, ...]
    texto: str


@dataclass(frozen=True)
class RespostaAssistente:
    texto: str
    fonte: str
    trecho_id: str


BASE_CONHECIMENTO: tuple[TrechoConhecimento, ...] = (
    TrechoConhecimento(
        id="documentos_alimentos",
        titulo="Documentos para venda de alimentos",
        tags=(
            "alimento",
            "alimentos",
            "comida",
            "lanche",
            "lanches",
            "sanitario",
            "vigilancia",
            "laudo",
            "manipulacao",
        ),
        texto=(
            "Para comercializar alimentos no APAL você precisa dos documentos "
            "básicos de todo ambulante e do laudo sanitário.\n\n"
            "Documentos de todos os requerentes:\n"
            "• Documento de identificação oficial com foto (RG, CNH ou Carteira "
            "de Trabalho) e CPF;\n"
            "• Comprovante de residência atualizado no município (água, luz ou "
            "telefone dos últimos 90 dias);\n"
            "• Foto 3x4 recente do titular, para a credencial;\n"
            "• Foto nítida do equipamento de trabalho (carrinho, barraca, "
            "food truck, isopor etc.).\n\n"
            "Exclusivo para alimentos: Certificado da Vigilância Sanitária "
            "(laudo sanitário) ou atestado de manipulação de alimentos. Sem "
            "esse anexo a triagem não avança a solicitação.\n\n"
            "Se você tiver CNPJ/MEI, anexe também o comprovante do MEI. "
            "Envie os arquivos na etapa de documentos do painel."
        ),
    ),
    TrechoConhecimento(
        id="documentos_gerais",
        titulo="Documentos necessários para o cadastro",
        tags=(
            "documento",
            "documentos",
            "anexo",
            "anexos",
            "rg",
            "cpf",
            "comprovante",
            "cadastro",
            "checklist",
        ),
        texto=(
            "Para evitar atraso na análise da licença, tenha em mãos:\n"
            "• Documento de identificação oficial com foto (RG, CNH ou Carteira "
            "de Trabalho) e CPF;\n"
            "• Comprovante de residência atualizado em Vitória da Conquista "
            "(últimos 90 dias);\n"
            "• Foto 3x4 recente do titular;\n"
            "• Foto nítida do equipamento de trabalho.\n\n"
            "Categorias de alimentos exigem ainda o laudo da Vigilância "
            "Sanitária. Categorias com estrutura de maior risco podem exigir "
            "laudo dos Bombeiros. Quem possui CNPJ anexa o MEI."
        ),
    ),
    TrechoConhecimento(
        id="prazos",
        titulo="Prazos de validade e renovação",
        tags=(
            "prazo",
            "prazos",
            "validade",
            "renovacao",
            "renovar",
            "vencer",
            "vencimento",
            "anual",
        ),
        texto=(
            "A licença de comércio ambulante é precária, pessoal e "
            "intransferível.\n\n"
            "Validade: o alvará vale no máximo até 31 de dezembro do ano em "
            "que foi emitido e precisa ser renovado todo ano.\n\n"
            "Renovação: protocolize o pedido no APAL com antecedência mínima "
            "de 30 dias antes do vencimento. O sistema envia aviso por e-mail "
            "e no painel 45 dias antes do vencimento.\n\n"
            "É proibido alugar, vender ou transferir o ponto e a licença. "
            "O descumprimento gera cassação da credencial."
        ),
    ),
    TrechoConhecimento(
        id="zona_proibida",
        titulo="Zona permitida e locais proibidos",
        tags=(
            "zona",
            "ponto",
            "local",
            "locais",
            "proibido",
            "permitido",
            "carrinho",
            "barraca",
            "calcada",
            "postura",
            "posicionar",
        ),
        texto=(
            "Você só pode atuar no ponto e no horário autorizados na licença. "
            "O Código de Posturas (Lei nº 695/1993) proíbe ocupar locais que "
            "prejudiquem pedestres ou o trânsito. Não posicione o equipamento "
            "em:\n"
            "• Rampas de acessibilidade e faixas de pedestres;\n"
            "• Entradas de hospitais, escolas, órgãos públicos e saídas de "
            "emergência;\n"
            "• Pontos de ônibus e táxis;\n"
            "• Portas de estabelecimentos fixos do mesmo ramo.\n\n"
            "Salvo feiras com espaço fixo, o equipamento deve ser recolhido ao "
            "fim do expediente. Estrutura abandonada na via é recolhida pela "
            "fiscalização."
        ),
    ),
    TrechoConhecimento(
        id="credencial_qr",
        titulo="Credencial digital e QR Code",
        tags=(
            "credencial",
            "crachá",
            "cracha",
            "qr",
            "codigo",
            "alvara",
            "alvará",
            "licenca",
            "direito",
            "direitos",
        ),
        texto=(
            "Com a taxa paga, a credencial digital com QR Code fica disponível "
            "no painel para impressão. Ela comprova que você está regularizado.\n\n"
            "Fiscais leem o QR para conferir se a taxa está paga, se a licença "
            "está ativa e se você está no ponto e no horário corretos. "
            "Cidadãos também podem conferir pela câmera do celular.\n\n"
            "Mantenha a credencial visível no ponto. Licença suspensa, vencida "
            "ou cassada não gera QR válido."
        ),
    ),
    TrechoConhecimento(
        id="limpeza_auxiliar",
        titulo="Limpeza do ponto e auxiliar",
        tags=(
            "limpeza",
            "lixo",
            "lixeira",
            "auxiliar",
            "ajudante",
            "residuo",
        ),
        texto=(
            "É dever manter a área do ponto limpa durante e após o expediente. "
            "Tenha pelo menos uma lixeira com saco plástico para os clientes. "
            "Descartar lixo, resíduos ou óleo na calçada ou em bueiros gera "
            "autuação.\n\n"
            "O titular pode cadastrar até um auxiliar, com RG, CPF e "
            "comprovante de residência, para emitir credencial de apoio em "
            "ausência justificada."
        ),
    ),
    TrechoConhecimento(
        id="apreensao",
        titulo="Apreensão de mercadorias",
        tags=(
            "apreensao",
            "apreender",
            "mercadoria",
            "multa",
            "recuperar",
        ),
        texto=(
            "Produtos não perecíveis apreendidos: o titular tem até 30 dias "
            "para comparecer à Gerência de Posturas (Ceasa), apresentar nota "
            "fiscal de origem e pagar multa e taxa de depósito.\n\n"
            "Produtos perecíveis sem comprovação sanitária não são devolvidos: "
            "são doados a instituições de caridade do município."
        ),
    ),
)


def _normalizar(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _tokens(texto: str) -> set[str]:
    bruto = "".join(c if c.isalnum() else " " for c in _normalizar(texto))
    return {t for t in bruto.split() if t and t not in _STOPWORDS and len(t) > 1}


def _pontuar(trecho: TrechoConhecimento, tokens: set[str]) -> int:
    tags = {_normalizar(t) for t in trecho.tags}
    titulo = _tokens(trecho.titulo)
    corpo = _tokens(trecho.texto)
    pontos = 0
    for token in tokens:
        if token in tags:
            pontos += 4
        elif token in titulo:
            pontos += 2
        elif token in corpo:
            pontos += 1
    sobre_alimento = bool(tokens & {"alimento", "alimentos", "comida", "lanche"})
    sobre_documento = bool(tokens & {"documento", "documentos", "anexo", "laudo"})
    if trecho.id == "documentos_alimentos" and sobre_alimento and sobre_documento:
        pontos += 8
    return pontos


def consultar_conhecimento(pergunta: str) -> RespostaAssistente:
    """Recupera o trecho mais pertinente da base local."""
    tokens = _tokens(pergunta)
    if not tokens:
        return RespostaAssistente(_FALLBACK, "base local", "fallback")

    melhor = None
    melhor_pontos = 0
    for trecho in BASE_CONHECIMENTO:
        pontos = _pontuar(trecho, tokens)
        if pontos > melhor_pontos:
            melhor = trecho
            melhor_pontos = pontos

    if melhor is None or melhor_pontos == 0:
        return RespostaAssistente(_FALLBACK, "base local", "fallback")

    return RespostaAssistente(melhor.texto, melhor.titulo, melhor.id)
