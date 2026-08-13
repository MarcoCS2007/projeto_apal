from django.core.management.base import BaseCommand

from scripts.seed_massivo import run


class Command(BaseCommand):
    help = "Gera um volume massivo de dados para testes nos gráficos e relatórios."

    def handle(self, *args, **options):
        run()
