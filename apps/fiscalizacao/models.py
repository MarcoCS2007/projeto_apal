from django.db import models
from django.utils import timezone

from apps.core.models import ModeloBase


class TipoOcorrencia(models.TextChoices):
    ADVERTENCIA = "Advertência", "Advertência"
    MULTA = "Multa", "Multa"
    APREENSAO = "Apreensão", "Apreensão"
    FORA_PONTO = "Irregularidade de ponto", "Irregularidade de ponto"
    FORA_HORARIO = "Irregularidade de horário", "Irregularidade de horário"
    SEM_LICENCA = "Comércio sem licença válida", "Comércio sem licença válida"
    SEM_CREDENCIAL = "Falta de credencial", "Falta de credencial"
    OUTRO = "Outra irregularidade", "Outra irregularidade"


class StatusOcorrencia(models.TextChoices):
    REGISTRADA = "Registrada", "Registrada"
    EM_ANALISE = "Em análise", "Em análise"
    PROCEDENTE = "Procedente", "Procedente"
    IMPROCEDENTE = "Improcedente", "Improcedente"
    CONVERTIDA_MULTA = "Convertida em multa", "Convertida em multa"


TIPO_POR_MOTIVO = {
    "fora_horario": TipoOcorrencia.FORA_HORARIO,
    "suspenso": TipoOcorrencia.SEM_LICENCA,
    "vencido": TipoOcorrencia.SEM_LICENCA,
    "adulterado": TipoOcorrencia.SEM_CREDENCIAL,
    "invalido": TipoOcorrencia.SEM_LICENCA,
}


class CatalogoInfracao(ModeloBase):
    GRAVIDADE_CHOICES = (
        ("LEVE", "Leve"),
        ("MEDIA", "Média"),
        ("GRAVE", "Grave"),
        ("GRAVISSIMA", "Gravíssima"),
    )
    descricao = models.CharField(max_length=255)
    gravidade = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES)
    pontos_desconto = models.IntegerField()

    class Meta:
        verbose_name = "Catálogo de Infração"
        verbose_name_plural = "Catálogos de Infrações"

    def __str__(self):
        return f"{self.descricao} - {self.get_gravidade_display()}"


class OcorrenciaInspecao(ModeloBase):
    STATUS_GESTOR_CHOICES = (
        ("PENDENTE", "Pendente"),
        ("APROVADA", "Aprovada"),
        ("REJEITADA", "Rejeitada"),
    )

    fiscal = models.ForeignKey(
        "usuarios.Fiscal",
        on_delete=models.CASCADE,
        related_name="ocorrencias_registradas",
    )
    ambulante = models.ForeignKey(
        "usuarios.Ambulante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ocorrencias_recebidas",
    )
    tipo_ocorrencia = models.CharField(max_length=100, choices=TipoOcorrencia.choices)
    descricao = models.TextField()
    local_ocorrencia = models.CharField(max_length=255, blank=True, default="")
    evidencia_foto = models.ImageField(
        upload_to="fiscalizacao/ocorrencias/", null=True, blank=True
    )
    status_ocorrencia = models.CharField(
        max_length=50,
        choices=StatusOcorrencia.choices,
        default=StatusOcorrencia.REGISTRADA,
    )
    infracao = models.ForeignKey(
        "CatalogoInfracao", on_delete=models.SET_NULL, null=True, blank=True
    )
    status_gestor = models.CharField(
        max_length=20, choices=STATUS_GESTOR_CHOICES, default="PENDENTE"
    )
    data_ocorrencia = models.DateTimeField(
        "Data e Hora da Ocorrência", default=timezone.now
    )

    class Meta:
        verbose_name = "Ocorrência de Inspeção"
        verbose_name_plural = "Ocorrências de Inspeção"

    def __str__(self):
        alvo = self.ambulante or "não identificado"
        return f"{self.tipo_ocorrencia} - {alvo}"

    @property
    def classe_badge(self):
        if self.status_ocorrencia == StatusOcorrencia.IMPROCEDENTE:
            return "success"
        if self.status_ocorrencia in (
            StatusOcorrencia.PROCEDENTE,
            StatusOcorrencia.CONVERTIDA_MULTA,
        ):
            return "danger"
        if self.status_ocorrencia == StatusOcorrencia.EM_ANALISE:
            return "purple"
        return "warning"

    @property
    def status_final(self):
        return self.status_ocorrencia in (
            StatusOcorrencia.IMPROCEDENTE,
            StatusOcorrencia.CONVERTIDA_MULTA,
        )


