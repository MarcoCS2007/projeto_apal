import datetime

from django.core.management.base import BaseCommand

from apps.espacos.models import PontoOcupacao
from apps.licenciamento.models import CategoriaProduto
from apps.usuarios.models import Administrador, Ambulante, Fiscal, Gestor


class Command(BaseCommand):
    help = "Carga inicial de dados (seeds) no banco de dados para testes."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga inicial de dados...")

        # 1. Administrador Master
        if not Administrador.objects.filter(cpf="00000000000").exists():
            Administrador.objects.create_superuser(
                cpf="00000000000",
                email="admin@apal.com",
                password="admin123",
                nome="Admin",
                sobrenome="Master",
                acesso_master=True,
            )
            self.stdout.write(
                self.style.SUCCESS("Administrador Master criado com sucesso.")
            )
        else:
            self.stdout.write("Administrador Master já existe.")

        # 2. Gestor
        if not Gestor.objects.filter(cpf="11111111111").exists():
            Gestor.objects.create_user(
                cpf="11111111111",
                email="gestor@apal.com",
                password="gestor123",
                nome="Gestor",
                sobrenome="Posturas",
                matricula_funcional="GES-001",
                cargo="Gestor de Posturas",
                departamento="Posturas",
                is_staff=True,
            )
            self.stdout.write(self.style.SUCCESS("Gestor criado com sucesso."))
        else:
            self.stdout.write("Gestor já existe.")

        # 3. Fiscal
        if not Fiscal.objects.filter(cpf="22222222222").exists():
            Fiscal.objects.create_user(
                cpf="22222222222",
                email="fiscal@apal.com",
                password="fiscal123",
                nome="Fiscal",
                sobrenome="Centro",
                matricula_funcional="FIS-001",
                zona_atuacao_primaria="Centro",
                is_staff=True,
            )
            self.stdout.write(self.style.SUCCESS("Fiscal criado com sucesso."))
        else:
            self.stdout.write("Fiscal já existe.")

        # 4. Ambulante
        if not Ambulante.objects.filter(cpf="33333333333").exists():
            Ambulante.objects.create_user(
                cpf="33333333333",
                email="ambulante@apal.com",
                password="amb123",
                nome="João",
                sobrenome="Ambulante",
                tipo_atuacao="Carrinho",
                codigo_qr_code="QR-001",
                data_nasc=datetime.date(1990, 1, 1),
                escolaridade="Ensino Médio",
                pontuacao=100,
            )
            self.stdout.write(self.style.SUCCESS("Ambulante criado com sucesso."))
        else:
            self.stdout.write("Ambulante já existe.")

        # 5. Categorias de Produto
        _categoria_1, created_1 = CategoriaProduto.objects.get_or_create(
            nome_categoria="Alimentos Manipulados",
            defaults={
                "descricao": "Alimentos preparados na hora.",
                "exige_laudo_sanitario": True,
            },
        )
        if created_1:
            self.stdout.write(
                self.style.SUCCESS(
                    "Categoria 'Alimentos Manipulados' criada com sucesso."
                )
            )
        else:
            self.stdout.write("Categoria 'Alimentos Manipulados' já existe.")

        _categoria_2, created_2 = CategoriaProduto.objects.get_or_create(
            nome_categoria="Artesanato",
            defaults={
                "descricao": "Produtos artesanais e manuais.",
                "exige_laudo_sanitario": False,
            },
        )
        if created_2:
            self.stdout.write(
                self.style.SUCCESS("Categoria 'Artesanato' criada com sucesso.")
            )
        else:
            self.stdout.write("Categoria 'Artesanato' já existe.")

        # 6. Pontos de Ocupação
        _ponto_1, created_p1 = PontoOcupacao.objects.get_or_create(
            nome_identificacao="Praça Central",
            defaults={
                "logradouro": "Praça Central",
                "bairro": "Centro",
                "metragem_maxima": 10.00,
                "status_ocupacao": "Livre",
            },
        )
        if created_p1:
            self.stdout.write(
                self.style.SUCCESS(
                    "Ponto de Ocupação 'Praça Central' criado com sucesso."
                )
            )
        else:
            self.stdout.write("Ponto de Ocupação 'Praça Central' já existe.")

        _ponto_2, created_p2 = PontoOcupacao.objects.get_or_create(
            nome_identificacao="Calçadão Comercial",
            defaults={
                "logradouro": "Rua do Comércio",
                "bairro": "Centro",
                "metragem_maxima": 15.00,
                "status_ocupacao": "Livre",
            },
        )
        if created_p2:
            self.stdout.write(
                self.style.SUCCESS(
                    "Ponto de Ocupação 'Calçadão Comercial' criado com sucesso."
                )
            )
        else:
            self.stdout.write("Ponto de Ocupação 'Calçadão Comercial' já existe.")

        self.stdout.write(
            self.style.SUCCESS("Carga inicial (seeds) finalizada com sucesso!")
        )
