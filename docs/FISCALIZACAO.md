# Módulo Fiscalização — Operação de rua e auditoria

Pasta: `apps/fiscalizacao`

Apoia o fiscal em campo (consulta por QR, CPF, nome ou número do alvará) e o gestor na auditoria do auto, com efeito sobre a licença e o score.

As URLs do painel do fiscal estão em `apps/usuarios/urls_web.py`; as views e regras ficam neste app.

---

## Para que serve

- Validar a credencial no ponto (QR HMAC).
- Detectar licença suspensa, vencida, adulterada ou fora do horário da escala.
- Registrar ocorrência com tipo, descrição, local e foto.
- Permitir que o gestor mude o status do auto e, se procedente, suspenda ou cancele a licença.

---

## Modelos

### `OcorrenciaInspecao`

| Campo | Uso |
| --- | --- |
| `fiscal` | Quem lavrou |
| `ambulante` | Alvo (opcional — pode ser “não identificado”) |
| `tipo_ocorrencia` | Ver tabela abaixo |
| `descricao` | Relato |
| `local_ocorrencia` | Texto (em geral o nome do ponto) |
| `evidencia_foto` | Foto do auto |
| `status_ocorrencia` | Fluxo de auditoria |

Tipos (`TipoOcorrencia`): Advertência, Multa, Apreensão, irregularidade de ponto, irregularidade de horário, comércio sem licença válida, falta de credencial, outra irregularidade.

A leitura do QR sugere o tipo:

| Motivo da inspeção | Tipo sugerido |
| --- | --- |
| Fora do horário | Irregularidade de horário |
| Suspenso / vencido / inválido | Comércio sem licença válida |
| QR adulterado | Falta de credencial |

---

## Status da ocorrência

```text
Registrada ──► Em análise ──► Procedente ──► Convertida em multa
     │              │
     └──────────────┴──► Improcedente
```

Transições permitidas (`TRANSICOES_STATUS` em `services.py`):

- Registrada → Em análise, Procedente ou Improcedente
- Em análise → Procedente ou Improcedente
- Procedente → Convertida em multa

Improcedente e Convertida em multa são finais (`status_final`).

Ao marcar **Procedente**, o sistema:

1. Desconta **20** pontos no score.
2. **Suspende** a licença Ativa (salvo se o gestor escolher outra ação).

Cancelar a licença só a partir de Procedente ou Convertida em multa (−25 no score).

---

## Rotas

| URL | Perfil | Função |
| --- | --- | --- |
| `/fiscal/` | Fiscal | Busca e ficha do ambulante |
| `/fiscal/ocorrencia/` | Fiscal | Formulário do auto |
| `/gestor/ocorrencias/` | Gestor | Lista com filtros |
| `/gestor/ocorrencias/<id>/` | Gestor | Detalhe e auditoria |
| `/api/fiscal/busca/` | Fiscal (JWT) | Busca por CPF, nome, alvará ou QR |
| `/api/fiscal/qr/` | Fiscal (JWT) | Validar o hash da credencial |
| `/api/fiscal/ocorrencias/` | Fiscal (JWT) | `POST` do auto com foto |

Login do fiscal: `/fiscal/entrar/` (módulo usuarios). App móvel: [API-MOVEL.md](API-MOVEL.md).

---

## Como a inspeção classifica o QR

`inspecionar_qr(codigo)` e `consultar_campo(termo)` em `apps/fiscalizacao/services.py`:

1. Termo com 32+ caracteres é tratado como hash do QR.
2. Senão tenta número de alvará (`ALV-…`), depois CPF (11 dígitos) ou nome.
3. Vários nomes → pede seleção.
4. Ambulante sem licença emitida → motivo `sem_licenca`.
5. Hash que não confere com HMAC → `adulterado`.
6. Licença Ativa mas fora da escala do dia/hora atuais → `fora_horario` (ainda mostra a ficha).

Antes de classificar, licenças vencidas são atualizadas (`marcar_licencas_vencidas`).

---

## Instruções de uso

### Fiscal — conferir um ambulante

1. Entre em `/fiscal/entrar/`.
2. No painel `/fiscal/`, informe:
   - o código do QR (cole ou use o campo de busca),
   - o CPF,
   - o nome, ou
   - o número do alvará (`ALV-2026-0001`).
3. A ficha mostra titular, ponto, categoria, horário autorizado e se o QR é aceito.
4. Se a credencial for inválida ou estiver fora do horário, use o atalho para **registrar ocorrência** — tipo, local e descrição já vêm sugeridos.

### Fiscal — lavrar o auto

1. Abra `/fiscal/ocorrencia/` (com ou sem busca prévia).
2. Selecione o tipo, descreva o fato, informe o local e, se possível, anexe foto.
3. Ambulante pode ficar em branco se o infrator não for identificado.
4. Ao gravar, o status fica **Registrada**. O gestor assume a partir daí. O fiscal **não** suspende licença neste passo.

### Gestor — auditar

1. `/gestor/ocorrencias/` — filtre por texto, status ou tipo.
2. Abra o detalhe.
3. Avance o status (não pule etapas ilegais).
4. Em **Procedente**, a licença Ativa passa a **Suspenso** por padrão.
5. Para cassar, escolha a ação de **cancelar** (só depois de procedente).
6. Improcedente encerra o auto sem penalidade de licença.

O dossiê do ambulante lista as ocorrências e o score já refletido.

---

## Dependências

- [core](CORE.md): HMAC do QR.
- [licenciamento](LICENCIAMENTO.md): ficha, escala, vencimento, suspensão/cancelamento.
- [usuarios](USUARIOS.md): Fiscal, Ambulante, score.

Não há `urls_web.py` neste app: as telas do fiscal estão em `usuarios.urls_web`; as do gestor, em `views_gestor`. A API JWT fica em `apps/fiscalizacao/urls.py` (`/api/fiscal/`).

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/fiscalizacao/models.py` | Ocorrência, tipos e status |
| `apps/fiscalizacao/services.py` | Inspeção, registro, auditoria |
| `apps/fiscalizacao/views.py` | Painel e formulário do fiscal |
| `apps/fiscalizacao/forms.py` | Busca, auto e auditoria |
| `templates/fiscal/` | Telas de campo |
| `templates/gestor/ocorrencias.html` | Lista do gestor |
| `templates/gestor/ocorrencia-detalhe.html` | Auditoria |