class StatusRota(models.TextChoices):
    AGENDADA = "AGENDADA", "Agendada"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    CONCLUIDA = "CONCLUIDA", "Concluída"
    INCOMPLETA = "INCOMPLETA", "Incompleta"


class StatusParada(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    CONCLUIDA = "CONCLUIDA", "Concluída"
    PULADA = "PULADA", "Pulada"


class RotaFiscal(ModeloBase):
    titulo = models.CharField("Título", max_length=255)
    fiscal = models.ForeignKey(
        "usuarios.Fiscal",
        on_delete=models.CASCADE,
        related_name="rotas_atribuidas",
    )
    criado_por = models.ForeignKey(
        "usuarios.Gestor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rotas_criadas",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusRota.choices,
        default=StatusRota.AGENDADA,
    )
    data_prevista = models.DateField("Data prevista", null=True, blank=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    observacoes_gestor = models.TextField(blank=True, default="")
    relato_incompleta = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Rota de Fiscalização"
        verbose_name_plural = "Rotas de Fiscalização"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.titulo} — {self.fiscal}"

    @property
    def total_paradas(self):
        return self.paradas.count()

    @property
    def paradas_concluidas(self):
        return self.paradas.filter(status=StatusParada.CONCLUIDA).count()

    @property
    def tem_ocorrencias(self):
        return self.paradas.filter(visita__ocorrencia__isnull=False).exists()

    @property
    def classe_badge(self):
        return {
            StatusRota.AGENDADA: "warning",
            StatusRota.EM_ANDAMENTO: "purple",
            StatusRota.CONCLUIDA: "success",
            StatusRota.INCOMPLETA: "danger",
        }.get(self.status, "warning")


class ParadaRota(ModeloBase):
    rota = models.ForeignKey(
        RotaFiscal, on_delete=models.CASCADE, related_name="paradas"
    )
    ordem = models.PositiveIntegerField(default=1)
    ambulante = models.ForeignKey(
        "usuarios.Ambulante",
        on_delete=models.CASCADE,
        related_name="paradas_rota",
    )
    ponto = models.ForeignKey(
        "espacos.PontoOcupacao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paradas_rota",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusParada.choices,
        default=StatusParada.PENDENTE,
    )

    class Meta:
        verbose_name = "Parada de Rota"
        verbose_name_plural = "Paradas de Rota"
        ordering = ("ordem", "pk")
        unique_together = (("rota", "ordem"),)

    def __str__(self):
        return f"#{self.ordem} — {self.ambulante}"

    @property
    def coordenadas_lat_lng(self):
        raw = (self.ponto.coordenadas if self.ponto else "") or ""
        partes = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        if len(partes) >= 2:
            try:
                return float(partes[0]), float(partes[1])
            except ValueError:
                return None
        return None

    @property
    def endereco_completo(self):
        if not self.ponto:
            return "Endereço não cadastrado para esta parada."
        partes = [
            self.ponto.logradouro,
            self.ponto.bairro,
            "Vitória da Conquista - BA",
        ]
        return ", ".join(p for p in partes if p)

    @property
    def local_resumo(self):
        if not self.ponto:
            return "Sem ponto"
        return self.ponto.nome_identificacao


class RegistroVisita(ModeloBase):
    parada = models.OneToOneField(
        ParadaRota, on_delete=models.CASCADE, related_name="visita"
    )
    encontrou_ambulante = models.BooleanField(default=False)
    foi_recebido = models.BooleanField(default=False)
    ocorrencia = models.ForeignKey(
        OcorrenciaInspecao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitas_rota",
    )
    observacoes = models.TextField(blank=True, default="")
    registrado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Registro de Visita"
        verbose_name_plural = "Registros de Visita"

    def __str__(self):
        return f"Visita — {self.parada}"
