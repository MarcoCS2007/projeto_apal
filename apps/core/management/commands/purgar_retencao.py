from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assistente.models import LogAssistente
from apps.usuarios.models import ConfiguracaoSeguranca, LogAcessoDossie


class Command(BaseCommand):
    help = "Remove logs mais antigos que a política de retenção LGPD."

    def handle(self, *args, **options):
        config = ConfiguracaoSeguranca.carregar()
        limite = timezone.now() - timedelta(days=config.retencao_logs_meses * 30)
        ia = LogAssistente.objects.filter(criado_em__lt=limite).delete()[0]
        dossie = LogAcessoDossie.objects.filter(criado_em__lt=limite).delete()[0]
        self.stdout.write(
            self.style.SUCCESS(
                f"Retenção de {config.retencao_logs_meses} meses: "
                f"removidos {ia} logs de IA e {dossie} acessos a dossiê."
            )
        )
