# 2. Arquitetura: o caminho de uma request

Antes de models e services, precisa ficar claro **o que acontece quando alguém abre uma URL**. O APAL é um único processo Django. Não há um servidor Node separado. HTML e JSON saem do mesmo `manage.py`.

## O que está ligado

- **Python / Django 5+** processa HTTP, lê o Postgres pelo ORM e renderiza HTML.
- **PostgreSQL** guarda as linhas. Arquivos (foto, PDF) vão para a pasta `media/`; o banco só guarda o caminho.
- **DRF + SimpleJWT** devolvem JSON para o app móvel, com o mesmo usuário do site.
- **Templates + `static/`** são o front-end. A pasta `front/` é protótipo antigo: alterar lá **não** muda `localhost:8000`.

Docker (`docker-compose.yml`) sobe `db` (Postgres) e `web` (Django na porta 8000). Settings comuns estão em `config/settings/base.py`; `dev.py` liga `DEBUG=True` e lê `.envs/.env.dev`.

## O mapa de URLs não “acha” a tela sozinho

Toda request entra em `config/urls.py`. Esse arquivo **não** contém as views. Ele só diz *qual app* cuida de cada prefixo:

```23:37:config/urls.py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.usuarios.urls")),
    path("api/", include("apps.licenciamento.urls")),
    path("api/", include("apps.fiscalizacao.urls")),
    path("api/", include("apps.assistente.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.usuarios.urls_web")),
    path("", include("apps.licenciamento.urls_web")),
    path("", include("apps.espacos.urls_web")),
    path("", include("apps.assistente.urls_web")),
]

handler404 = "apps.core.views.pagina_nao_encontrada"
handler500 = "apps.core.views.erro_servidor"
```

Leia assim:

1. `/admin/` → admin do Django.
2. Qualquer coisa que comece com `/api/` → um dos `urls.py` (JSON). Vários `include` no mesmo prefixo: o Django tenta o primeiro, depois o segundo, até achar a rota.
3. O resto (`""`) → `urls_web.py` (HTML). A home (`/`) está em `apps.core.urls`; `/privacidade/` também; `/ambulante/` e `/ambulante/perfil/` estão em `usuarios.urls_web`; `/ambulante/alvara/` está em `licenciamento.urls_web`.

Rotas que não existem caem em `handler404`; falha não tratada, em `handler500` (templates `404.html` e `500.html`).

O `name=` de cada `path(...)` é o identificador que templates usam em `{% url 'ambulante_alvara' %}` e o Python usa em `reverse("ambulante_alvara")`. Se você mudar a URL e esquecer o `name`, os links quebram.

## Duas portas, um cérebro

| Porta | Arquivo típico | Resposta | Auth |
| --- | --- | --- | --- |
| Site | `urls_web.py` + `views.py` | HTML | cookie `sessionid` |
| App | `urls.py` + `api.py` | JSON | header `Authorization: Bearer …` |

As duas devem chamar a **mesma função** de `services.py`. Se a view HTML calcular “licença ativa” de um jeito e a API de outro, o ambulante vê um status no celular e outro no computador.

## O que o Django faz com um GET autenticado

Exemplo: o ambulante logado abre `/ambulante/`.

1. Middleware de sessão lê o cookie e preenche `request.user`.
2. `urls_web` aponta para `PainelAmbulanteView`.
3. A classe herda `LoginRequiredMixin` e `AcessoAmbulanteMixin`. Se não houver sessão, redireciona para `/entrar/`. Se houver sessão de gestor, o mixin manda para o backoffice (não mostra o painel do ambulante).
4. `get_context_data` busca o `Ambulante` com o **mesmo pk** do usuário logado, puxa a licença atual e o score, e monta um dicionário.
5. Django mistura esse dicionário com `templates/ambulante/painel.html`, que por sua vez puxa `base.html`.
6. O HTML sai com CSRF, CSS e o menu.

Nenhum JavaScript consultou o banco nesse fluxo. O browser só desenha o HTML pronto.

Um POST (enviar o wizard, deferir, lavrar auto) segue o mesmo caminho até a view; aí a view valida o `forms.Form` e só então chama o service, que faz `save()` no model.

## CSRF vs JWT (por que o app não manda csrfmiddlewaretoken)

O middleware `CsrfViewMiddleware` protege POST de formulário HTML contra site falso que usa o cookie da vítima. Por isso `base.html` coloca `<meta name="csrf-token">` e os forms têm `{% csrf_token %}`.

O JWT **não** usa cookie de sessão. Um atacante em outro site não consegue reaproveitar o Bearer que está no celular. Por isso as views de login/refresh da API desligam autenticação de sessão e aceitam JSON cru.

Não misture no cliente: o app nativo não deve mandar `sessionid`; o template não deve mandar Bearer no lugar do CSRF.

## Onde a regra pode morar (e onde não pode)

```text
Browser  →  View (quem é você? qual form?)  →  Service (a regra)  →  Model/SQL
                ↘ Template (só mostra o context)
```

- **View**: login, perfil, ler POST, escolher template ou `Response(...)`.
- **Form**: validar tipos, campos obrigatórios, arquivos.
- **Service**: “pode deferir?”, “gera o HMAC”, “soma score”.
- **Model**: persistência + propriedades que *descrevem* o registro (`qr_valido`, `cadastro_completo`).
- **Template**: `if` de apresentação, nunca `LicencaAlvara.objects.filter`.

O próximo capítulo abre os models e mostra como uma propriedade em Python vira decisão de tela.
