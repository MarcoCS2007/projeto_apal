# 5. Front-end — como o HTML conversa com o Python

Não existe um `App.tsx`. Cada URL autenticada devolve HTML já preenchido. Entender o front é entender **herança de template** e **context**.

## 5.1 `extends` não copia o arquivo: ele preenche buracos

`templates/base.html` é o casco: `<head>`, skip link, header, widget de acessibilidade, `<main id="conteudo-principal">`, VLibras, `script.js`.

Uma página filha só declara blocos. O painel do ambulante começa assim:

```1:16:templates/ambulante/painel.html
{% extends "base.html" %}

{% block title %}Painel do Ambulante - APAL{% endblock %}

{% block header_nav %}
{% include "publico/_nav.html" with active="painel" %}
{% endblock %}

{% block hero %}
<section class="hero-section">
    ...
</section>
{% endblock %}
```

O Django:

1. Carrega `base.html`.
2. Troca `{% block title %}` pelo título desta página.
3. Troca `{% block header_nav %}` pelo include do menu (o `active` marca o item atual no `_nav`).
4. Injeta o hero acima do `<main>`.
5. O `{% block content %}` da filha cai **dentro** do `<main>` do base — por isso o skip link “Pular para o conteúdo” sempre acerta.

Se você criar um HTML solto sem `extends`, a página nasce sem acessibilidade, sem CSRF meta, sem CSS. Por isso a regra do item 16: tela nova = `extends "base.html"`.

`{% include %}` é outro mecanismo: cola um arquivo no lugar (nav, badge, ficha do fiscal). O `_` no nome (`_nav.html`) é convenção de “não é página, é pedaço”.

## 5.2 O template não busca no banco — ele lê nomes que a view inventou

`PainelAmbulanteView.get_context_data` (em `apps/usuarios/views.py`) coloca no dicionário, entre outros:

- `cadastro_completo` — resultado da propriedade do model
- `licenca` — retorno de `licenca_atual(...)`
- `documentos_rejeitados` / `documentos_pendentes` — querysets já filtrados
- chaves do `resumo_score` (faixa, pontos, dicas)

O template só pergunta o que já veio:

```27:31:templates/ambulante/painel.html
            {% if cadastro_completo %}
                Seu cadastro está preenchido. Acompanhe aqui o andamento da licença.
            {% else %}
                Complete seu cadastro para solicitar a licença. ...
            {% endif %}
```

E para a licença:

```73:79:templates/ambulante/painel.html
                        {% if licenca %}
                            protocolo {{ licenca.protocolo }} — {{ licenca.status }}.
                        {% elif tem_licenca %}
                            já existe um registro vinculado.
                        {% else %}
                            você ainda não possui licença.
```

`{{ licenca.protocolo }}` dispara a propriedade/campo do objeto Python que a view passou. Não há SQL escondido no `{% if %}` além do que o objeto já carregou. Se `licenca` for `None`, acessar `licenca.protocolo` quebraria — por isso o `if licenca` envolve o uso.

`{{ user.nome }}` vem do context processor `django.contrib.auth`: todo template autenticado tem `user`. Mixins já garantiram que esse `user` é ambulante nesta tela.

## 5.3 `{% url %}` e `{% static %}`

Nunca escreva `href="/ambulante/alvara/"` num template novo. O `name` da rota em `urls_web.py` é a fonte da verdade:

```django
<a href="{% url 'ambulante_alvara' %}">Meu Alvará</a>
```

Se a URL mudar e o `name` permanecer, o link continua. `{% static 'css/style.css' %}` aponta para `static/css/style.css` (em produção o WhiteNoise serve o arquivo coletado em `staticfiles/`).

## 5.4 Mensagens: o flash do Django

O `base.html` itera `messages`. A view faz `messages.success(request, "Cadastro concluído...")` **antes** do redirect. No GET seguinte o texto aparece uma vez no `<main>`. Por isso o wizard, depois de salvar, redireciona em vez de `render` de novo: o POST não deve ser o GET que o usuário recarrega.

Classes: `form-success` se a tag for `success`, senão `login-error`. Não é CSS de “login” só: reutilizam a classe de alerta vermelho.

## 5.5 `pode` no menu: context processor, não a view da página

`config/settings/base.py` registra `apps.usuarios.permissoes.permissoes_context`. Em **toda** request autenticada ou não, o template ganha `pode` e `recorte_sanitario`.

`pode` é um objeto `PodeModulos`: `pode.ocorrencias` vira `True/False` conforme `usuario_pode(user, "ocorrencias")`. O nav do gestor envolve cada item com `{% if pode.leitura_qr %}`. Desligar o módulo no Master some o link **e**, se a view tem `RequerModuloMixin`, quem colar a URL toma 403.

Administrador: `usuario_pode` retorna True imediatamente, então o Master vê todos os menus do gestor se entrar nessas telas.

## 5.6 HTMX no HTML

Na triagem, o botão Aprovar não submete o form da página inteira. Um elemento com `hx-post` + `hx-target` (no template) manda POST e substitui só a linha. O CSRF sai do meta ou do cookie que o `script.js` / HTMX lê.

Se HTMX falhar, a mesma view ainda redireciona (capítulo 4). O fragmento `_documento_row.html` recebe `documento` já com o novo `status_aprovacao` — por isso a linha muda de cor sem reload.

## 5.7 JS global não calcula alvará

`static/js/script.js` liga o painel de acessibilidade (classes no `body`), o menu mobile (`nav-open`) e leitura em voz. **Não** há `if (licenca.status === 'Ativo')` no JS de negócio.

Exceções pontuais no `{% block extra_js %}`: Chart.js no dashboard (recebe números **já calculados** em `indicadores_gerenciais`); câmera no painel do fiscal (só preenche o campo `q` / `qr` e submete). A classificação do QR continua sendo `inspecionar_qr` no servidor.

## 5.8 O que a pasta `front/` é

HTML estático de quando o layout foi desenhado. Servidor Django **não** aponta para ela. Copiar um trecho de lá para `templates/` exige: `extends`, `{% url %}`, `{% static %}`, e trocar dados mockados por `{{ variavel }}` do context.

Próximo capítulo: os algoritmos que view e template apenas disparam.
