# Módulo Assistente — Orientação educativa ao ambulante

Pasta: `apps/assistente`

Chat de dúvidas sobre documentos, prazos, zona permitida e credencial. A resposta vem de uma **base local** (não há chamada a API de IA). Cada pergunta vira um log auditável pelo Master.

---

## Para que serve

- Tirar dúvidas frequentes do ambulante em linguagem direta.
- Guardar pergunta, resposta e fonte para transparência.
- Permitir que o Master veja o que está sendo perguntado (`/master/logs-ia/`).

Não substitui o atendimento da prefeitura nem emite licença. Não acessa dados de outros ambulantes.

---

## Modelo

`LogAssistente`:

| Campo | Conteúdo |
| --- | --- |
| `ambulante` | Quem perguntou |
| `pergunta` | Texto enviado (até 500 caracteres no formulário) |
| `resposta` | Trecho devolvido pela base |
| `fonte` | Título do trecho (ou “base local” no fallback) |
| `criado_em` | Data da consulta |

Ordenação padrão: mais recente primeiro.

---

## Como a resposta é escolhida

1. A view chama `responder_pergunta(ambulante, pergunta)` em `apps/assistente/services.py`.
2. Isso usa `consultar_conhecimento` em `apps/core/ia.py`.
3. A pergunta é normalizada (sem acento), tokenizada e pontuada contra tags, título e corpo de cada trecho.
4. O trecho com maior pontuação vira a resposta; pontuação zero devolve um fallback pedindo para perguntar sobre documentos, prazos, zona ou QR.

Temas cobertos na base:

- Documentos gerais e documentos para **alimentos** (laudo sanitário)
- Prazos de validade e renovação (alvará até 31/12; protocolar 30 dias antes)
- Zona permitida / locais proibidos (Código de Posturas)
- Credencial digital e QR Code
- Limpeza do ponto e auxiliar
- Apreensão de mercadorias

Sugestões exibidas na tela:

- quais documentos preciso para alimentos?
- quais os prazos de renovação?
- onde é proibido posicionar o carrinho?
- como funciona a credencial com QR Code?

---

## Rotas e telas

| URL | Perfil | Função |
| --- | --- | --- |
| `/ambulante/assistente/` | Ambulante | Formulário + histórico das últimas 20 perguntas |
| `/master/logs-ia/` | Master | Auditoria (view no módulo usuarios) |
| `/api/ambulante/assistente/` | Ambulante (JWT) | Histórico `GET` e pergunta `POST` |

Há um atalho no painel do ambulante (`templates/ambulante/_assistente_widget.html`).

Django Admin: `LogAssistente` registrado em `apps/assistente/admin.py` (lista por ambulante, fonte e data).

---

## Instruções de uso

### Ambulante — perguntar

1. Faça login em `/entrar/`.
2. No painel, abra o assistente (`/ambulante/assistente/`) ou o atalho do widget.
3. Digite a dúvida ou clique em uma sugestão.
4. Envie. A resposta aparece no histórico da conversa (ordem cronológica na tela).
5. Se a resposta for o texto genérico de “não encontrei”, reformule com palavras do tema (documento, prazo, zona, QR, apreensão).

O assistente **não** consulta a sua licença nem o status do protocolo. Para isso use Meu Alvará e o painel.

### Master — auditar consultas

1. Entre no painel Master (`/master/`).
2. Abra **Logs de IA** (`/master/logs-ia/`).
3. A tela mostra até 50 registros recentes, total de logs, consultas do dia e quantos ambulantes já perguntaram.
4. Use o Admin Django (`/admin/`) se precisar buscar por CPF, trecho da pergunta ou da resposta.

### Desenvolvedor — incluir um novo tema

1. Adicione um `TrechoConhecimento` em `BASE_CONHECIMENTO` (`apps/core/ia.py`) com `id`, `titulo`, `tags` e `texto`.
2. Cubra o caso em `apps/assistente/tests.py` / testes do `core`.
3. Opcional: inclua uma frase em `SUGESTOES_ASSISTENTE`.

Não coloque segredos nem dados pessoais na base: ela é compartilhada por todos os ambulantes.

---

## Dependências

- [core](CORE.md): motor RAG (`ia.py`).
- [usuarios](USUARIOS.md): `AcessoAmbulanteMixin` na tela; `MasterLogsIAView` na auditoria. Logs antigos saem com `python manage.py purgar_retencao`.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/assistente/models.py` | `LogAssistente` |
| `apps/assistente/services.py` | Grava log após consultar a base |
| `apps/assistente/views.py` | Tela do ambulante |
| `apps/assistente/forms.py` | Validação da pergunta |
| `apps/assistente/urls_web.py` | `/ambulante/assistente/` |
| `apps/core/ia.py` | Trechos e pontuação |
| `templates/ambulante/assistente.html` | Interface |
| `templates/master/logs-ia.html` | Auditoria Master |
