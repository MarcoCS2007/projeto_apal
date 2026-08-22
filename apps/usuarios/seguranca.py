"""Matriz de módulos × perfis gravada pelo painel Master."""

PERFIS_MATRIZ = (
    ("ambulante", "Ambulante"),
    ("fiscal", "Fiscal de Rua"),
    ("gestor", "Gestor Municipal"),
    ("cidadao", "Cidadão / Público"),
)

MODULOS_PERMISSAO = (
    ("mapa_vagas", "Consulta do Mapa de Vagas em Tempo Real"),
    ("solicitacao_licenca", "Solicitação e Renovação de Licença"),
    ("emissao_alvara", "Emissão Direta e Validação de Alvará"),
    ("leitura_qr", "Leitura de QR Code / Validação de Campo"),
    ("ocorrencias", "Lavratura de Autos de Ocorrência / Apreensão"),
    ("rotas_fiscais", "Criação e Execução de Rotas de Fiscalização"),
    ("relatorios", "Exportação de Relatórios Gerenciais (.CSV / .PDF)"),
)

CELULAS_EDITAVEIS = {
    "mapa_vagas": frozenset({"ambulante", "fiscal", "gestor", "cidadao"}),
    "solicitacao_licenca": frozenset({"ambulante", "gestor"}),
    "emissao_alvara": frozenset({"gestor"}),
    "leitura_qr": frozenset({"fiscal", "gestor", "cidadao"}),
    "ocorrencias": frozenset({"fiscal", "gestor"}),
    "rotas_fiscais": frozenset({"fiscal", "gestor"}),
    "relatorios": frozenset({"gestor"}),
}


def campo_matriz(modulo, perfil):
    return f"matriz_{modulo}_{perfil}"


def matriz_padrao():
    return {
        modulo: dict.fromkeys(perfis, True)
        for modulo, perfis in CELULAS_EDITAVEIS.items()
    }
