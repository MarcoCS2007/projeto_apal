from django.core.management.base import BaseCommand

from apps.core.backup import gerar_backup, listar_backups


class Command(BaseCommand):
    help = "Gera um dump restaurável do banco em BACKUP_ROOT (JSON para loaddata)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--listar",
            action="store_true",
            help="Lista os backups já gravados, sem gerar um novo.",
        )

    def handle(self, *args, **options):
        if options["listar"]:
            itens = listar_backups()
            if not itens:
                self.stdout.write("Nenhum backup encontrado.")
                return
            for item in itens:
                self.stdout.write(
                    f"{item['nome']}  {item['modificado']:%Y-%m-%d %H:%M}  "
                    f"{item['tamanho']} bytes"
                )
            return
        caminho = gerar_backup()
        self.stdout.write(self.style.SUCCESS(f"Backup gravado em {caminho}"))
