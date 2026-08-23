from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_alter_usuariobase_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ambulante",
            name="codigo_qr_code",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="ambulante",
            name="data_nasc",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="ambulante",
            name="escolaridade",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AlterField(
            model_name="ambulante",
            name="tipo_atuacao",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
