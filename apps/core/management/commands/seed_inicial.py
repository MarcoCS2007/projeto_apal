import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.espacos.models import Endereco, EstruturaTrabalho, PontoOcupacao
from apps.licenciamento.models import CategoriaProduto
from apps.usuarios.lgpd import BASE_LEGAL_LGPD
from apps.usuarios.models import (
    Administrador,
    Ambulante,
    ConfiguracaoSeguranca,
    Fiscal,
    Gestor,
)

SENHA_ADMIN = "admin123"
SENHA_GESTOR = "gestor123"
SENHA_FISCAL = "fiscal123"
SENHA_AMBULANTE = "amb123"

# CPFs fictícios com dígitos verificadores válidos (mesma regra do cadastro).
CPF_ADMIN = "52998224725"
CPF_GESTOR = "11144477735"
CPF_GESTOR_MARIANA = "20030040094"
CPF_GESTOR_ROBERTO = "30040050009"
CPF_FISCAL = "12345678909"
CPF_FISCAL_CARLOS = "40050060007"
CPF_FISCAL_ANA = "50060070013"
CPF_FISCAL_PAULO = "60070080020"
CPF_AMBULANTE = "10020030088"
CPF_MARIA = "39053344705"
CPF_ANTONIO = "80190200391"
CPF_RAIMUNDA = "90200310402"
CPF_CARLOS_AMB = "10203040570"
CPF_FATIMA = "20304050601"
CPF_LUCIANA = "30405060726"
CPF_PEDRO = "70080090036"
# Ambulantes extras só para densidade do mapa demo (VC-BA).
CPF_MAPA_1 = "40506070859"
CPF_MAPA_2 = "50607080981"
CPF_MAPA_3 = "60708090176"
CPF_MAPA_4 = "70809010224"

CATEGORIAS = (
    {
        "nome_categoria": "Alimentos Manipulados",
        "descricao": "Alimentos preparados na hora.",
        "exige_laudo_sanitario": True,
        "fator_financeiro": Decimal("15.00"),
    },
    {
        "nome_categoria": "Artesanato",
        "descricao": "Produtos artesanais e manuais.",
        "exige_laudo_sanitario": False,
        "fator_financeiro": Decimal("10.00"),
    },
    {
        "nome_categoria": "Lanches e Salgados",
        "descricao": "Cachorro-quente, tapioca, milho e similares.",
        "exige_laudo_sanitario": True,
        "fator_financeiro": Decimal("12.50"),
    },
    {
        "nome_categoria": "Vestuário e Acessórios",
        "descricao": "Roupas, bolsas, bijuterias e calçados.",
        "exige_laudo_sanitario": False,
        "fator_financeiro": Decimal("20.00"),
    },
    {
        "nome_categoria": "Bebidas e Água de Coco",
        "descricao": "Bebidas não alcoólicas e água de coco.",
        "exige_laudo_sanitario": True,
        "fator_financeiro": Decimal("8.00"),
    },
    {
        "nome_categoria": "Frutas e Hortifruti",
        "descricao": "Frutas, verduras e legumes in natura.",
        "exige_laudo_sanitario": False,
        "fator_financeiro": Decimal("5.00"),
    },
)

