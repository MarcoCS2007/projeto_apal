from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".envs" / ".env.dev")

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web", "0.0.0.0"]
