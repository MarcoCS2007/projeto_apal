# 8. Guia do iniciante

Como usar este repositório no primeiro dia e nos primeiros PRs.

## 8.1 Antes de escrever código

1. Suba o projeto ([README da raiz](../../README.md)): Docker, `.envs/.env.dev`, `migrate`, `seed_inicial`.
2. Entre com as contas seed (Master `00000000000`, gestor `11111111111`, fiscal `22222222222`, ambulante `33333333333`).
3. Percorra o ciclo com a mão: completar cadastro → triagem → deferir → taxa → emitir → credencial → `/fiscal/` → ocorrência → dossiê/score.
4. Leia os capítulos 3–6 com o editor aberto no trecho citado. O 7 é o ciclo inteiro; use a tabela de sintomas no final quando algo “não acontecer”.

## 8.2 “Quero alterar X” → abra Y

| Quero… | Abra primeiro | Depois |
| --- | --- | --- |
| Mudar um texto/botão da tela | `templates/...` | CSS em `static/css/style.css` se for visual |
| Mudar quem pode ver um menu | `templates/gestor/_nav.html` + `permissoes.py` | Matriz no Master |
| Travar uma tela por perfil | Mixin em `usuarios/views.py` | `RequerModuloMixin` se for módulo da matriz |
| Mudar regra de alvará/docs/taxa | `apps/licenciamento/services.py` | Testes `test_emissao.py`, `test_alvara.py` |
| Mudar leitura de QR / auto | `apps/fiscalizacao/services.py` | `test_campo.py`, `test_auditoria.py` |
| Mudar pontos do score | `PONTOS` em `usuarios/score.py` | `test_score.py` |
| Nova pergunta do assistente | `BASE_CONHECIMENTO` em `core/ia.py` | `assistente/tests.py` |
| Novo campo no cadastro do ambulante | `forms_cadastro.py` + model/migração | Wizard web **e** `usuarios/api.py` |
| Novo ponto/categoria no seed | `seed_inicial.py` | Rode o comando de novo (idempotente) |
| Novo endpoint JSON | `api.py` + `urls.py` do app | Chame o **service** já existente; documente em `docs/API-MOVEL.md` |
| Nova página HTML | `views.py` + `urls_web.py` + template `extends "base.html"` | `{% url %}` e mixin de acesso |
| Esquema do banco | `models.py` → `makemigrations` → `migrate` | Nunca edite migração antiga já compartilhada |
| Login / JWT | `backends.py`, `serializers.py`, `authentication.py` | `docs/API-AUTENTICACAO.md` |

## 8.3 Checklist de um PR pequeno

1. A regra nova está no **service** (ou no form), não copiada na view e na API.
2. Template novo estende `base.html` e usa `{% url %}` / `{% static %}`.
3. View autenticada tem mixin de perfil (e módulo, se for backoffice).
4. Há teste que quebra se alguém reverter a regra.
5. `make precommit` e `make test` (ou equivalentes) passam.
6. Não commitar `.env`, chaves, `media/`, `__pycache__`.

## 8.4 Como o Django “acha” as coisas (lembrete)

```text
URL no browser
  → config/urls.py (include)
    → apps/<app>/urls_web.py   nome="..."
      → Classe View
        → get/post → form.is_valid() → service() → model.save()
        → render(template, context)
          → HTML sai com links {% url %} que fecham o ciclo
```

`reverse("ambulante_alvara")` no Python = `{% url 'ambulante_alvara' %}` no HTML = o `name=` da rota.

## 8.5 Glossário rápido

| Termo no código | Significado humano |
| --- | --- |
| Requerimento | `LicencaAlvara` ainda sem número `ALV-` (status de fila) |
| Alvará | A mesma linha, já emitida (`numero_licenca` + Ativo) |
| Protocolo | `REQ-2026-0003` |
| Credencial | Tela/PNG do crachá com QR |
| HMAC / `codigo_qr_code` | Hash estável, não um UUID aleatório |
| DAM | Taxa municipal simulada (R$ 120) |
| MTI | Herança de usuário em várias tabelas |
| Soft-delete | `ativo=False` em vez de apagar a linha |
| HTMX | Troca um pedaço de HTML sem recarregar a página |
| Seed | Dados fictícios para desenvolver |
| Context processor | Variáveis injetadas em todos os templates (`pode`, `user`) |
| CBV | Class-based view (`LoginView`, `TemplateView`, `View`) |

## 8.6 Onde pedir ajuda no próprio repo

- Comportamento de um **módulo** (botões, URLs de uso): `docs/USUARIOS.md`, `LICENCIAMENTO.md`, etc.
- **Contrato do app**: `docs/API-MOVEL.md`
- **Deploy / dump**: `docs/DEPLOY.md`, `docs/BACKUP.md`
- **Por que a ordem das features é essa**: `contexto/ORDEM_DE_IMPLANTACAO.md`

Se a dúvida for “por que o código fez isso?”, abra o [capítulo 6](06-funcoes-reutilizadas.md) (algoritmo) e o [capítulo 7](07-fluxos.md) (a mesma regra no clique do usuário). Não procure só o nome do arquivo: siga os `if` da função.
