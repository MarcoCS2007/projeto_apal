# Módulo Usuários — Autenticação, perfis e painéis

Pasta: `apps/usuarios`

Este é o núcleo de identidade do APAL: contas, login (web e API), cadastro do ambulante, perfil, score de reputação, painel Master e a maior parte das telas do gestor (orquestrando licenciamento, espaços e fiscalização).

O contrato JWT está detalhado em [API-AUTENTICACAO.md](API-AUTENTICACAO.md). Aqui está o uso operacional do módulo.

---

## Perfis

O modelo de autenticação é `UsuarioBase` (`AUTH_USER_MODEL`). O login usa **CPF** (`USERNAME_FIELD`). Cada perfil é uma subclasse (herança multi-tabela):

| Perfil | Modelo | Canal web | Para que existe |
| --- | --- | --- | --- |
| Ambulante | `Ambulante` | `/entrar/` | Trabalhador: cadastro, perfil, alvará, credencial, score, assistente |
| Fiscal | `Fiscal` | `/fiscal/entrar/` | Campo: leitura de QR e lavratura de ocorrência |
| Gestor | `Gestor` | `/login/` | Backoffice: fila, triagem, emissão, dossiê, ocorrências, relatórios |
| Administrador | `Administrador` | `/login/` | Painel Master: gestores, fiscais, permissões, logs de IA, backup |

A propriedade `user.role` devolve o perfil. Mixins nas views web impedem que um perfil entre na área de outro.

---

## Modelos principais

### `UsuarioBase`

CPF, nome, e-mail, telefones, foto, flags Django (`is_active`, `is_staff`) e campos de `ModeloBase`. Propriedades úteis: `nome_completo`, `iniciais`, `cpf_formatado`, `cpf_mascarado`.

### `Ambulante`

Dados do ofício (apelido, CNPJ, tipo de atuação, escolaridade, NIS, ponto pretendido) e:

- `genero` — feminino, masculino, outro ou não informado
- `renda_estimada` — valor opcional usado nos relatórios sociodemográficos
- `codigo_qr_code` — hash HMAC gravado na emissão do alvará
- `pontuacao` — score 0–100 (inicia em 100)
- `dados_complementares` — JSON (categoria pretendida, conta suspensa/cancelada, RG, flags de cadastro)
- `cadastro_completo` — verdadeiro só com data de nascimento, escolaridade, atuação, endereço e estrutura com metragem
- `situacao_conta` — `pendente`, `completa`, `suspensa` ou `cancelada`
- `aceite_lgpd`, `aceite_lgpd_em`, `base_legal_lgpd` — consentimento no registro da conta

### `Fiscal` / `Gestor` / `Administrador`

Matrícula e zona (fiscal), cargo e departamento (gestor), flags `acesso_master` e `acesso_painel_tecnico` (administrador).

### `EventoScore`

Histórico imutável de pontos. Eventos com `chave` não se repetem (ex.: o mesmo alvará não pontua duas vezes).

### `ConfiguracaoSeguranca`

Singleton (`pk=1`) com tempo de sessão, tentativas de bloqueio, exigência de 2FA, retenção de logs e **matriz de módulos × perfis** editada no Master.

### `LogAcessoDossie`

Auditoria LGPD: quem abriu (ou exportou em PDF) o dossiê de qual ambulante. Purgado com `purgar_retencao`.

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
| `/registro/` | Visitante | Cria conta de ambulante (CPF, e-mail, senha, aceite LGPD) |
| `/entrar/` | Ambulante | Login por sessão |
| `/fiscal/entrar/` | Fiscal | Login por sessão |
| `/login/` | Gestor e Master | Login do backoffice (ambulante/fiscal são recusados) |
| `/logout/` | Autenticado | `POST` com CSRF; encerra sessão |
| `/redefinir-senha/` | Qualquer um | Pedido de redefinição por e-mail ou CPF |
| `/redefinir-senha/<uidb64>/<token>/` | Quem recebeu o e-mail | Confirma a nova senha |

