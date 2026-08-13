"""Gera cópia restaurável do banco no diretório BACKUP_ROOT."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone


def diretorio_backups():
    pasta = Path(settings.BACKUP_ROOT)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def listar_backups():
    pasta = Path(settings.BACKUP_ROOT)
    if not pasta.exists():
        return []
    arquivos = sorted(
        pasta.glob("apal_backup_*"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    itens = []
    for arquivo in arquivos:
        itens.append(
            {
                "nome": arquivo.name,
                "caminho": arquivo,
                "tamanho": arquivo.stat().st_size,
                "modificado": datetime.fromtimestamp(
                    arquivo.stat().st_mtime, tz=timezone.get_current_timezone()
                ),
            }
        )
    return itens


def gerar_backup():
    """Grava dump JSON (loaddata) — portátil no Windows e no PostgreSQL."""
    pasta = diretorio_backups()
    carimbo = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    destino = pasta / f"apal_backup_{carimbo}.json"
    with destino.open("w", encoding="utf-8") as saida:
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "--exclude",
            "sessions.session",
            "--exclude",
            "admin.logentry",
            "--exclude",
            "contenttypes",
            "--exclude",
            "auth.permission",
            indent=2,
            stdout=saida,
        )
    return destino
