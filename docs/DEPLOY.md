# Guia de Deploy - Projeto APAL 🚀

Este documento detalha o passo a passo para colocar a API do Projeto APAL em produção. A nossa infraestrutura foi desenhada seguindo os princípios do *12-Factor App*, o que significa que a transição de desenvolvimento para produção ocorre primariamente através da troca das variáveis de ambiente e da substituição do servidor web.

## 1. O que precisa ser modificado e por quê?

O servidor de desenvolvimento do Django (`manage.py runserver`) é excelente para testes locais, mas **nunca deve ser usado em produção**. Ele não foi feito para lidar com múltiplas requisições simultâneas e não possui proteções de segurança avançadas.

Para o deploy, precisaremos de três ajustes principais:
1. **Servidor WSGI:** Trocar o `runserver` pelo `gunicorn` (um servidor Python focado em performance e concorrência).
2. **Arquivos Estáticos:** O Django não serve arquivos estáticos (CSS do admin, imagens) com o `DEBUG=False`. Usaremos a biblioteca `whitenoise` para que a própria aplicação sirva esses arquivos de forma otimizada.
3. **Isolamento de Ambiente:** Criar o arquivo `.env.prod` e um arquivo de orquestração Docker específico para produção.

---

## 2. Preparando o Código para Produção

`gunicorn` e `whitenoise` já estão em `requirements/base.txt` (Django 5+). O `STATIC_ROOT` (`staticfiles/`) e o middleware do WhiteNoise já estão em `config/settings/base.py`. Os apps instalados são só `core`, `usuarios`, `licenciamento`, `espacos`, `fiscalizacao` e `assistente`.

Com `DEBUG=False` o Django **não** serve CSS/JS pelo `runserver`. Depois de `pip install -r requirements/base.txt`:

```bash
python3 manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

O WhiteNoise passa a servir `/static/` a partir de `STATIC_ROOT`. Não use `runserver` em produção.

---

## 3. Configurando o Ambiente de Produção

No seu servidor (VPS, AWS, DigitalOcean, etc), clone o repositório do projeto.

### Passo 3.1: Criar o `.env.prod`

Dentro da pasta `.envs/`, crie o arquivo `.env.prod`. **Nunca comite este arquivo no GitHub**.

```env
# Define que o Django deve usar o arquivo prod.py
DJANGO_SETTINGS_MODULE=config.settings.prod

# Segurança
SECRET_KEY=gere-uma-chave-longa-e-complexa-aqui-sem-espacos
ALLOWED_HOSTS=api.projetoapal.com.br,127.0.0.1,localhost

# Banco de Dados (PostgreSQL)
POSTGRES_DB=apal_prod_db
POSTGRES_USER=apal_prod_user
POSTGRES_PASSWORD=senha_super_segura_aqui
POSTGRES_HOST=db
POSTGRES_PORT=5432

```

### Passo 3.2: O Docker Compose de Produção

Crie um arquivo chamado `docker-compose.prod.yml` na raiz do projeto. Ele é quase idêntico ao de desenvolvimento, mas usa o `gunicorn` e aponta para o `.env.prod`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    env_file:
      - .envs/.env.prod
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d$$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: always

  web:
    build:
      context: .
      dockerfile: ./infra/Dockerfile
      args:
        REQUIREMENTS_FILE: base.txt
    # TROCAMOS O RUNSERVER PELO GUNICORN
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
    ports:
      - "8000:8000"
    env_file:
      - .envs/.env.prod
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data_prod:

```

*Nota sobre os Workers:* A regra geral para o `--workers` no Gunicorn é `(2 x Núcleos de CPU) + 1`. Se o seu servidor tem 1 CPU, use 3 workers.

---

## 4. Executando o Deploy (Usando o Makefile)

Para que o nosso `Makefile` encontre o arquivo de produção sem precisarmos reescrever as regras, vamos definir uma variável de ambiente no servidor. Isso diz ao Docker para usar o `.prod.yml` por padrão.

No terminal do servidor, execute:

```bash
export COMPOSE_FILE=docker-compose.prod.yml

```

Agora, você pode utilizar a automação do projeto:

**1. Subir os contêineres:**
*(Como queremos rodar o servidor em segundo plano e nosso `make up` não possui a flag `-d`, utilizamos o comando do Docker Compose)*

```bash
docker compose up -d --build

```

**2. Rodar as migrações no banco de dados de produção:**

```bash
make migrate

```

**3. Coletar os arquivos estáticos (para o painel de Admin funcionar):**
*(Utilizando a regra de comando livre do nosso Makefile)*

```bash
make cmd="python manage.py collectstatic --no-input"

```

**4. Criar o primeiro superusuário do sistema:**

```bash
make createsuperuser

```

---

## 5. Comandos Úteis de Manutenção

Como a variável `COMPOSE_FILE` já está ativa na sessão do seu servidor, os comandos nativos de infraestrutura do Docker ficam muito mais curtos (não sendo necessário adicionar ao Makefile):

* **Ver os logs da aplicação em tempo real:**
`docker compose logs -f web`
* **Reiniciar a API (após mudar algo no código):**
`docker compose restart web`
* **Derrubar o ambiente completamente:**
`docker compose down`
* **Backup e restauração:** ver `docs/BACKUP.md` (`manage.py backup_banco` e `loaddata` / `pg_restore`).
* **Dados de demonstração (não use em produção real):** `python manage.py seed_inicial`. Volume extra para gráficos: `seed_massivo`.
