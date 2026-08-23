# Módulo Core — Fundação do sistema

Pasta: `apps/core`

O `core` não tem um painel próprio de negócio. Ele concentra o que **todos os outros módulos reutilizam**: modelo base com auditoria, permissões por perfil, páginas públicas, QR Code da credencial, consulta educativa local (RAG), seed, backup e retenção LGPD.

---

## Para que serve

- Padronizar `criado_em`, `atualizado_em` e `ativo` em quase todas as entidades.
- Expor as páginas institucionais (home, sobre, FAQ, privacidade).
- Tratar páginas de erro 404 e 500.
- Gerar e validar o hash HMAC do QR da credencial.
- Responder o assistente **offline**, sem API externa de IA.
- Popular o banco com categorias, pontos e usuários de teste.
- Gerar dump restaurável e aplicar a política de retenção de logs.

---

## Modelos

`ModeloBase` (abstrato) em `apps/core/models.py`:

| Campo | Uso |
| --- | --- |
| `criado_em` | Data/hora de criação |
| `atualizado_em` | Última alteração |
| `ativo` | Soft-delete / inativação |
| `objects` | Manager padrão (inclui inativos) |
| `ativos` | Manager que filtra `ativo=True` |

Não há tabelas próprias neste app (sem migrações de modelo).

---

## Páginas públicas e erros

Rotas em `apps/core/urls.py`, incluídas na raiz do projeto:

| URL | Nome | Template | Conteúdo |
| --- | --- | --- | --- |
| `/` | `index` | `home.html` | Landing institucional |
| `/sobre/` | `sobre` | `publico/sobre.html` | Sobre o APAL |
| `/faq/` | `faq` | `publico/faq.html` | Perguntas frequentes |
| `/privacidade/` | `privacidade` | `publico/privacidade.html` | Política LGPD (base legal e meses de retenção) |

Qualquer visitante acessa. Login e cadastro ficam no módulo [usuarios](USUARIOS.md).

Em `config/urls.py`:

- `handler404` → `apps.core.views.pagina_nao_encontrada` (`templates/404.html`)
- `handler500` → `apps.core.views.erro_servidor` (`templates/500.html`)

Com `DEBUG=True`, o Django mostra a página de diagnóstico; os handlers valem em produção.

---

## Permissões da API

Arquivo: `apps/core/permissions.py`

Use nas views DRF quando a rota for exclusiva de um perfil:

```python
from apps.core.permissions import IsAmbulante, IsFiscal, IsGestor, IsAdministrador
```

| Classe | Permite se `user.role` for |
| --- | --- |
| `IsAmbulante` | `ambulante` |
| `IsFiscal` | `fiscal` |
| `IsGestor` | `gestor` |
| `IsAdministrador` | `administrador` |

Elas já exigem usuário autenticado. Combine com `|` do DRF se a rota aceitar mais de um perfil. Detalhes do JWT: [API-AUTENTICACAO.md](API-AUTENTICACAO.md). Rotas do app: [API-MOVEL.md](API-MOVEL.md).

Idioma e fuso: `LANGUAGE_CODE=pt-br` e `TIME_ZONE=America/Bahia` em `config/settings/base.py`.

---

## QR Code da credencial

Arquivos: `apps/core/qrcode.py` e `apps/core/qr_imagem.py`

| Função | O que faz |
| --- | --- |
| `gerar_codigo_qr(licenca)` | HMAC-SHA256 estável (`pk` + número oficial), com a `SECRET_KEY` |
| `validar_codigo_qr(codigo)` | Confere o hash no ambulante, exige licença **Ativa** e `qr_valido` |
| `renderizar_qr_png(payload)` | Gera a imagem PNG exibida na credencial |

O hash é gravado em `Ambulante.codigo_qr_code` na **emissão do alvará** (módulo licenciamento). O fiscal lê esse código no módulo [fiscalizacao](FISCALIZACAO.md).

Antes de validar, o sistema marca licenças com vencimento ultrapassado como **Vencido**.

---

## Base de conhecimento (IA local)

Arquivo: `apps/core/ia.py`

`consultar_conhecimento(pergunta)` pontua a pergunta contra trechos fixos (documentos, prazos, zona, QR, limpeza, apreensão) e devolve o texto mais pertinente. Não chama serviço externo: funciona em testes e no hackathon offline.

O módulo [assistente](ASSISTENTE.md) é quem grava o log e expõe a tela. O Master consulta esses logs em `/master/logs-ia/`.

---

## Instruções de uso

### Desenvolvedor — herdar o modelo base

```python
from apps.core.models import ModeloBase

class MinhaEntidade(ModeloBase):
    ...
```

Use `MinhaEntidade.ativos.all()` quando quiser ignorar registros inativados.

### Desenvolvedor — popular o banco local

Com o projeto no ar:

```bash
python manage.py seed_inicial
python manage.py seed_massivo   # volume extra para gráficos e relatórios
```

No Docker: `make seed` / `make seed_massivo` (ou `./dev.sh exec python manage.py seed_inicial`).

`seed_inicial` cria categorias (com fator financeiro), pontos de ocupação e contas de demonstração (Master, gestores, fiscais e ambulantes). Senhas: ver [README da pasta docs](README.md).

### Visitante — páginas institucionais

1. Abra `http://localhost:8000`.
2. Use **Sobre**, **FAQ** e a política de privacidade no site público.
3. Para entrar no sistema, siga o canal do seu perfil em [USUARIOS.md](USUARIOS.md).

### Gestor / fiscal — o QR não é configurado aqui

A geração acontece na emissão do alvará. Este módulo só fornece o algoritmo. Se o QR “não bate”, confira `SECRET_KEY` (o hash muda se a chave mudar) e se a licença ainda está **Ativa**.

### Master / TI — backup e retenção

Backup e purge estão documentados em [BACKUP.md](BACKUP.md). Os comandos moram neste app (`backup_banco`, `purgar_retencao`); a tela **Gerar backup** do Painel TI dispara `POST /master/backup/`.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/core/models.py` | `ModeloBase` e `AtivoManager` |
| `apps/core/permissions.py` | Permissões DRF por perfil |
| `apps/core/urls.py` / `views.py` | Home, sobre, FAQ, privacidade, 404/500 |
| `apps/core/qrcode.py` | Hash e validação do QR |
| `apps/core/qr_imagem.py` | PNG do QR |
| `apps/core/ia.py` | RAG local do assistente |
| `apps/core/backup.py` | Dump JSON restaurável |
| `apps/core/management/commands/seed_inicial.py` | Dados de demonstração |
| `apps/core/management/commands/seed_massivo.py` | Volume para gráficos (`scripts/seed_massivo.py`) |
| `apps/core/management/commands/backup_banco.py` | Backup pela linha de comando |
| `apps/core/management/commands/purgar_retencao.py` | Retenção LGPD |
