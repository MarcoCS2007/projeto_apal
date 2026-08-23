from django.db.models import Q

from apps.usuarios.models import Ambulante

PERIODO_INFRACOES_DIAS = 30


def _aplicar_origem(qs, origem, campo_ambulante="ambulante"):
    prefixo = f"{campo_ambulante}__" if campo_ambulante else ""
    if origem == "residentes":
        return qs.filter(**{f"{prefixo}tipo_atuacao": "fixo"})
    if origem == "itinerantes":
        return qs.filter(**{f"{prefixo}tipo_atuacao": "movel"})
    return qs


def _idade(nascimento, hoje=None):
    from django.utils import timezone

    if not nascimento:
        return None
    hoje = hoje or timezone.localdate()
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


GRUPO_ESCOLARIDADE = {
    "fundamental_incompleto": "Ensino Fundamental",
    "fundamental_completo": "Ensino Fundamental",
    "medio_incompleto": "Ensino Médio",
    "medio_completo": "Ensino Médio",
    "superior": "Ensino Superior",
    "analfabeto": "Sem instrução formal",
}


def _grupo_escolaridade(valor):
    if not valor:
        return "Não informado"
    if valor in GRUPO_ESCOLARIDADE:
        return GRUPO_ESCOLARIDADE[valor]
    texto = valor.lower()
    if "fundamental" in texto:
        return "Ensino Fundamental"
    if "médio" in texto or "medio" in texto:
        return "Ensino Médio"
    if "superior" in texto:
        return "Ensino Superior"
    if "analfabet" in texto:
        return "Sem instrução formal"
    return valor


FAIXAS_ETARIAS = (
    ("18-24", 18, 24, "18–24 anos"),
    ("25-45", 25, 45, "25–45 anos"),
    ("46-60", 46, 60, "46–60 anos"),
    ("60+", 61, 200, "60 anos ou mais"),
)


def _faixa_etaria(idade):
    if idade is None:
        return "", "Não informado"
    for chave, minimo, maximo, rotulo in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return chave, rotulo
    if idade < 18:
        return "ate_17", "Até 17 anos"
    return "60+", "60 anos ou mais"


def filtros_do_request(request):
    return {
        "bairro": request.GET.get("bairro", ""),
        "origem": request.GET.get("origem", ""),
        "periodo_dias": request.GET.get("periodo", PERIODO_INFRACOES_DIAS),
        "cidade": request.GET.get("cidade", ""),
        "genero": request.GET.get("genero", ""),
        "faixa_etaria": request.GET.get("faixa", ""),
        "escolaridade": request.GET.get("escolaridade", ""),
    }


def filtrar_ambulantes(
    bairro="",
    origem="",
    cidade="",
    genero="",
    faixa_etaria="",
    escolaridade="",
    **kwargs,
):
    qs = Ambulante.objects.all()
    if bairro:
        qs = qs.filter(
            Q(licencas__ponto_ocupacao__bairro__iexact=bairro)
            | Q(ponto_pretendido__bairro__iexact=bairro)
        ).distinct()
    qs = _aplicar_origem(qs, origem, campo_ambulante="")
    if cidade:
        qs = qs.filter(enderecos__cidade__iexact=cidade).distinct()
    if genero:
        qs = qs.filter(genero=genero)
    if escolaridade == "fundamental":
        qs = qs.filter(
            Q(escolaridade__icontains="fundamental")
            | Q(escolaridade__in=("fundamental_incompleto", "fundamental_completo"))
        )
    elif escolaridade == "medio":
        qs = qs.filter(
            Q(escolaridade__icontains="medio")
            | Q(escolaridade__icontains="médio")
            | Q(escolaridade__in=("medio_incompleto", "medio_completo"))
        )
    elif escolaridade == "superior":
        qs = qs.filter(escolaridade__icontains="superior")
    if faixa_etaria:
        ids = [
            ambulante.pk
            for ambulante in qs.only("pk", "data_nasc")
            if _faixa_etaria(_idade(ambulante.data_nasc))[0] == faixa_etaria
        ]
        qs = qs.filter(pk__in=ids or [0])
    return qs