PONTOS = (
    {
        "nome_identificacao": "Praça Central",
        "logradouro": "Praça Barão do Rio Branco",
        "bairro": "Centro",
        "metragem_maxima": Decimal("10.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8661,-40.8390",
    },
    {
        "nome_identificacao": "Calçadão Comercial",
        "logradouro": "Rua Coronel Gugé",
        "bairro": "Centro",
        "metragem_maxima": Decimal("15.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8654,-40.8378",
    },
    {
        "nome_identificacao": "Praça 9 de Novembro",
        "logradouro": "Praça 9 de Novembro",
        "bairro": "Centro",
        "metragem_maxima": Decimal("8.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8648,-40.8365",
    },
    {
        "nome_identificacao": "Terminal Lauro de Freitas",
        "logradouro": "Av. Lauro de Freitas",
        "bairro": "Candeias",
        "metragem_maxima": Decimal("12.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8612,-40.8441",
    },
    {
        "nome_identificacao": "Feira do Bairro Brasil",
        "logradouro": "Rua do Comércio Popular",
        "bairro": "Brasil",
        "metragem_maxima": Decimal("6.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8702,-40.8520",
    },
    {
        "nome_identificacao": "Região do Ceasa",
        "logradouro": "Av. Presidente Dutra",
        "bairro": "Jurema",
        "metragem_maxima": Decimal("20.00"),
        "status_ocupacao": "Livre",
        "coordenadas": "-14.8580,-40.8288",
    },
)

GESTORES = (
    {
        "cpf": CPF_GESTOR,
        "email": "gestor@apal.com",
        "password": SENHA_GESTOR,
        "nome": "Gestor",
        "sobrenome": "Posturas",
        "telefone_whatsapp": "77988001001",
        "matricula_funcional": "GES-001",
        "cargo": "Gestor de Posturas",
        "departamento": "SESEP - Serviços Públicos (Posturas)",
        "is_staff": True,
    },
    {
        "cpf": CPF_GESTOR_MARIANA,
        "email": "mariana.almeida@pmvc.ba.gov.br",
        "password": SENHA_GESTOR,
        "nome": "Mariana",
        "sobrenome": "Almeida",
        "telefone_whatsapp": "77988001002",
        "matricula_funcional": "GES-002",
        "cargo": "Coordenadora de Licenciamento",
        "departamento": "Vigilância Sanitária Municipal",
        "is_staff": True,
    },
    {
        "cpf": CPF_GESTOR_ROBERTO,
        "email": "roberto.lima@pmvc.ba.gov.br",
        "password": SENHA_GESTOR,
        "nome": "Roberto",
        "sobrenome": "Lima",
        "telefone_whatsapp": "77988001003",
        "matricula_funcional": "GES-003",
        "cargo": "Analista Tributário",
        "departamento": "SEFIN - Secretaria de Finanças / Tributos",
        "is_staff": True,
    },
)

FISCAIS = (
    {
        "cpf": CPF_FISCAL,
        "email": "fiscal@apal.com",
        "password": SENHA_FISCAL,
        "nome": "Fiscal",
        "sobrenome": "Centro",
        "telefone_whatsapp": "77988002001",
        "matricula_funcional": "FIS-001",
        "zona_atuacao_primaria": "Centro Comercial / Praça 9 de Novembro",
        "is_staff": True,
    },
    {
        "cpf": CPF_FISCAL_CARLOS,
        "email": "carlos.moreira@pmvc.ba.gov.br",
        "password": SENHA_FISCAL,
        "nome": "Carlos Eduardo",
        "sobrenome": "Moreira",
        "telefone_whatsapp": "77988002002",
        "matricula_funcional": "FIS-002",
        "zona_atuacao_primaria": "Feira do Bairro Brasil / Zona Oeste",
        "is_staff": True,
    },
    {
        "cpf": CPF_FISCAL_ANA,
        "email": "ana.souza@pmvc.ba.gov.br",
        "password": SENHA_FISCAL,
        "nome": "Ana Paula",
        "sobrenome": "Souza",
        "telefone_whatsapp": "77988002003",
        "matricula_funcional": "FIS-003",
        "zona_atuacao_primaria": "Terminal Lauro de Freitas",
        "is_staff": True,
    },
    {
        "cpf": CPF_FISCAL_PAULO,
        "email": "paulo.itinerante@pmvc.ba.gov.br",
        "password": SENHA_FISCAL,
        "nome": "Paulo",
        "sobrenome": "Nogueira",
        "telefone_whatsapp": "77988002004",
        "matricula_funcional": "FIS-004",
        "zona_atuacao_primaria": "Fiscalização Itinerante / Eventos",
        "is_staff": True,
    },
)


class Command(BaseCommand):
    help = "Carga inicial de dados fictícios para testes locais."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga inicial de dados...")
        self._administrador()
        self._gestores()
        self._fiscais()
        pontos = self._pontos()
        self._categorias()
        self._catalogo_infracoes()
        self._ambulantes(pontos)
        ConfiguracaoSeguranca.carregar()
        self.stdout.write("Configuração global de segurança disponível.")
        self._abrir_fila_analise()
        self._licencas_mapa_demo(pontos)
        self._rota_demo()
        self._resumo()
        self.stdout.write(
            self.style.SUCCESS("Carga inicial (seeds) finalizada com sucesso!")
        )

    def _criar(self, model, cpf, defaults, senha, criar):
        email = defaults.get("email")
        from django.db.models import Q

        from apps.usuarios.models import UsuarioBase

        existente = UsuarioBase.objects.filter(Q(cpf=cpf) | Q(email=email)).first()
        if existente:
            self.stdout.write(f"Usuário com CPF {cpf} ou email {email} já existe.")
            return model.objects.filter(pk=existente.pk).first() or existente
        usuario = criar(cpf=cpf, password=senha, **defaults)
        self.stdout.write(
            self.style.SUCCESS(f"{model.__name__} {usuario.nome} criado.")
        )
        return usuario

    def _dados_lgpd(self):
        """Mesmo registro do cadastro web (checkbox + art. 7º, III)."""
        return {
            "aceite_lgpd": True,
            "aceite_lgpd_em": timezone.now(),
            "base_legal_lgpd": BASE_LEGAL_LGPD,
        }

    def _garantir_aceite_lgpd(self, ambulante):
        """Preenche o aceite em contas antigas do seed, sem sobrescrever data já gravada."""
        if (
            ambulante.aceite_lgpd
            and ambulante.aceite_lgpd_em
            and ambulante.base_legal_lgpd
        ):
            return ambulante
        ambulante.aceite_lgpd = True
        if not ambulante.aceite_lgpd_em:
            ambulante.aceite_lgpd_em = timezone.now()
        if not ambulante.base_legal_lgpd:
            ambulante.base_legal_lgpd = BASE_LEGAL_LGPD
        ambulante.save(
            update_fields=[
                "aceite_lgpd",
                "aceite_lgpd_em",
                "base_legal_lgpd",
                "atualizado_em",
            ]
        )
        return ambulante

    def _administrador(self):
        from apps.usuarios.models import UsuarioBase

        if (
            UsuarioBase.objects.filter(cpf=CPF_ADMIN).exists()
            or UsuarioBase.objects.filter(email="admin@apal.com").exists()
        ):
            self.stdout.write("Administrador Master já existe.")
            return
        Administrador.objects.create_superuser(
            cpf=CPF_ADMIN,
            email="admin@apal.com",
            password="admin123",
            nome="Admin",
            sobrenome="Master",
            telefone_whatsapp="77988000000",
            acesso_master=True,
            acesso_painel_tecnico=True,
        )
        self.stdout.write(self.style.SUCCESS("Administrador Master criado."))

    def _gestores(self):
        for dados in GESTORES:
            payload = dict(dados)
            cpf = payload.pop("cpf")
            senha = payload.pop("password")
            self._criar(Gestor, cpf, payload, senha, Gestor.objects.create_user)

    def _fiscais(self):
        for dados in FISCAIS:
            payload = dict(dados)
            cpf = payload.pop("cpf")
            senha = payload.pop("password")
            self._criar(Fiscal, cpf, payload, senha, Fiscal.objects.create_user)

    def _categorias(self):
        for dados in CATEGORIAS:
            defaults = dict(dados)
            nome_categoria = defaults.pop("nome_categoria")
            _obj, created = CategoriaProduto.objects.update_or_create(
                nome_categoria=nome_categoria,
                defaults=defaults,
            )
            nome = nome_categoria
            if created:
                self.stdout.write(self.style.SUCCESS(f"Categoria '{nome}' criada."))
            else:
                self.stdout.write(f"Categoria '{nome}' já existe e foi atualizada.")

    def _pontos(self):
        pontos = {}
        for dados in PONTOS:
            obj, created = PontoOcupacao.objects.get_or_create(
                nome_identificacao=dados["nome_identificacao"],
                defaults=dados,
            )
            if not created and (
                not obj.coordenadas or obj.coordenadas != dados.get("coordenadas")
            ):
                obj.coordenadas = dados.get("coordenadas") or ""
                obj.logradouro = dados["logradouro"]
                obj.bairro = dados["bairro"]
                obj.save(
                    update_fields=[
                        "coordenadas",
                        "logradouro",
                        "bairro",
                        "atualizado_em",
                    ]
                )
            pontos[dados["nome_identificacao"]] = obj
            nome = dados["nome_identificacao"]
            if created:
                self.stdout.write(self.style.SUCCESS(f"Ponto '{nome}' criado."))
            else:
                self.stdout.write(f"Ponto '{nome}' já existe.")
        return pontos

    def _ambulantes(self, pontos):
        self._ambulante_joao()
        self._ambulante_completo(
            cpf=CPF_MARIA,
            email="maria.dores@email.com",
            nome="Maria",
            sobrenome="das Dores",
            telefone="77991001001",
            apelido="Tapioca da Maria",
            cnpj="12345678000190",
            tipo_atuacao="fixo",
            escolaridade="medio_completo",
            data_nasc=datetime.date(1984, 3, 12),
            nis="12345678901",
            ponto=pontos["Praça 9 de Novembro"],
            endereco={
                "cep": "45000-000",
                "logradouro": "Rua da Bandeira",
                "numero": "120",
                "bairro": "Centro",
                "cidade": "Vitória da Conquista",
                "estado_uf": "BA",
            },
            estrutura={
                "tipo_estrutura": "carrinho",
                "dimensoes_metragem": Decimal("2.50"),
                "descricao": "Tapioca, cuscuz e sucos naturais.",
            },
            extras={"razao_social": "Maria das Dores MEI", "sem_cnpj": False},
            genero="feminino",
            renda_mensal_estimada=Decimal("2200.00"),
            num_funcionarios=1,
        )
        self._ambulante_completo(
            cpf=CPF_ANTONIO,
            email="antonio.bispo@email.com",
            nome="Antônio",
            sobrenome="Bispo",
            telefone="77991001002",
            apelido="Banca do Bispo",
            cnpj=None,
            tipo_atuacao="fixo",
            escolaridade="fundamental_completo",
            data_nasc=datetime.date(1976, 7, 8),
            nis=None,
            ponto=pontos["Calçadão Comercial"],
            endereco={
                "cep": "45020-210",
                "logradouro": "Rua Grande",
                "numero": "45",
                "complemento": "Fundos",
                "bairro": "Centro",
                "cidade": "Planalto",
                "estado_uf": "BA",
            },
            estrutura={
                "tipo_estrutura": "banca",
                "dimensoes_metragem": Decimal("4.00"),
                "descricao": "Roupas e acessórios populares.",
            },
            extras={"sem_cnpj": True},
            genero="masculino",
            renda_mensal_estimada=Decimal("1800.00"),
            num_funcionarios=0,
        )
        self._ambulante_completo(
            cpf=CPF_RAIMUNDA,
            email="raimunda.alves@email.com",
            nome="Raimunda",
            sobrenome="Alves",
            telefone="77991001003",
            apelido="Food Truck da Dunda",
            cnpj="98765432000155",
            tipo_atuacao="movel",
            escolaridade="superior",
            data_nasc=datetime.date(1991, 11, 21),
            nis="10987654321",
            ponto=pontos["Terminal Lauro de Freitas"],
            endereco={
                "cep": "45028-000",
                "logradouro": "Av. Presidente Dutra",
                "numero": "890",
                "bairro": "Candeias",
                "cidade": "Vitória da Conquista",
                "estado_uf": "BA",
            },
            estrutura={
                "tipo_estrutura": "veiculo",
                "dimensoes_metragem": Decimal("10.00"),
                "descricao": "Lanches, hambúrguer e milho verde.",
            },
            extras={"razao_social": "Raimunda Alves Lanches ME", "sem_cnpj": False},
            genero="feminino",
            renda_mensal_estimada=Decimal("3500.00"),
            num_funcionarios=2,
        )
        self._ambulante_completo(
            cpf=CPF_CARLOS_AMB,
            email="carlos.feira@email.com",
            nome="Carlos",
            sobrenome="Ferreira",
            telefone="77991001004",
            apelido="Tabuleiro do Carlos",
            cnpj=None,
            tipo_atuacao="eventual",
            escolaridade="medio_incompleto",
            data_nasc=datetime.date(1988, 5, 2),
            nis="11223344556",
            ponto=pontos["Feira do Bairro Brasil"],
            endereco={
                "cep": "45051-000",
                "logradouro": "Rua São Jorge",
                "numero": "33",
                "bairro": "Brasil",
                "cidade": "Vitória da Conquista",
                "estado_uf": "BA",
            },
            estrutura={
                "tipo_estrutura": "tabuleiro",
                "dimensoes_metragem": Decimal("1.50"),
                "descricao": "Frutas da época e amendoim.",
            },
            extras={"sem_cnpj": True},
            genero="masculino",
            renda_mensal_estimada=Decimal("1200.00"),
            num_funcionarios=1,
        )
        self._ambulante_completo(
            cpf=CPF_FATIMA,
            email="fatima.inativa@email.com",
            nome="Fátima",
            sobrenome="Oliveira",
            telefone="77991001005",
            apelido="Água de Coco da Fátima",
            cnpj=None,
            tipo_atuacao="fixo",
            escolaridade="fundamental_incompleto",
            data_nasc=datetime.date(1972, 9, 30),
            nis=None,
            ponto=pontos["Praça Central"],
            endereco={
                "cep": "45000-100",
                "logradouro": "Av. Bartolomeu de Gusmão",
                "numero": "10",
                "bairro": "Centro",
                "cidade": "Vitória da Conquista",
                "estado_uf": "BA",
            },
            estrutura={
                "tipo_estrutura": "carrinho",
                "dimensoes_metragem": Decimal("2.00"),
                "descricao": "Água de coco e sucos.",
            },
            extras={"sem_cnpj": True},
            ativo=False,
            genero="feminino",
            renda_mensal_estimada=Decimal("900.00"),
            num_funcionarios=0,
        )
        self._ambulante_conta(
            cpf=CPF_LUCIANA,
            email="luciana.rocha@email.com",
            nome="Luciana",
            sobrenome="Rocha",
            telefone="77991001006",
        )
        luciana = Ambulante.objects.filter(cpf=CPF_LUCIANA).first()
        if luciana and not luciana.ponto_pretendido_id:
            luciana.ponto_pretendido = pontos["Calçadão Comercial"]
            luciana.save(update_fields=["ponto_pretendido", "atualizado_em"])
        self._ambulante_parcial(
            cpf=CPF_PEDRO,
            email="pedro.nunes@email.com",
            nome="Pedro",
            sobrenome="Nunes",
            telefone="77991001007",
            ponto=pontos["Região do Ceasa"],
        )

    def _ambulante_joao(self):
        from django.db.models import Q

        from apps.usuarios.models import UsuarioBase

        existente = Ambulante.objects.filter(
            Q(cpf=CPF_AMBULANTE) | Q(email="ambulante@apal.com")
        ).first()
        if (
            not existente
            and UsuarioBase.objects.filter(
                Q(cpf=CPF_AMBULANTE) | Q(email="ambulante@apal.com")
            ).exists()
        ):
            self.stdout.write(
                "Usuário com email ambulante@apal.com ou CPF já existe mas não é ambulante."
            )
            return
        if existente:
            self._garantir_aceite_lgpd(existente)
            self.stdout.write(f"Ambulante {CPF_AMBULANTE} já existe.")
            return
        Ambulante.objects.create_user(
            cpf=CPF_AMBULANTE,
            email="ambulante@apal.com",
            password=SENHA_AMBULANTE,
            nome="João",
            sobrenome="Ambulante",
            telefone_whatsapp="77991000000",
            tipo_atuacao="Carrinho",
            codigo_qr_code="QR-001",
            data_nasc=datetime.date(1990, 1, 1),
            escolaridade="Ensino Médio",
            genero="masculino",
            pontuacao=100,
            **self._dados_lgpd(),
        )
        self.stdout.write(
            self.style.SUCCESS("Ambulante João criado (cadastro pendente).")
        )

    def _ambulante_conta(self, *, cpf, email, nome, sobrenome, telefone):
        from django.db.models import Q

        from apps.usuarios.models import UsuarioBase

        existente = Ambulante.objects.filter(Q(cpf=cpf) | Q(email=email)).first()
        if (
            not existente
            and UsuarioBase.objects.filter(Q(cpf=cpf) | Q(email=email)).exists()
        ):
            self.stdout.write(
                f"Usuário com email {email} ou CPF já existe mas não é ambulante."
            )
            return
        if existente:
            self._garantir_aceite_lgpd(existente)
            self.stdout.write(f"Ambulante {cpf} já existe.")
            return
        Ambulante.objects.create_user(
            cpf=cpf,
            email=email,
            password=SENHA_AMBULANTE,
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp=telefone,
            **self._dados_lgpd(),
        )
        self.stdout.write(self.style.SUCCESS(f"Ambulante {nome} criado (só a conta)."))

    def _ambulante_parcial(self, *, cpf, email, nome, sobrenome, telefone, ponto):
        from django.db.models import Q

        from apps.usuarios.models import UsuarioBase

        existente = Ambulante.objects.filter(Q(cpf=cpf) | Q(email=email)).first()
        if (
            not existente
            and UsuarioBase.objects.filter(Q(cpf=cpf) | Q(email=email)).exists()
        ):
            self.stdout.write(
                f"Usuário com email {email} ou CPF já existe mas não é ambulante."
            )
            return
        if existente:
            self._garantir_aceite_lgpd(existente)
            self.stdout.write(f"Ambulante {cpf} já existe.")
            return
        ambulante = Ambulante.objects.create_user(
            cpf=cpf,
            email=email,
            password=SENHA_AMBULANTE,
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp=telefone,
            data_nasc=datetime.date(1995, 4, 18),
            escolaridade="medio_completo",
            tipo_atuacao="movel",
            ponto_pretendido=ponto,
            pontuacao=80,
            **self._dados_lgpd(),
        )
        Endereco.objects.create(
            ambulante=ambulante,
            cep="45000-250",
            logradouro="Rua Ibitiara",
            numero="200",
            bairro="Recreio",
            cidade="Vitória da Conquista",
            estado_uf="BA",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Ambulante {nome} criado (dados + endereço, sem estrutura)."
            )
        )

    def _ambulante_completo(
        self,
        *,
        cpf,
        email,
        nome,
        sobrenome,
        telefone,
        apelido,
        cnpj,
        tipo_atuacao,
        escolaridade,
        data_nasc,
        nis,
        ponto,
        endereco,
        estrutura,
        extras,
        ativo=True,
        genero="nao_informado",
        renda_mensal_estimada=None,
        num_funcionarios=0,
    ):
        from django.db.models import Q

        from apps.usuarios.models import UsuarioBase

        existente = Ambulante.objects.filter(Q(cpf=cpf) | Q(email=email)).first()
        if (
            not existente
            and UsuarioBase.objects.filter(Q(cpf=cpf) | Q(email=email)).exists()
        ):
            self.stdout.write(
                f"Usuário com email {email} ou CPF já existe mas não é ambulante."
            )
            return
        if existente:
            self._garantir_aceite_lgpd(existente)
            campos = []
            if genero and existente.genero in ("", "nao_informado"):
                existente.genero = genero
                campos.append("genero")
            if (
                renda_mensal_estimada is not None
                and existente.renda_mensal_estimada is None
            ):
                existente.renda_mensal_estimada = renda_mensal_estimada
                campos.append("renda_mensal_estimada")
            if num_funcionarios and not existente.num_funcionarios:
                existente.num_funcionarios = num_funcionarios
                campos.append("num_funcionarios")
            if campos:
                existente.save(update_fields=campos + ["atualizado_em"])
            self.stdout.write(f"Ambulante {cpf} já existe.")
            return
        ambulante = Ambulante.objects.create_user(
            cpf=cpf,
            email=email,
            password=SENHA_AMBULANTE,
            nome=nome,
            sobrenome=sobrenome,
            telefone_whatsapp=telefone,
            apelido_nome_fantasia=apelido,
            cnpj=cnpj,
            tipo_atuacao=tipo_atuacao,
            escolaridade=escolaridade,
            data_nasc=data_nasc,
            nis=nis,
            genero=genero,
            renda_mensal_estimada=renda_mensal_estimada,
            num_funcionarios=num_funcionarios,
            ponto_pretendido=ponto,
            dados_complementares=extras,
            pontuacao=100 if ativo else 40,
            ativo=ativo,
            is_active=ativo,
            **self._dados_lgpd(),
        )
        Endereco.objects.create(ambulante=ambulante, **endereco)
        EstruturaTrabalho.objects.create(ambulante=ambulante, **estrutura)
        situacao = "completo" if ativo else "completo e inativo"
        self.stdout.write(self.style.SUCCESS(f"Ambulante {nome} criado ({situacao})."))

    def _abrir_fila_analise(self):
        from apps.licenciamento.models import CategoriaProduto
        from apps.licenciamento.services import abrir_requerimento

        mapa = {
            CPF_MARIA: "Lanches e Salgados",
            CPF_ANTONIO: "Vestuário e Acessórios",
            CPF_RAIMUNDA: "Alimentos Manipulados",
            CPF_CARLOS_AMB: "Frutas e Hortifruti",
        }
        for cpf, nome_categoria in mapa.items():
            ambulante = Ambulante.objects.filter(cpf=cpf, ativo=True).first()
            if not ambulante:
                continue
            categoria = CategoriaProduto.objects.filter(
                nome_categoria=nome_categoria
            ).first()
            licenca, criado = abrir_requerimento(ambulante, categoria=categoria)
            if criado:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Requerimento {licenca.protocolo} na fila ({ambulante.nome})."
                    )
                )
            elif licenca:
                self.stdout.write(
                    f"Requerimento {licenca.protocolo} já estava na fila."
                )

    def _licencas_mapa_demo(self, pontos):
        """Licenças ATIVAS extras para auras com volumes distintos no mapa demo.

        Vários alvarás no mesmo ponto são intencionais só para a demonstração
        visual (Praça Central “quente”); o fluxo real de emissão segue 1:1.
        """
        from datetime import timedelta

        from apps.core.qrcode import gerar_codigo_qr
        from apps.licenciamento.models import (
            CategoriaProduto,
            LicencaAlvara,
            StatusLicenca,
        )

        hoje = timezone.localdate()
        categoria = CategoriaProduto.objects.filter(ativo=True).first()
        extras = (
            {
                "cpf": CPF_MAPA_1,
                "email": "jose.mapa@email.com",
                "nome": "José",
                "sobrenome": "Santana",
                "telefone": "77991002001",
                "apelido": "Milho do Zé",
                "tipo_atuacao": "fixo",
                "ponto": pontos["Praça Central"],
                "categoria": "Lanches e Salgados",
            },
            {
                "cpf": CPF_MAPA_2,
                "email": "ana.mapa@email.com",
                "nome": "Ana",
                "sobrenome": "Pires",
                "telefone": "77991002002",
                "apelido": "Bijuterias da Ana",
                "tipo_atuacao": "fixo",
                "ponto": pontos["Praça Central"],
                "categoria": "Vestuário e Acessórios",
            },
            {
                "cpf": CPF_MAPA_3,
                "email": "bruno.mapa@email.com",
                "nome": "Bruno",
                "sobrenome": "Costa",
                "telefone": "77991002003",
                "apelido": "Sucos do Bruno",
                "tipo_atuacao": "fixo",
                "ponto": pontos["Praça Central"],
                "categoria": "Bebidas e Água de Coco",
            },
            {
                "cpf": CPF_MAPA_4,
                "email": "helena.mapa@email.com",
                "nome": "Helena",
                "sobrenome": "Dias",
                "telefone": "77991002004",
                "apelido": "Food Truck da Helena",
                "tipo_atuacao": "movel",
                "ponto": pontos["Terminal Lauro de Freitas"],
                "categoria": "Alimentos Manipulados",
            },
        )
        for item in extras:
            ponto = item["ponto"]
            amb = Ambulante.objects.filter(cpf=item["cpf"]).first()
            if amb is None:
                amb = Ambulante.objects.create_user(
                    cpf=item["cpf"],
                    email=item["email"],
                    password=SENHA_AMBULANTE,
                    nome=item["nome"],
                    sobrenome=item["sobrenome"],
                    telefone_whatsapp=item["telefone"],
                    apelido_nome_fantasia=item["apelido"],
                    tipo_atuacao=item["tipo_atuacao"],
                    escolaridade="medio_completo",
                    data_nasc=datetime.date(1985, 6, 15),
                    genero="nao_informado",
                    renda_mensal_estimada=Decimal("1500.00"),
                    ponto_pretendido=ponto,
                    pontuacao=100,
                    **self._dados_lgpd(),
                )
                Endereco.objects.create(
                    ambulante=amb,
                    cep="45000-000",
                    logradouro="Rua Demo Mapa",
                    numero="1",
                    bairro=ponto.bairro,
                    cidade="Vitória da Conquista",
                    estado_uf="BA",
                )
                EstruturaTrabalho.objects.create(
                    ambulante=amb,
                    tipo_estrutura="carrinho",
                    dimensoes_metragem=Decimal("2.00"),
                    descricao="Estrutura seed mapa demo.",
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Ambulante mapa demo {item['nome']} criado.")
                )
            else:
                if amb.ponto_pretendido_id != ponto.pk:
                    amb.ponto_pretendido = ponto
                    amb.save(update_fields=["ponto_pretendido", "atualizado_em"])

            if LicencaAlvara.objects.filter(
                ambulante=amb, status=StatusLicenca.ATIVO, ponto_ocupacao=ponto
            ).exists():
                continue

            cat = CategoriaProduto.objects.filter(
                nome_categoria=item["categoria"]
            ).first() or categoria
            estrutura = amb.estruturas.order_by("id").first()
            licenca = LicencaAlvara.objects.create(
                ambulante=amb,
                estrutura_trabalho=estrutura,
                ponto_ocupacao=ponto,
                categoria_produto=cat,
                status=StatusLicenca.ATIVO,
                data_emissao=hoje,
                data_vencimento=hoje + timedelta(days=365),
                numero_licenca=f"ALV-MAPA-{amb.pk}",
                taxa_paga=True,
            )
            ponto.ocupar()
            if not amb.codigo_qr_code:
                amb.codigo_qr_code = gerar_codigo_qr(licenca)
                amb.save(update_fields=["codigo_qr_code", "atualizado_em"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Licença ATIVA mapa demo {licenca.numero_licenca} "
                    f"em {ponto.nome_identificacao}."
                )
            )

        # Ceasa fica sem alvará ativo (só Pedro pretendido) para aura azul no filtro.
        ceasa = pontos["Região do Ceasa"]
        if not LicencaAlvara.objects.filter(
            ponto_ocupacao=ceasa, status=StatusLicenca.ATIVO
        ).exists():
            if ceasa.status_ocupacao != "Livre":
                ceasa.status_ocupacao = "Livre"
                ceasa.save(update_fields=["status_ocupacao", "atualizado_em"])

    def _rota_demo(self):
        from apps.fiscalizacao.models import RotaFiscal
        from apps.fiscalizacao.services_rotas import criar_rota

        fiscal = Fiscal.objects.filter(cpf=CPF_FISCAL).first()
        gestor = Gestor.objects.filter(cpf=CPF_GESTOR).first()
        if fiscal is None:
            self.stdout.write("Fiscal seed não encontrado; rota demo ignorada.")
            return
        if RotaFiscal.objects.filter(titulo="Ronda Centro — demonstração").exists():
            self.stdout.write("Rota demo já existe.")
            return
        cpfs = (CPF_MARIA, CPF_ANTONIO, CPF_RAIMUNDA, CPF_CARLOS_AMB)
        ids = list(
            Ambulante.objects.filter(cpf__in=cpfs, ativo=True).values_list(
                "pk", flat=True
            )
        )
        if len(ids) < 2:
            self.stdout.write("Ambulantes insuficientes para rota demo.")
            return
        rota = criar_rota(
            gestor,
            fiscal,
            "Ronda Centro — demonstração",
            ids[:4],
            data_prevista=timezone.localdate(),
            observacoes="Rota seed para demonstração: visite os pontos do Centro e registre cada parada.",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Rota demo #{rota.pk} criada com {rota.total_paradas} paradas."
            )
        )

    def _resumo(self):
        self.stdout.write("")
        self.stdout.write("Contas para teste (todas idempotentes):")
        self.stdout.write(f"  Admin     CPF {CPF_ADMIN}  senha admin123")
        self.stdout.write(f"  Gestor    CPF {CPF_GESTOR}  senha gestor123")
        self.stdout.write(f"  Fiscal    CPF {CPF_FISCAL}  senha fiscal123")
        self.stdout.write(
            f"  Ambulante CPF {CPF_AMBULANTE}  senha amb123  (cadastro pendente)"
        )
        self.stdout.write("  Demais gestores/fiscais usam gestor123 / fiscal123.")
        self.stdout.write("  Demais ambulantes usam amb123.")
        self.stdout.write(
            "  Completos: Maria das Dores, Antônio Bispo, Raimunda Alves, Carlos Ferreira."
        )
        self.stdout.write(
            "  Só conta: Luciana Rocha (pretendido Calçadão). "
            "Parcial: Pedro Nunes (Ceasa). Inativa: Fátima Oliveira."
        )
        self.stdout.write(
            "  Mapa demo: 3 alvaras na Praca Central + 1 no Terminal "
            "(filtro ativos -> aura vermelha no Centro)."
        )
        self.stdout.write(
            "  Rota demo: fiscal@apal.com -> /fiscal/rotas/ (Ronda Centro)."
        )

    def _catalogo_infracoes(self):
        from apps.fiscalizacao.models import CatalogoInfracao

        infracoes = [
            ("Venda fora do horário regulamentado", "Leve", 5),
            ("Ausência de identificação (Crachá)", "Leve", 5),
            ("Metragem acima do permitido", "Media", 20),
            ("Sujeira no local de trabalho", "Media", 20),
            ("Falta de laudo sanitário", "Grave", 50),
            ("Venda de produto ilícito", "Gravissima", 100),
        ]
        for desc, gravidade, pontos in infracoes:
            CatalogoInfracao.objects.get_or_create(
                descricao=desc,
                defaults={"gravidade": gravidade, "pontos_desconto": pontos},
            )
        self.stdout.write(self.style.SUCCESS("Catálogo de Infrações criado."))
