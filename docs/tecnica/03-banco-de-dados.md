# 3. Banco e models — o que o código realmente decide

O Postgres não conhece “ambulante” nem “alvará”. Quem conhece são as classes em `models.py`. O ORM traduz `Ambulante.objects.filter(cpf="...")` em SQL. Este capítulo explica as decisões **dentro** dessas classes.

## 3.1 `ModeloBase`: três colunas em quase tudo

```4:18:apps/core/models.py
class AtivoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)


class ModeloBase(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)

    objects = models.Manager()
    ativos = AtivoManager()

    class Meta:
        abstract = True
```

`abstract = True` significa: **não existe tabela `core_modelobase`**. Cada filho (`PontoOcupacao`, `LicencaAlvara`, …) ganha as três colunas na *própria* tabela.

- `auto_now_add` grava a data só na inserção.
- `auto_now` atualiza em todo `save()`.
- `ativo=False` é o “apagar” do sistema. O gestor que “exclui” um ponto não dá `DELETE`: o código faz `ponto.ativo = False`. Licenças antigas continuam apontando para o ponto.

Há dois managers de propósito:

- `PontoOcupacao.objects.all()` — inclui inativos (histórico, admin).
- `PontoOcupacao.ativos.all()` — só `ativo=True` (catálogo da tela).

`AtivoManager.get_queryset` injeta o `filter(ativo=True)` em *qualquer* consulta que passe por `.ativos`. Se você listar o catálogo com `.objects` e esquecer o filtro, o ambulante volta a ver vaga “excluída”.

## 3.2 Login por CPF, não por username

O Django espera um `User` com campo `username`. Aqui o modelo de autenticação é `UsuarioBase` (`AUTH_USER_MODEL` em `config/settings/base.py`).

```52:67:apps/usuarios/models.py
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
```

`USERNAME_FIELD = "cpf"` faz o SimpleJWT e o `authenticate(username=...)` tratarem o identificador como CPF. A senha **nunca** é texto puro: `create_user` chama `set_password`, que grava hash.

`UsuarioBaseManager.create_superuser` não cria um `UsuarioBase` “nu”: ele pega o model `Administrador` e cria por ali. Por isso o primeiro `createsuperuser` já entra no painel Master.

O backend web `CPFOuEmailBackend` aceita e-mail se o identificador contém `@`; senão remove tudo que não é dígito e busca `cpf=`. Os dois caminhos batem na mesma linha da tabela `usuarios_usuariobase`.

## 3.3 Quatro perfis = quatro tabelas ligadas pelo mesmo `id`

`Ambulante(UsuarioBase)` não adiciona colunas na tabela base. O Django cria `usuarios_ambulante` com FK `usuariobase_ptr_id` apontando para `usuarios_usuariobase.id`, e essa FK **é** a primary key do ambulante.

Consequência prática que aparece o tempo todo:

```python
Ambulante.objects.get(pk=request.user.pk)
```

O pk do `request.user` (que pode ter sido carregado como `UsuarioBase`) **é** o pk do `Ambulante`. Não existe “tabela de ligação N:N entre user e perfil”. Um CPF é um perfil.

## 3.4 `user.role`: como o sistema descobre quem você é

```96:106:apps/usuarios/models.py
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
```

Três tentativas, nessa ordem:

1. Se o objeto **já é** um `Ambulante`, `self.__class__.__name__` é `"Ambulante"`. `lower()` → `"ambulante"`, que existe em `Perfil`. Mixins e `IsAmbulante` usam isso.
2. Se o ORM carregou um `UsuarioBase` genérico (comum no JWT), a instância ainda tem os related `ambulante`, `fiscal`, `gestor`, `administrador` (OneToOne). `hasattr(self, "ambulante")` é True só se a linha filha existe. O `select_related` em `JWTAuthenticationComPerfil` existe para esse `hasattr` não disparar query extra e para o related já estar preenchido.
3. Superuser sem linha de perfil vira administrador por segurança.

`Perfil` é `TextChoices`: o valor gravado/comparado é a string `"fiscal"`, não um inteiro. Comparar com `user.role == Perfil.FISCAL` ou com `"fiscal"` funciona porque o enum se compara ao value.

Se `role` voltar `None`, os mixins recusam acesso. Isso acontece se alguém criar um `UsuarioBase` sem subclasse — o seed e os forms de cadastro não fazem isso.

## 3.5 `cadastro_completo`: a trava do “Enviar” da licença

Não é um campo no banco. É uma propriedade calculada:

```161:176:apps/usuarios/models.py
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
```

Em português: tem data de nascimento, escolaridade, tipo de atuação (fixo/móvel/eventual), **pelo menos um** `Endereco` (`related_name="enderecos"`) e uma `EstruturaTrabalho` com tipo e m² > 0.

O que isso **não** exige: CNPJ, ponto pretendido, documentos anexados, gênero nem renda. Gênero e renda alimentam o dashboard; ponto e anexos entram na etapa 5–6 e no parecer. Por isso um ambulante “completo” ainda pode estar sem requerimento.

`abrir_requerimento` consulta exatamente essa propriedade. Se você marcar cadastro completo só com um checkbox na tela, o service ainda recusa.

## 3.6 Conta suspensa vs inativa

