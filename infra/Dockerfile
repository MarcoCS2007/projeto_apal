FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app
ARG REQUIREMENTS_FILE=base.txt
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir uv && uv pip install --system -r requirements/${REQUIREMENTS_FILE}

COPY . /app/

# Cria um grupo e um usuário de sistema chamado 'app_user'
RUN addgroup --system app_group && adduser --system --group app_user

# Transfere a propriedade de todos os arquivos do projeto para o novo usuário
RUN chown -R app_user:app_group /app

# Avisa o Docker que, a partir desta linha, tudo roda com o usuário seguro
USER app_user

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]