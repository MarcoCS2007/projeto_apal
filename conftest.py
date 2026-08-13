from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    env_path = Path(__file__).resolve().parent / ".envs" / ".env.dev"
    if env_path.exists():
        load_dotenv(env_path)
