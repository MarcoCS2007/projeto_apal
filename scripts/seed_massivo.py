import os
import random
import sys
from datetime import timedelta
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django

django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from faker import Faker

from apps.core.qrcode import gerar_codigo_qr
from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import OcorrenciaInspecao, TipoOcorrencia
from apps.licenciamento.models import (
    CategoriaProduto,
    EscalaTrabalho,
    LicencaAlvara,
    StatusLicenca,
)
from apps.usuarios.models import Ambulante, Fiscal

fake = Faker("pt_BR")


def run():
    print("Iniciando seed massivo...")

    # Categorias
    print("Criando categorias...")
    categorias_dados = [
        {"nome": "Alimentos Rápidos", "fator": "15.00"},
        {"nome": "Artesanato Local", "fator": "10.00"},
        {"nome": "Bebidas Frias", "fator": "12.00"},
        {"nome": "Vestuário Pop", "fator": "20.00"},
        {"nome": "Hortifruti", "fator": "5.00"},
        {"nome": "Eletrônicos e Acessórios", "fator": "25.00"},
    ]
    categorias = []
    for c in categorias_dados:
        cat, _ = CategoriaProduto.objects.get_or_create(
            nome_categoria=c["nome"], defaults={"fator_financeiro": Decimal(c["fator"])}
        )
        categorias.append(cat)

    # Pontos de Ocupação
    print("Criando pontos de ocupação...")
    pontos = []
    for i in range(15):
        ponto, _ = PontoOcupacao.objects.get_or_create(
            nome_identificacao=f"Ponto Massivo {i+1}",
            defaults={
                "logradouro": fake.street_name(),
                "bairro": fake.bairro(),
                "metragem_maxima": Decimal(random.uniform(5.0, 30.0)).quantize(
                    Decimal("0.00")
                ),
                "status_ocupacao": StatusOcupacao.LIVRE,
            },
        )
        pontos.append(ponto)

    # Fiscais (para ocorrências)
    fiscal = Fiscal.objects.first()
    if not fiscal:
        fiscal = Fiscal.objects.create_user(
            cpf="99999999999",
            password="123",
            email="fiscal_massivo@apal.com",
            nome="Fiscal",
            sobrenome="Massivo",
        )

    print("Criando 500 ambulantes...")
    escolaridades = [
        "fundamental_incompleto",
        "fundamental_completo",
        "medio_incompleto",
        "medio_completo",
        "superior",
        "analfabeto",
    ]
    tipos_atuacao = ["fixo", "movel", "eventual"]

    password_hash = make_password("senha123")
    hoje = timezone.localtime()

    ambulantes_objs = []
    cpfs_gerados = set()

    # Pre-generate CPFs to avoid collision
    while len(cpfs_gerados) < 500:
        cpfs_gerados.add(fake.cpf().replace(".", "").replace("-", ""))

    for cpf in cpfs_gerados:
        data_nasc = fake.date_of_birth(minimum_age=18, maximum_age=70)

        amb = Ambulante(
            cpf=cpf,
            email=f"{cpf}@faker.com",
            password=password_hash,
            nome=fake.first_name(),
            sobrenome=fake.last_name(),
            telefone_whatsapp=fake.cellphone_number()
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", ""),
            data_nasc=data_nasc,
            escolaridade=random.choice(escolaridades),
            tipo_atuacao=random.choice(tipos_atuacao),
            nis=fake.numerify("###########") if random.random() < 0.45 else None,
            genero=random.choice(
                [
                    "feminino",
                    "masculino",
                    "feminino",
                    "masculino",
                    "outro",
                    "nao_informado",
                ]
            ),
            renda_mensal_estimada=Decimal(random.randint(800, 6500)),
            num_funcionarios=random.randint(0, 4),
            aceite_lgpd=True,
            aceite_lgpd_em=hoje,
            base_legal_lgpd="Seed Massivo",
            pontuacao=100,
            is_active=True,
        )
        ambulantes_objs.append(amb)

    from django.db import transaction

    with transaction.atomic():
        for amb in ambulantes_objs:
            amb.save()

    ambulantes_criados = list(Ambulante.objects.filter(email__endswith="@faker.com"))

    print("Criando endereços, estruturas e licenças...")
    enderecos_objs = []
    estruturas_objs = []
    licencas_objs = []

    cidades_externas = ["Planalto", "Brumado", "Poções", "Cândido Sales"]

    for amb in ambulantes_criados:
        # Endereço (20% fora de Conquista)
        cidade = "Vitória da Conquista"
        if random.random() < 0.2:
            cidade = random.choice(cidades_externas)

        enderecos_objs.append(
            Endereco(
                ambulante=amb,
                cep=fake.postcode()[:8] if fake.postcode() else "45000000",
                logradouro=fake.street_name()[:250],
                numero=fake.building_number()[:20],
                bairro=fake.bairro()[:100],
                cidade=cidade,
                estado_uf="BA",
            )
        )

        # Estrutura
        estruturas_objs.append(
            EstruturaTrabalho(
                ambulante=amb,
                tipo_estrutura=random.choice(
                    ["carrinho", "banca", "tabuleiro", "veiculo"]
                ),
                dimensoes_metragem=Decimal(random.uniform(2.0, 10.0)).quantize(
                    Decimal("0.00")
                ),
                descricao="Estrutura massiva",
            )
        )

        # Licença (espalhada nos últimos 24 meses)
        dias_atras = random.randint(1, 730)
        data_emissao = hoje - timedelta(days=dias_atras)
        data_vencimento = data_emissao + timedelta(days=365)

        status_lic = (
            StatusLicenca.ATIVO
            if data_vencimento.date() > hoje.date()
            else StatusLicenca.VENCIDO
        )

        cat = random.choice(categorias)
        metragem = Decimal(random.uniform(2.0, 10.0)).quantize(Decimal("0.00"))
        valor = round(metragem * cat.fator_financeiro, 2)

        licencas_objs.append(
            LicencaAlvara(
                ambulante=amb,
                categoria_produto=cat,
                ponto_ocupacao=random.choice(pontos),
                status=status_lic,
                data_emissao=data_emissao,
                data_vencimento=data_vencimento,
                valor_taxa=valor,
                taxa_paga=True,
                protocolo=f"REQ-M-{amb.pk}-{dias_atras}",
            )
        )

    Endereco.objects.bulk_create(enderecos_objs, ignore_conflicts=True)
    EstruturaTrabalho.objects.bulk_create(estruturas_objs, ignore_conflicts=True)
    LicencaAlvara.objects.bulk_create(licencas_objs, ignore_conflicts=True)

    licencas_criadas = list(
        LicencaAlvara.objects.filter(protocolo__startswith="REQ-M-")
    )

    print("Gerando escalas e ocorrências...")
    escalas_objs = []
    ocorrencias_objs = []

    turnos = [
        ("06:00", "12:00"),  # Manhã
        ("12:00", "18:00"),  # Tarde
        ("18:00", "23:59"),  # Noite
        ("08:00", "18:00"),  # Integral
    ]
    dias_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]

    for licenca in licencas_criadas:
        # Escalas
        turno_inicio, turno_fim = random.choice(turnos)
        qtd_dias = random.randint(3, 7)
        dias_escolhidos = random.sample(dias_semana, qtd_dias)

        for dia in dias_escolhidos:
            escalas_objs.append(
                EscalaTrabalho(
                    licenca_alvara=licenca,
                    dia_semana=dia,
                    horario_inicio=turno_inicio,
                    horario_termino=turno_fim,
                )
            )

        # Ocorrências (Gamificação Extrema)
        amb = licenca.ambulante
        # 70% Diamante (0 ocorrências)
        # 20% Prata/Ouro (1-2 ocorrências leves)
        # 10% Infrator (3-6 ocorrências severas)
        perfil = random.random()
        qtd_ocorrencias = 0
        tipos = []

        if perfil > 0.9:  # 10% Infratores
            qtd_ocorrencias = random.randint(3, 6)
            tipos = [
                TipoOcorrencia.MULTA,
                TipoOcorrencia.APREENSAO,
                TipoOcorrencia.SEM_LICENCA,
                TipoOcorrencia.OUTRO,
            ]
            amb.pontuacao = max(0, amb.pontuacao - (qtd_ocorrencias * 20))
        elif perfil > 0.7:  # 20% Leves
            qtd_ocorrencias = random.randint(1, 2)
            tipos = [
                TipoOcorrencia.ADVERTENCIA,
                TipoOcorrencia.FORA_HORARIO,
                TipoOcorrencia.FORA_PONTO,
            ]
            amb.pontuacao = max(0, amb.pontuacao - (qtd_ocorrencias * 10))

        amb.save(update_fields=["pontuacao"])

        from apps.fiscalizacao.models import CatalogoInfracao

        catalogo = list(CatalogoInfracao.objects.all())

        for _ in range(qtd_ocorrencias):
            infracao_escolhida = random.choice(catalogo) if catalogo else None
            ocorrencias_objs.append(
                OcorrenciaInspecao(
                    fiscal=fiscal,
                    ambulante=amb,
                    tipo_ocorrencia=random.choice(tipos),
                    descricao="Infração gerada no seed massivo.",
                    local_ocorrencia=(
                        licenca.ponto_ocupacao.nome_identificacao
                        if licenca.ponto_ocupacao
                        else "Rua"
                    ),
                    infracao=infracao_escolhida,
                    status_gestor="Aprovada",
                    data_ocorrencia=hoje - timedelta(days=random.randint(1, 300)),
                )
            )

    EscalaTrabalho.objects.bulk_create(escalas_objs, ignore_conflicts=True)
    OcorrenciaInspecao.objects.bulk_create(ocorrencias_objs, ignore_conflicts=True)

    # Atualizar QR Codes e data de criacao das ocorrencias (auto_now_add issue)
    print("Atualizando QR Codes e datas de ocorrência...")

    # Em bulk_create, o auto_now_add sobrescreve a data. Vamos corrigir no banco.
    for oc in OcorrenciaInspecao.objects.filter(
        descricao="Infração gerada no seed massivo."
    ):
        dias_atras = random.randint(1, 300)
        oc.criado_em = hoje - timedelta(days=dias_atras)
        oc.save(update_fields=["criado_em"])

    for licenca in licencas_criadas:
        amb = licenca.ambulante
        if licenca.status == StatusLicenca.ATIVO:
            licenca.numero_licenca = f"ALV-M-{licenca.pk}"
            licenca.save(update_fields=["numero_licenca"])
            amb.codigo_qr_code = gerar_codigo_qr(licenca)
            amb.save(update_fields=["codigo_qr_code"])

    print("Seed massivo concluído com sucesso!")


if __name__ == "__main__":
    run()