### Ambulante

| URL | O que faz |
| --- | --- |
| `/ambulante/` | Painel: status do cadastro, licença, documentos, atalho ao score |
| `/ambulante/perfil/` | E-mail, CPF, foto 3x4 e endereço residencial |
| `/ambulante/cadastro/` | Wizard em 6 etapas |
| `/ambulante/score/` | Faixa, histórico e dicas de regularização |

Alvará, credencial e assistente estão nos módulos [licenciamento](LICENCIAMENTO.md) e [assistente](ASSISTENTE.md).

### Gestor (backoffice)

| URL | O que faz |
| --- | --- |
| `/backoffice/` | Início com contadores (fila, docs, ambulantes) |
| `/gestor/dashboard/` | Indicadores de ocupação, licenças e retrato sociodemográfico |
| `/gestor/dashboard/chart-data/` | JSON dos gráficos (filtros da query string) |
| `/gestor/dashboard/exportar.xlsx` | Planilha Excel do relatório |
| `/gestor/dashboard/exportar.pdf` | PDF do relatório |
| `/gestor/fila/` | Processos em análise / pendência documental |
| `/gestor/analisar/<id>/` | Parecer: deferir, indeferir ou devolver |
| `/gestor/emitir/<id>/` | Emissão do alvará, escala e QR |
| `/gestor/licencas/` | Licenças ativas/vencidas/suspensas |
| `/gestor/ambulantes/` | Lista e busca |
| `/gestor/ambulantes/<id>/dossie/` | Dossiê completo (grava `LogAcessoDossie`) |
| `/gestor/ambulantes/<id>/dossie/pdf/` | Exportação PDF do dossiê |
| `/gestor/ambulantes/<id>/editar/` | Correção cadastral |
| `/gestor/ambulantes/<id>/acao/` | Suspender, reativar ou cancelar conta (`POST`) |
| `/gestor/ocorrencias/` | Fila de autos |
| `/gestor/ocorrencias/<id>/` | Auditoria (status e efeito na licença) |

Triagem de documentos, categorias e pontos: ver [licenciamento](LICENCIAMENTO.md) e [espacos](ESPACOS.md).

### Master

| URL | O que faz |
| --- | --- |
| `/master/` | Painel TI com totais, últimos logins e atalho de backup |
| `/master/backup/` | `POST` — gera dump (exige `acesso_painel_tecnico`) |
| `/master/gestores/` e `/master/gestores/cadastrar/` | Listar / criar gestor |
| `/master/fiscais/` e `/master/fiscais/cadastrar/` | Listar / criar fiscal |
| `/master/permissoes/` | Políticas globais e matriz de acessos |
| `/master/logs-ia/` | Últimas consultas do assistente |

### API JWT

Prefixo `/api/` (`apps/usuarios/urls.py`): `POST /api/login/`, `POST /api/token/refresh/`, `GET /api/me/`, cadastro e score do ambulante. Demais rotas do app: [API-MOVEL.md](API-MOVEL.md). Autenticação: [API-AUTENTICACAO.md](API-AUTENTICACAO.md).

---

## Instruções de uso

### Ambulante — criar conta e completar cadastro

1. Acesse `/registro/`, informe CPF, nome, e-mail e senha e aceite a LGPD.
2. Você entra automaticamente no painel `/ambulante/`.
3. Em **Meu perfil** (`/ambulante/perfil/`) ajuste e-mail, CPF, foto 3x4 e endereço.
4. Clique em completar cadastro (`/ambulante/cadastro/`) e avance as etapas:
   1. Dados pessoais (nascimento, gênero, renda estimada, escolaridade, telefones, NIS)
   2. Endereço residencial
   3. Dados da atividade (CNPJ/MEI se houver, nome fantasia)
   4. Tipo de atuação, estrutura (tipo, metragem em m², foto)
   5. Ponto pretendido e categoria de produto
   6. Anexos (RG/CPF, comprovante; MEI e laudos se a categoria exigir)
