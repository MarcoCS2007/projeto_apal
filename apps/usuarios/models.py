from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.core.models import ModeloBase


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

    def __str__(self):
        return self.apelido_nome_fantasia or self.nome

    @property
    def cadastro_completo(self):
        return bool(self.data_nasc and self.escolaridade and self.tipo_atuacao)


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
