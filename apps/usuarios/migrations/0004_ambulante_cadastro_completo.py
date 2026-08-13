from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("espacos", "0004_alter_endereco_id_alter_estruturatrabalho_id_and_more"),
        ("usuarios", "0003_ambulante_conta_inicial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ambulante",
            name="dados_complementares",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="ambulante",
            name="ponto_pretendido",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ambulantes_interessados",
                to="espacos.pontoocupacao",
            ),
        ),
    ]
