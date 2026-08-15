from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.core.models import ModeloBase
from apps.usuarios.seguranca import matriz_padrao


class UsuarioBaseManager(BaseUserManager):
    def create_user(self, cpf, email=None, password=None, **extra_fields):
        if not cpf:
            raise ValueError("O campo CPF é obrigatório.")
        email = self.normalize_email(email)
        user = self.model(cpf=cpf, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, cpf, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("acesso_master", True)
        extra_fields.setdefault("acesso_painel_tecnico", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário deve ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário deve ter is_superuser=True.")

        administrador = self.model._meta.apps.get_model("usuarios", "Administrador")
        return administrador.objects.create_user(cpf, email, password, **extra_fields)


class Perfil(models.TextChoices):
    AMBULANTE = "ambulante", "Ambulante"
    FISCAL = "fiscal", "Fiscal"
    GESTOR = "gestor", "Gestor"
    ADMINISTRADOR = "administrador", "Administrador"


class Genero(models.TextChoices):
    FEMININO = "feminino", "Feminino"
    MASCULINO = "masculino", "Masculino"
    OUTRO = "outro", "Outro"
    NAO_INFORMADO = "nao_informado", "Prefiro não informar"


class UsuarioBase(AbstractBaseUser, PermissionsMixin, ModeloBase):
    cpf = models.CharField(max_length=14, unique=True)
    nome = models.CharField(max_length=150)
    sobrenome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefone_whatsapp = models.CharField(max_length=20)
    telefone_2 = models.CharField(max_length=20, blank=True, null=True)
    foto = models.ImageField(upload_to="usuarios/fotos/", blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioBaseManager()

    USERNAME_FIELD = "cpf"
    REQUIRED_FIELDS = ("email", "nome", "sobrenome")

    def __str__(self):
        return f"{self.nome} {self.sobrenome} - {self.cpf}"

    @property
    def nome_completo(self):
        return f"{self.nome} {self.sobrenome}".strip()

    @property
    def iniciais(self):
        letras = [parte[0].upper() for parte in (self.nome, self.sobrenome) if parte]
        return "".join(letras[:2]) or "?"

    @property
    def cpf_formatado(self):
        digits = "".join(ch for ch in (self.cpf or "") if ch.isdigit())
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return self.cpf

    @property
    def cpf_mascarado(self):
        digits = "".join(ch for ch in (self.cpf or "") if ch.isdigit())
        if len(digits) == 11:
            return f"***.***.***-{digits[9:]}"
        return "***"

    @property
    def role(self):
        try:
            return Perfil(self.__class__.__name__.lower())
        except ValueError:
            pass
        for perfil in Perfil:
            if hasattr(self, perfil.value):
                return perfil
        if self.is_superuser:
            return Perfil.ADMINISTRADOR
        return None

    def garantir_perfil_administrador(self):
        administrador = Administrador.objects.filter(pk=self.pk).first()
        if administrador:
            return administrador
        administrador = Administrador(
            usuariobase_ptr_id=self.pk,
            acesso_master=True,
            acesso_painel_tecnico=True,
        )
        administrador.save_base(raw=True)
        return Administrador.objects.get(pk=self.pk)


class Ambulante(UsuarioBase):
    apelido_nome_fantasia = models.CharField(max_length=150, blank=True, null=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    tipo_atuacao = models.CharField(max_length=100, blank=True, default="")
    codigo_qr_code = models.CharField(
        max_length=255, unique=True, blank=True, null=True
    )
    data_nasc = models.DateField(blank=True, null=True)
    genero = models.CharField(
        max_length=20,
        choices=Genero.choices,
        default=Genero.NAO_INFORMADO,
        blank=True,
    )
    escolaridade = models.CharField(max_length=100, blank=True, default="")
    nis = models.CharField(max_length=20, blank=True, null=True)
    renda_mensal_estimada = models.DecimalField(
        "Renda mensal estimada (R$)",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    num_funcionarios = models.IntegerField(default=0)
    pontuacao = models.IntegerField(default=100)
    aceite_lgpd = models.BooleanField(default=False)
    aceite_lgpd_em = models.DateTimeField(null=True, blank=True)
    base_legal_lgpd = models.CharField(max_length=80, blank=True, default="")
    ponto_pretendido = models.ForeignKey(
        "espacos.PontoOcupacao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ambulantes_interessados",
    )
    dados_complementares = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.apelido_nome_fantasia or self.nome

    @property
    def cadastro_completo(self):
        estrutura = self.estruturas.order_by("id").first()
        tem_estrutura = bool(
            estrutura
            and estrutura.tipo_estrutura
            and estrutura.dimensoes_metragem
            and estrutura.dimensoes_metragem > 0
        )
        return bool(
            self.data_nasc
            and self.escolaridade
            and self.tipo_atuacao
            and self.enderecos.exists()
            and tem_estrutura
        )

    @property
    def situacao_conta(self):
        extras = self.dados_complementares or {}
        if extras.get("conta_cancelada"):
            return "cancelada"
        if not self.ativo or not self.is_active:
            return "suspensa"
        if self.cadastro_completo:
            return "completa"
        return "pendente"

    def aplicar_situacao_conta(self, situacao):
        extras = dict(self.dados_complementares or {})
        if situacao == "cancelada":
            extras["conta_cancelada"] = True
            self.ativo = False
            self.is_active = False
        elif situacao == "suspensa":
            extras.pop("conta_cancelada", None)
            extras["conta_suspensa"] = True
            self.ativo = False
            self.is_active = False
        else:
            extras.pop("conta_cancelada", None)
            extras.pop("conta_suspensa", None)
            self.ativo = True
            self.is_active = True
        self.dados_complementares = extras
        self.save(
            update_fields=[
                "ativo",
                "is_active",
                "dados_complementares",
                "atualizado_em",
            ]
        )


class TipoEventoScore(models.TextChoices):
    LICENCA_ATIVA = "licenca_ativa", "Licença em dia"
    RENOVACAO = "renovacao", "Renovação no prazo"
    OCORRENCIA_PROCEDENTE = "ocorrencia_procedente", "Ocorrência procedente"
    LICENCA_SUSPENSA = "licenca_suspensa", "Licença suspensa"
    LICENCA_CANCELADA = "licenca_cancelada", "Licença cancelada"


class EventoScore(ModeloBase):
    ambulante = models.ForeignKey(
        Ambulante,
        on_delete=models.CASCADE,
        related_name="eventos_score",
    )
    tipo = models.CharField(max_length=40, choices=TipoEventoScore.choices)
    pontos = models.IntegerField()
    saldo_apos = models.IntegerField()
    descricao = models.CharField(max_length=255)
    chave = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        verbose_name = "Evento de score"
        verbose_name_plural = "Eventos de score"
        constraints = (
            models.UniqueConstraint(
                fields=("ambulante", "chave"),
                condition=~models.Q(chave=""),
                name="evento_score_chave_unica",
            ),
        )

    def __str__(self):
        sinal = "+" if self.pontos > 0 else ""
        return f"{self.ambulante} {sinal}{self.pontos} ({self.tipo})"


class Fiscal(UsuarioBase):
    matricula_funcional = models.CharField(max_length=50, unique=True)
    zona_atuacao_primaria = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome} - {self.matricula_funcional}"


class Gestor(UsuarioBase):
    matricula_funcional = models.CharField(max_length=50, unique=True)
    cargo = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome} - {self.cargo}"


class Administrador(UsuarioBase):
    acesso_master = models.BooleanField(default=False)
    acesso_painel_tecnico = models.BooleanField(default=False)

    def __str__(self):
        return self.nome


class ConfiguracaoSeguranca(ModeloBase):
    """Singleton das políticas globais e da matriz de acessos por perfil."""

    TEMPO_SESSAO_CHOICES = (
        (15, "15 minutos"),
        (30, "30 minutos (Recomendado)"),
        (60, "60 minutos (1 hora)"),
        (120, "120 minutos (2 horas)"),
    )
    TENTATIVAS_CHOICES = (
        (3, "3 tentativas incorretas"),
        (5, "5 tentativas incorretas (Padrão)"),
        (10, "10 tentativas incorretas"),
    )
    EXIGENCIA_2FA_CHOICES = (
        ("todos", "Obrigatório para Todos os Perfis"),
        ("internos", "Obrigatório apenas para TI, Gestores e Fiscais"),
        ("opcional", "Opcional para todos os perfis"),
    )
    RETENCAO_LOGS_CHOICES = (
        (6, "6 meses"),
        (12, "12 meses (Exigência LGPD)"),
        (24, "24 meses (2 anos)"),
        (36, "36 meses (3 anos)"),
    )

    tempo_sessao_minutos = models.PositiveSmallIntegerField(
        default=30,
        choices=TEMPO_SESSAO_CHOICES,
    )
    tentativas_bloqueio = models.PositiveSmallIntegerField(
        default=5,
        choices=TENTATIVAS_CHOICES,
    )
    exigencia_2fa = models.CharField(
        max_length=20,
        default="internos",
        choices=EXIGENCIA_2FA_CHOICES,
    )
    retencao_logs_meses = models.PositiveSmallIntegerField(
        default=12,
        choices=RETENCAO_LOGS_CHOICES,
    )
    matriz = models.JSONField(default=matriz_padrao, blank=True)

    class Meta:
        verbose_name = "Configuração de segurança"
        verbose_name_plural = "Configurações de segurança"

    def __str__(self):
        return "Políticas globais de acesso"

    @classmethod
    def carregar(cls):
        objeto, _criado = cls.objects.get_or_create(
            pk=1,
            defaults={"matriz": matriz_padrao()},
        )
        return objeto

    def perfil_pode(self, perfil, modulo):
        if perfil in (Perfil.ADMINISTRADOR, Perfil.ADMINISTRADOR.value):
            return True
        chave = perfil.value if hasattr(perfil, "value") else str(perfil)
        return bool(self.matriz.get(modulo, {}).get(chave, False))


class LogAcessoDossie(ModeloBase):
    """Auditoria de acesso ao dossiê do ambulante (LGPD)."""

    usuario = models.ForeignKey(
        "usuarios.UsuarioBase",
        on_delete=models.CASCADE,
        related_name="acessos_dossie",
    )
    ambulante = models.ForeignKey(
        "usuarios.Ambulante",
        on_delete=models.CASCADE,
        related_name="logs_acesso_dossie",
    )

    class Meta:
        verbose_name = "Log de acesso ao dossiê"
        verbose_name_plural = "Logs de acesso ao dossiê"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.usuario} → {self.ambulante} ({self.criado_em})"
