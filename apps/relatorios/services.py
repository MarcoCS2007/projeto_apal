from collections import Counter, defaultdict

from django.db.models import Avg, Case, CharField, Count, Q, Sum, Value, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone

from apps.espacos.models import Endereco
from apps.fiscalizacao.models import OcorrenciaInspecao
from apps.licenciamento.models import LicencaAlvara, StatusLicenca
from apps.usuarios.models import Ambulante, Genero

from .filters import _faixa_etaria, _grupo_escolaridade, _idade


def _percentual(parte, total):
    if not total:
        return 0.0
    return round((parte / total) * 100, 1)


# A. Indicadores de Dados Únicos
def get_distribuicao_etaria(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    idades = Counter()
    hoje = timezone.localdate()

    # Buscando apenas data_nasc é mais performático que trazer a model inteira
    for row in qs.values("data_nasc"):
        _, rotulo = _faixa_etaria(_idade(row["data_nasc"], hoje))
        idades[rotulo] += 1

    return [{"faixa": rotulo, "total": total} for rotulo, total in idades.items()]


def get_distribuicao_genero(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = qs.values("genero").annotate(total=Count("id")).order_by("-total")
    mapa_genero = dict(Genero.choices)

    return [
        {
            "genero": mapa_genero.get(row["genero"], row["genero"] or "Não informado"),
            "total": row["total"],
        }
        for row in agrupado
    ]


def get_grau_instrucao(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = qs.values("escolaridade").annotate(total=Count("id")).order_by("-total")
    instrucao = Counter()
    for row in agrupado:
        grupo = _grupo_escolaridade(row["escolaridade"])
        instrucao[grupo] += row["total"]

    total_geral = sum(instrucao.values())
    return [
        {"escolaridade": k, "total": v, "percentual": _percentual(v, total_geral)}
        for k, v in instrucao.items()
    ]


def get_vulnerabilidade_social(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    total = qs.count()
    com_nis = qs.exclude(Q(nis__isnull=True) | Q(nis__exact="")).count()

    return {
        "com_nis": com_nis,
        "sem_nis": total - com_nis,
        "percentual_vulnerabilidade": _percentual(com_nis, total),
    }


def get_estimativa_renda(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = (
        LicencaAlvara.objects.filter(ambulante__in=qs, categoria_produto__isnull=False)
        .values("categoria_produto__nome_categoria")
        .annotate(renda_media=Avg("ambulante__renda_mensal_estimada"))
        .order_by("-renda_media")
    )

    return [
        {
            "categoria": row["categoria_produto__nome_categoria"],
            "renda_media": round(row["renda_media"], 2) if row["renda_media"] else 0,
        }
        for row in agrupado
    ]


def get_empregos_indiretos(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    resultado = qs.aggregate(total=Sum("num_funcionarios"))
    return resultado["total"] or 0


# B. Cruzamentos Estratégicos
def get_vulnerabilidade_vs_conformidade(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = (
        qs.annotate(
            tem_nis=Case(
                When(Q(nis__isnull=False) & ~Q(nis__exact=""), then=Value("Com NIS")),
                default=Value("Sem NIS"),
                output_field=CharField(),
            )
        )
        .values("tem_nis", "escolaridade")
        .annotate(
            media_score=Avg("pontuacao"),
            total_ocorrencias=Count("ocorrencias_recebidas"),
        )
        .order_by("tem_nis", "escolaridade")
    )

    return [
        {
            "grupo": f"{row['tem_nis']} - {_grupo_escolaridade(row['escolaridade'])}",
            "media_score": round(row["media_score"], 1) if row["media_score"] else 0,
            "ocorrencias": row["total_ocorrencias"],
        }
        for row in agrupado
    ]


def get_perfil_empreendedor_vs_nicho(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    # Agrupamos via python para a idade e misturamos com dados da licença
    licencas = (
        LicencaAlvara.objects.filter(ambulante__in=qs)
        .select_related("ambulante", "categoria_produto")
        .prefetch_related("ambulante__estruturas")
    )

    nicho_map = defaultdict(lambda: {"idade": Counter(), "genero": Counter()})

    hoje = timezone.localdate()
    mapa_genero = dict(Genero.choices)

    for licenca in licencas:
        categoria = (
            licenca.categoria_produto.nome_categoria
            if licenca.categoria_produto
            else "Sem Categoria"
        )
        amb = licenca.ambulante

        _, rotulo_idade = _faixa_etaria(_idade(amb.data_nasc, hoje))
        genero_rotulo = mapa_genero.get(amb.genero, amb.genero or "Não informado")

        estrutura = amb.estruturas.first()
        tipo_estrutura = estrutura.tipo_estrutura if estrutura else "Sem Estrutura"

        chave_completa = f"{categoria} | {tipo_estrutura}"

        nicho_map[chave_completa]["idade"][rotulo_idade] += 1
        nicho_map[chave_completa]["genero"][genero_rotulo] += 1

    # Converter para formato amigável
    resultado = []
    for nicho, stats in nicho_map.items():
        resultado.append(
            {
                "nicho": nicho,
                "idades": dict(stats["idade"]),
                "generos": dict(stats["genero"]),
            }
        )
    return resultado


def get_geracao_emprego_localizacao(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = (
        LicencaAlvara.objects.filter(
            ambulante__in=qs,
            ponto_ocupacao__isnull=False,
            categoria_produto__isnull=False,
        )
        .values("categoria_produto__nome_categoria", "ponto_ocupacao__bairro")
        .annotate(total_empregos=Sum("ambulante__num_funcionarios"))
        .filter(total_empregos__gt=0)
        .order_by("-total_empregos")
    )

    return [
        {
            "categoria": row["categoria_produto__nome_categoria"],
            "bairro": row["ponto_ocupacao__bairro"],
            "empregos": row["total_empregos"],
        }
        for row in agrupado
    ]


def get_mobilidade_urbana(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    enderecos = {
        row["ambulante_id"]: row["bairro"]
        for row in Endereco.objects.filter(ambulante__in=qs).values(
            "ambulante_id", "bairro"
        )
    }
    pontos = {
        row["ambulante_id"]: row["ponto_ocupacao__bairro"]
        for row in LicencaAlvara.objects.filter(
            ambulante__in=qs, ponto_ocupacao__isnull=False
        ).values("ambulante_id", "ponto_ocupacao__bairro")
    }

    matriz = defaultdict(int)
    for amb_id in qs.values_list("pk", flat=True):
        bairro_residencia = enderecos.get(amb_id, "Não informado")
        bairro_trabalho = pontos.get(amb_id, "Não informado")
        matriz[(bairro_residencia, bairro_trabalho)] += 1

    return [
        {"residencia": res, "trabalho": trab, "total": count}
        for (res, trab), count in sorted(matriz.items(), key=lambda item: -item[1])
    ]


def get_impacto_itinerante(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    # Consideramos CIDADE_SEDE = "Vitória da Conquista" (ou usar do ambiente)
    CIDADE_SEDE = "Vitória da Conquista"

    amb_ids_fora = (
        Endereco.objects.filter(ambulante__in=qs)
        .exclude(cidade__icontains=CIDADE_SEDE)
        .values_list("ambulante_id", flat=True)
    )

    ocorrencias_fora = (
        OcorrenciaInspecao.objects.filter(ambulante_id__in=amb_ids_fora)
        .values("tipo_ocorrencia")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    return [
        {"infracao": row["tipo_ocorrencia"], "total": row["total"]}
        for row in ocorrencias_fora
    ]


def get_evolucao_regularizacao(qs=None):
    if qs is None:
        qs = Ambulante.objects.all()

    agrupado = (
        LicencaAlvara.objects.filter(
            ambulante__in=qs, status=StatusLicenca.ATIVO, data_emissao__isnull=False
        )
        .annotate(
            ano_emissao=ExtractYear("data_emissao"),
            mes_emissao=ExtractMonth("data_emissao"),
        )
        .values("ano_emissao", "mes_emissao", "ambulante__tipo_atuacao")
        .annotate(total=Count("id"))
        .order_by("ano_emissao", "mes_emissao")
    )

    resultado = defaultdict(lambda: {"fixo": 0, "movel": 0, "eventual": 0})
    for row in agrupado:
        chave = f"{row['mes_emissao']:02d}/{row['ano_emissao']}"
        tipo = row["ambulante__tipo_atuacao"] or "indefinido"
        if "fixo" in tipo.lower():
            resultado[chave]["fixo"] += row["total"]
        elif "movel" in tipo.lower() or "móvel" in tipo.lower():
            resultado[chave]["movel"] += row["total"]
        else:
            resultado[chave]["eventual"] += row["total"]

    return [
        {
            "periodo": p,
            "fixo": vals["fixo"],
            "movel": vals["movel"],
            "eventual": vals["eventual"],
        }
        for p, vals in resultado.items()
    ]
