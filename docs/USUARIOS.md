# Módulo Usuários — Autenticação, perfis e painéis

Pasta: `apps/usuarios`

Este é o núcleo de identidade do APAL: contas, login (web e API), cadastro do ambulante, score de reputação, painel Master e a maior parte das telas do gestor (orquestrando licenciamento, espaços e fiscalização).

O contrato JWT está detalhado em [API-AUTENTICACAO.md](API-AUTENTICACAO.md). Aqui está o uso operacional do módulo.

---

## Perfis

O modelo de autenticação é `UsuarioBase` (`AUTH_USER_MODEL`). O login usa **CPF** (`USERNAME_FIELD`). Cada perfil é uma subclasse (herança multi-tabela):

| Perfil | Modelo | Canal web | Para que existe |
| --- | --- | --- | --- |
| Ambulante | `Ambulante` | `/entrar/` | Trabalhador: cadastro, alvará, credencial, score, assistente |
| Fiscal | `Fiscal` | `/fiscal/entrar/` | Campo: leitura de QR e lavratura de ocorrência |
| Gestor | `Gestor` | `/login/` | Backoffice: fila, triagem, emissão, dossiê, ocorrências |
| Administrador | `Administrador` | `/login/` | Painel Master: gestores, fiscais, permissões, logs de IA |

A propriedade `user.role` devolve o perfil. Mixins nas views web impedem que um perfil entre na área de outro.

---

## Modelos principais

### `UsuarioBase`

CPF, nome, e-mail, telefones, foto, flags Django (`is_active`, `is_staff`) e campos de `ModeloBase`.

### `Ambulante`

Dados do ofício (apelido, CNPJ, tipo de atuação, escolaridade, NIS, ponto pretendido) e:

- `codigo_qr_code` — hash HMAC gravado na emissão do alvará
- `pontuacao` — score 0–100 (inicia em 100)
- `dados_complementares` — JSON (categoria pretendida, conta suspensa/cancelada)
- `cadastro_completo` — verdadeiro só com data de nascimento, escolaridade, atuação, endereço e estrutura com metragem
- `situacao_conta` — `pendente`, `completa`, `suspensa` ou `cancelada`

### `Fiscal` / `Gestor` / `Administrador`

Matrícula e zona (fiscal), cargo e departamento (gestor), flags de acesso Master.

### `EventoScore`

Histórico imutável de pontos. Eventos com `chave` não se repetem (ex.: o mesmo alvará não pontua duas vezes).

### `ConfiguracaoSeguranca`

Singleton (`pk=1`) com tempo de sessão, tentativas de bloqueio, exigência de 2FA, retenção de logs e **matriz de módulos × perfis** editada no Master.

---

## Score de reputação

Arquivo: `apps/usuarios/score.py`

| Evento | Pontos |
| --- | --- |
| Licença ativa / alvará emitido | +10 |
| Renovação no prazo | +8 |
| Ocorrência procedente | −20 |
| Licença suspensa | −15 |
| Licença cancelada | −25 |

Faixas: **Diamante** (90–100), **Ouro** (75–89), **Prata** (50–74), **Bronze** (0–49). O saldo nunca sai de 0–100.

O score é aplicado automaticamente na emissão, renovação e auditoria de ocorrência — o ambulante não “marca” pontos à mão.

---

## Rotas web

Definidas em `apps/usuarios/urls_web.py` (parte das rotas de fiscalização também está aqui, mas a lógica é do módulo [fiscalizacao](FISCALIZACAO.md)).

### Público / autenticação

| URL | Quem | O que faz |
| --- | --- | --- |
| `/registro/` | Visitante | Cria conta de ambulante (CPF, e-mail, senha) |
| `/entrar/` | Ambulante | Login por sessão |
| `/fiscal/entrar/` | Fiscal | Login por sessão |
| `/login/` | Gestor e Master | Login do backoffice (ambulante/fiscal são recusados) |
| `/logout/` | Autenticado | `POST` com CSRF; encerra sessão |
| `/redefinir-senha/` | Qualquer um | Pedido de redefinição por e-mail ou CPF |

### Ambulante

| URL | O que faz |
| --- | --- |
| `/ambulante/` | Painel: status do cadastro, licença, documentos, atalho ao score |
| `/ambulante/cadastro/` | Wizard em 6 etapas |
| `/ambulante/score/` | Faixa, histórico e dicas de regularização |

Alvará, credencial e assistente estão nos módulos [licenciamento](LICENCIAMENTO.md) e [assistente](ASSISTENTE.md).

### Gestor (backoffice)

| URL | O que faz |
| --- | --- |
| `/backoffice/` | Início com contadores (fila, docs, ambulantes) |
| `/gestor/dashboard/` | Indicadores de ocupação e licenças |
| `/gestor/fila/` | Processos em análise / pendência documental |
| `/gestor/analisar/<id>/` | Parecer: deferir, indeferir ou devolver |
| `/gestor/emitir/<id>/` | Emissão do alvará, escala e QR |
| `/gestor/licencas/` | Licenças ativas/vencidas/suspensas |
| `/gestor/ambulantes/` | Lista e busca |
| `/gestor/ambulantes/<id>/dossie/` | Dossiê completo |
| `/gestor/ambulantes/<id>/editar/` | Correção cadastral |
| `/gestor/ambulantes/<id>/acao/` | Suspender, reativar ou cancelar conta (`POST`) |
| `/gestor/ocorrencias/` | Fila de autos |
| `/gestor/ocorrencias/<id>/` | Auditoria (status e efeito na licença) |

