#!/usr/bin/env python
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    base_dir = Path(__file__).resolve().parent
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    env_file = ".env.prod" if settings_module.endswith(".prod") else ".env.dev"
    env_path = base_dir / ".envs" / env_file
    if env_path.exists():
        load_dotenv(env_path)

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
