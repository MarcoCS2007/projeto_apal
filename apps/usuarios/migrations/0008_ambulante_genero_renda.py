from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0007_ambulante_lgpd_log_dossie"),
    ]

    operations = [
        migrations.AddField(
            model_name="ambulante",
            name="genero",
            field=models.CharField(
                blank=True,
                choices=[
                    ("feminino", "Feminino"),
                    ("masculino", "Masculino"),
                    ("outro", "Outro"),
                    ("nao_informado", "Não informado"),
                ],
                default="nao_informado",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="ambulante",
            name="renda_estimada",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name="Renda mensal estimada (R$)",
            ),
        ),
    ]
