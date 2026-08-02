#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    # 1. Encontra o caminho da pasta raiz do projeto
    base_dir = Path(__file__).resolve().parent
    # 2. Aponta para o seu arquivo dentro da pasta .envs
    env_path = base_dir / ".envs" / ".env.dev"
    # 3. Carrega as variáveis para dentro do os.environ
    if env_path.exists():
        load_dotenv(env_path)
    # 4. Define o ambiente padrão

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
