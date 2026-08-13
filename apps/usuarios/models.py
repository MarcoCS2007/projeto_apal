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
    codigo_qr_code = models.CharField(max_length=255, unique=True, blank=True, null=True)
    data_nasc = models.DateField(blank=True, null=True)
    escolaridade = models.CharField(max_length=100, blank=True, default="")
    nis = models.CharField(max_length=20, blank=True, null=True)
    num_funcionarios = models.IntegerField(default=0)
    pontuacao = models.IntegerField(default=100)
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