`aplicar_situacao_conta` grava flags no JSON `dados_complementares` **e** desliga `ativo` / `is_active`. `is_active=False` impede login Django/JWT. O JSON distingue cancelada de suspensa para o badge do dossiê (`situacao_conta`).

Dois campos booleanos (`ativo` do `ModeloBase` e `is_active` do auth) são atualizados juntos de propósito: um apaga o registro do catálogo, o outro barra autenticação.

## 3.7 Licença: uma tabela, dois momentos de vida

`LicencaAlvara` é o requerimento **e** o alvará. Não há `Requerimento` separado.

Na criação, `status` default é `"Em Análise"`. O `save()` gera o protocolo **depois** do primeiro INSERT, porque precisa do `pk`:

```264:271:apps/licenciamento/models.py
    def save(self, *args, **kwargs):
        from django.utils import timezone

        super().save(*args, **kwargs)
        if not self.protocolo:
            ano = (self.criado_em or timezone.now()).year
            self.protocolo = f"REQ-{ano}-{self.pk:04d}"
            super().save(update_fields=["protocolo"])
```

`0001` é o pk com 4 dígitos, não um contador anual isolado. Dois saves: um para nascer a linha, outro só no `protocolo`.

Propriedades que as telas usam como se fossem colunas:

| Propriedade | Verdadeira quando |
| --- | --- |
| `na_fila` | status ∈ {Em Análise, Pendência Documental} |
| `aguardando_taxa` | ainda não pagou **e** status é Aprovado ou Aguardando Pagamento |
| `pode_emitir` | status Aprovado **e** `numero_licenca` vazio |
| `qr_valido` | status Ativo **e** vencimento hoje ou futuro |
| `pode_renovar` | status Vencido |

`qr_valido` é a trava da credencial:

```288:296:apps/licenciamento/models.py
    def qr_valido(self):
        from django.utils import timezone

        if self.status != StatusLicenca.ATIVO:
            return False
        return not (
            self.data_vencimento and self.data_vencimento < timezone.localdate()
        )
```

Mesmo que o HMAC no ambulante ainda exista, a tela do crachá recusa se isso for False. Suspensão não apaga o hash; só faz `qr_valido` falhar pelo status.

`pode_emitir` impede emitir duas vezes a mesma linha: depois que `_gerar_numero_licenca` preenche `ALV-…`, a propriedade vira False.

No deferimento, `valor_taxa` passa a ser `estrutura.dimensoes_metragem * categoria.fator_financeiro`. O default do campo no banco (`VALOR_TAXA_DAM` = R$ 120) só vale até o parecer calcular.

## 3.8 Ponto de ocupação: Livre no papel vs Livre de verdade

O campo `status_ocupacao` pode dizer Livre, mas o método `disponivel_para_nova_atribuicao` exige **três** coisas:

```83:94:apps/espacos/models.py
    def tem_licenca_ativa(self):
        from apps.licenciamento.models import StatusLicenca

        return self.licencas.filter(
            ativo=True,
            status=StatusLicenca.ATIVO,
        ).exists()

    def disponivel_para_nova_atribuicao(self):
        if not self.ativo or self.status_ocupacao != StatusOcupacao.LIVRE:
            return False
        return not self.tem_licenca_ativa()
```

Por quê a query extra? Porque o status do ponto e o status da licença podem divergir (bug, emissão pela metade, seed). O deferimento e a emissão perguntam o método, não só o CharField. `ocupar()` só escreve `Ocupado`. `liberar_se_livre()` só volta a Livre se **não** restar licença Ativa — senão uma renovação no mesmo ponto apagaria a ocupação da licença ainda válida.

`metragem_compativel` é `estrutura.m² <= ponto.m²`. `None` passa (não bloqueia se a estrutura ainda não tem metragem); o cadastro completo já exige m² > 0, então no parecer real a comparação roda.

## 3.9 Documento: um tipo por ambulante

Constraint `uniq_documento_ambulante_tipo`: o ambulante não tem dois RG. Reenviar **substitui** o arquivo e volta o status para Pendente. `rejeitar` exige texto; senão `ValidationError`. A rejeição chama `marcar_pendencia_documental`, que dá `update` em lote nas licenças Em Análise daquele ambulante — não percorre a view.

## 3.10 Score: histórico + saldo

`Ambulante.pontuacao` é o saldo atual (default 100). `EventoScore` é o extrato. A constraint única em `(ambulante, chave)` com `chave != ""` impede o mesmo alvará pontuar +10 duas vezes. O capítulo 6 mostra o `if chave already exists: return None` que completa essa garantia no Python.

`LogAcessoDossie` grava quem abriu o dossiê (HTML ou PDF). Não altera o ambulante; serve à auditoria LGPD e some com `purgar_retencao`.

## 3.11 O que o banco *não* faz sozinho

Não há trigger de “passou da data → Vencido”. Quem faz isso é `marcar_licencas_vencidas()` no momento em que alguém consulta credencial, fiscal ou dashboard. Se ninguém abrir o sistema no dia 1º de janeiro, as linhas podem continuar `Ativo` até a próxima request — e aí o `update` em massa corre.

Próximo capítulo: como uma view usa `role`, mixins e esses models sem duplicar a regra.