5. Em documentos, use **Salvar** para enviar anexos sem protocolar, ou **Enviar** quando o cadastro estiver completo. O envio abre o requerimento na fila da prefeitura.
6. Acompanhe o protocolo em **Meu Alvará**. O score aparece em `/ambulante/score/`.

Login posterior: `/entrar/` com CPF e senha. Esqueceu a senha: `/redefinir-senha/`.

### Fiscal — entrar no campo

1. Acesse `/fiscal/entrar/` com CPF e senha.
2. Você cai no painel de fiscalização. O uso da leitura de QR e do auto está em [FISCALIZACAO.md](FISCALIZACAO.md).

### Gestor — rotina diária

1. Acesse `/login/` (somente gestor ou Master).
2. No `/backoffice/`, veja a fila e os documentos pendentes.
3. **Triagem** (`/gestor/triagem/`): aprove ou rejeite anexos (rejeição exige justificativa).
4. **Em análise** (`/gestor/fila/`): abra o processo, confira metragem × ponto, dê o parecer.
5. Se deferir, o sistema calcula a taxa (`metragem × fator financeiro` da categoria) e redireciona para emissão.
6. Use o **dossiê** para ver score, documentos e ocorrências; exporte PDF se precisar; edite cadastro ou suspenda/cancele a conta.
7. Audite ocorrências em `/gestor/ocorrencias/` — procedente pode suspender a licença automaticamente.
8. Em **Relatórios** (`/gestor/dashboard/`), filtre por bairro, origem, cidade, gênero, faixa etária e escolaridade; exporte Excel ou PDF.

### Master — administrar o sistema

1. Entre em `/login/` com a conta administrador.
2. Cadastre gestores e fiscais pelos formulários do Master (matrícula é obrigatória e única).
3. Em **Permissões**, ajuste tempo de sessão e a matriz módulo × perfil. Administrador sempre tem acesso total.
4. Em **Logs de IA**, audite perguntas e respostas do assistente (até 50 mais recentes na tela).
5. No Painel TI, **Gerar backup restaurável** (só com `acesso_painel_tecnico`).

### Desenvolvedor — autenticação

- Backend: `apps.usuarios.backends.CPFOuEmailBackend` (aceita CPF ou e-mail).
- Tempo de sessão: `aplicar_tempo_sessao` lê `ConfiguracaoSeguranca.tempo_sessao_minutos`.
- Logout é **somente POST**. `GET /logout/` retorna 405.
- Base legal LGPD: `apps/usuarios/lgpd.py`.

---

## Dependências

- Usa [espacos](ESPACOS.md) no cadastro (endereço, estrutura, ponto pretendido).
- Usa [licenciamento](LICENCIAMENTO.md) no painel, fila, emissão, score e relatórios.
- Usa [fiscalizacao](FISCALIZACAO.md) na listagem/auditoria de ocorrências.
- Usa [assistente](ASSISTENTE.md) nos logs do Master.
- Usa [core](CORE.md) no backup disparado pelo Painel TI.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/usuarios/models.py` | Perfis, score, segurança, log de dossiê |
| `apps/usuarios/score.py` | Regras e faixas de pontuação |
| `apps/usuarios/seguranca.py` | Matriz padrão de permissões |
| `apps/usuarios/lgpd.py` | Base legal exibida na privacidade |
| `apps/usuarios/forms_cadastro.py` | Wizard e formulário de perfil |
| `apps/usuarios/views.py` | Login, cadastro, perfil, Master |
| `apps/usuarios/views_gestor.py` | Fila, dossiê, emissão, ocorrências, exportações |
| `apps/usuarios/urls.py` | API JWT |
| `apps/usuarios/urls_web.py` | Rotas HTML |
| `apps/usuarios/backends.py` | Login por CPF ou e-mail |
