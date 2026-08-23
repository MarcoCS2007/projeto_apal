from django.core.management.base import BaseCommand

from apps.usuarios.score import verificar_recuperacao_mensal


class Command(BaseCommand):
    help = "Executa o gatilho de recuperação de score (+2 pontos) para ambulantes sem infração nos últimos 30 dias."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando rotina de recuperação de score...")
        afetados = verificar_recuperacao_mensal()
        self.stdout.write(
            self.style.SUCCESS(
                f"Sucesso! O score de {afetados} ambulante(s) foi recuperado nesta execução."
            )
        )