Triagem de documentos, categorias e pontos: ver [licenciamento](LICENCIAMENTO.md) e [espacos](ESPACOS.md).

### Master

| URL | O que faz |
| --- | --- |
| `/master/` | Painel com totais e últimos logins |
| `/master/gestores/` e `/master/gestores/cadastrar/` | Listar / criar gestor |
| `/master/fiscais/` e `/master/fiscais/cadastrar/` | Listar / criar fiscal |
| `/master/permissoes/` | Políticas globais e matriz de acessos |
| `/master/logs-ia/` | Últimas consultas do assistente |

### API JWT

Prefixo `/api/` (`apps/usuarios/urls.py`): `POST /api/login/`, `POST /api/token/refresh/`, `GET /api/me/`, cadastro e score do ambulante. Demais rotas do app: [API-MOVEL.md](API-MOVEL.md). Autenticação: [API-AUTENTICACAO.md](API-AUTENTICACAO.md).

---

## Instruções de uso

### Ambulante — criar conta e completar cadastro

1. Acesse `/registro/`, informe CPF, nome, e-mail e senha.
2. Você entra automaticamente no painel `/ambulante/`.
3. Clique em completar cadastro (`/ambulante/cadastro/`) e avance as etapas:
   1. Dados pessoais (nascimento, escolaridade, foto)
   2. Endereço residencial
   3. Dados da atividade (tipo de atuação, CNPJ/MEI se houver)
   4. Estrutura (tipo, metragem em m², foto)
   5. Ponto pretendido e categoria de produto
   6. Anexos (RG/CPF, comprovante; MEI e laudos se a categoria exigir)
4. Em documentos, use **Salvar** para enviar anexos sem protocolar, ou **Enviar** quando o cadastro estiver completo. O envio abre o requerimento na fila da prefeitura.
5. Acompanhe o protocolo em **Meu Alvará**. O score aparece em `/ambulante/score/`.

Login posterior: `/entrar/` com CPF e senha. Esqueceu a senha: `/redefinir-senha/`.

### Fiscal — entrar no campo

1. Acesse `/fiscal/entrar/` com CPF e senha.
2. Você cai no painel de fiscalização. O uso da leitura de QR e do auto está em [FISCALIZACAO.md](FISCALIZACAO.md).

### Gestor — rotina diária

1. Acesse `/login/` (somente gestor ou Master).
2. No `/backoffice/`, veja a fila e os documentos pendentes.
3. **Triagem** (`/gestor/triagem/`): aprove ou rejeite anexos (rejeição exige justificativa).
4. **Em análise** (`/gestor/fila/`): abra o processo, confira metragem × ponto, dê o parecer.
5. Se deferir, emita o alvará (datas, ponto, dias e horário). O QR é gerado nesse momento.
6. Use o **dossiê** para ver score, documentos e ocorrências; edite cadastro ou suspenda/cancele a conta se necessário.
7. Audite ocorrências em `/gestor/ocorrencias/` — procedente pode suspender a licença automaticamente.

### Master — administrar o sistema

1. Entre em `/login/` com a conta administrador.
2. Cadastre gestores e fiscais pelos formulários do Master (matrícula é obrigatória e única).
3. Em **Permissões**, ajuste tempo de sessão e a matriz módulo × perfil. Administrador sempre tem acesso total.
4. Em **Logs de IA**, audite perguntas e respostas do assistente (até 50 mais recentes na tela).

### Desenvolvedor — autenticação

- Backend: `apps.usuarios.backends.CPFOuEmailBackend` (aceita CPF ou e-mail).
- Tempo de sessão: `aplicar_tempo_sessao` lê `ConfiguracaoSeguranca.tempo_sessao_minutos`.
- Logout é **somente POST**. `GET /logout/` retorna 405.

---

## Dependências

- Usa [espacos](ESPACOS.md) no cadastro (endereço, estrutura, ponto pretendido).
- Usa [licenciamento](LICENCIAMENTO.md) no painel, fila, emissão e score.
- Usa [fiscalizacao](FISCALIZACAO.md) na listagem/auditoria de ocorrências.
- Usa [assistente](ASSISTENTE.md) nos logs do Master.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/usuarios/models.py` | Perfis, score, segurança |
| `apps/usuarios/score.py` | Regras e faixas de pontuação |
| `apps/usuarios/seguranca.py` | Matriz padrão de permissões |
| `apps/usuarios/views.py` | Login, cadastro, Master |
| `apps/usuarios/views_gestor.py` | Fila, dossiê, emissão, ocorrências |
| `apps/usuarios/urls.py` | API JWT |
| `apps/usuarios/urls_web.py` | Rotas HTML |
| `apps/usuarios/backends.py` | Login por CPF ou e-mail |
