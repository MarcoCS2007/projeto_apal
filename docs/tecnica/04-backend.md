# 4. Back-end — o que a view faz (e o que ela não faz)

Uma view neste projeto é um porteiro: confirma quem está logado, lê o formulário, chama uma função de domínio e escolhe o HTML ou o JSON. A regra (“pode emitir?”, “o QR é falso?”) não deveria nascer aqui.

## 4.1 Mixins: a ordem das classes importa

Exemplo real, o chat do ambulante:

```13:17:apps/assistente/views.py
class AssistenteAmbulanteView(LoginRequiredMixin, AcessoAmbulanteMixin, FormView):
    template_name = "ambulante/assistente.html"
    form_class = PerguntaAssistenteForm
    login_url = reverse_lazy("entrar")
    success_url = reverse_lazy("ambulante_assistente")
```

O Python resolve herança da esquerda para a direita:

1. `LoginRequiredMixin` — sem cookie de sessão, 302 para `/entrar/`.
2. `AcessoAmbulanteMixin` — tem sessão, mas `user.role` não é ambulante? Não mostra o chat. Manda gestor ao backoffice, fiscal ao painel dele, Master ao `/master/`.
3. `FormView` — GET mostra o form; POST válido cai em `form_valid`.

`AcessoAmbulanteMixin.test_func` é literalmente:

```163:165:apps/usuarios/views.py
    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role == Perfil.AMBULANTE)
```

`handle_no_permission` não devolve 403 genérico para quem já está logado no perfil errado: redireciona para o painel daquele perfil. Isso evita o gestor “preso” num login de ambulante.

O backoffice usa o mesmo padrão com `AcessoBackofficeMixin` (`role` em gestor **ou** administrador) e o Master com `AcessoMasterMixin` (só administrador). `PainelGestorMixin` ainda empilha `RequerModuloMixin`: mesmo sendo gestor, se a matriz do Master desligou `ocorrencias` para o perfil gestor, `usuario_pode` falha e estoura `PermissionDenied`.

## 4.2 A API faz a mesma pergunta de outro jeito

```6:13:apps/core/permissions.py
class TemPerfil(BasePermission):
    perfis_permitidos = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in self.perfis_permitidos
        )
```

`IsFiscal` só preenche `perfis_permitidos = (Perfil.FISCAL,)`. Sem Bearer válido o DRF responde 401 (não autenticado). Com token de ambulante numa rota de fiscal, 403 (autenticado, perfil errado).

Isso é a versão JSON do mixin. Não copie um `if request.user.role != "fiscal"` na `APIView`: use `permission_classes = (IsFiscal,)`.

## 4.3 JWT: o token carrega o perfil para o app não adivinhar

```8:26:apps/usuarios/serializers.py
class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.ativo:
            raise AuthenticationFailed(
                "Usuário inativo. Entre em contato com a administração."
            )

        data["role"] = self.user.role
        return data
```

`super().validate` já autentica CPF/senha (USERNAME_FIELD). Depois:

- Recusa se `ativo=False` (conta suspensa no dossiê), mesmo com senha certa.
- Coloca `role` **no corpo JSON** e **dentro** do access token (`get_token`). O app pode ler o JSON sem decodificar JWT, e o servidor ainda confia no claim só depois de validar a assinatura.

`JWTAuthenticationComPerfil.get_user` busca o usuário com `select_related("ambulante", "fiscal", "gestor", "administrador")`. Sem isso, o primeiro `user.role` (passo 2 da propriedade) faria query extra em toda request da API.

## 4.4 O wizard: um `View` e um dicionário de forms

Não são seis URLs. É uma classe e `?etapa=N` / `POST etapa=N`.

```340:347:apps/usuarios/views.py
ETAPAS_CADASTRO = {
    1: DadosPessoaisCadastroForm,
    2: EnderecoCadastroForm,
    3: EmpresaCadastroForm,
    4: EstruturaCadastroForm,
    5: PontoCadastroForm,
    6: AnexosCadastroForm,
}
```

`_etapa` lê o inteiro, e se vier lixo volta para 1. Isso permite o stepper por teclado (`?etapa=3`) sem rota nova.

No GET, instancia o form da etapa **já com o ambulante**, para o form preencher valores salvos (rascunho). No POST:

```410:426:apps/usuarios/views.py
    def post(self, request):
        ambulante = self._ambulante()
        etapa = self._etapa(request.POST)
        form_class = ETAPAS_CADASTRO[etapa]
        acao = request.POST.get("acao", "proxima")
        form_kwargs = {"ambulante": ambulante}
        if etapa == 6:
            form_kwargs["acao"] = acao
        form = form_class(request.POST, request.FILES, **form_kwargs)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self._contexto(ambulante, etapa, form),
            )

        form.save()
```

Fluxo mental:

1. Qual etapa? Qual botão (`proxima`, `salvar`, `enviar`)?
2. O form valida (metragem positiva, ponto Livre, arquivo com extensão certa…).
3. `form.save()` grava **só aquela etapa** (endereço na 2, estrutura na 4, etc.). A view não monta o `Endereco(...)` na mão.
4. Se a validação falha, o **mesmo** template reabre com `form.errors` — não redireciona, senão a mensagem some.

Depois do `save()`, se `acao == "enviar"` e `cadastro_completo`, a view importa `abrir_requerimento` e protocola. A view **não** cria `LicencaAlvara` direto: se criar, fura a regra de “já existe requerimento na fila”.

`_ambulante()` usa `Ambulante.objects.get(pk=self.request.user.pk)` porque o mixin já garantiu o perfil; um `UsuarioBase` puro não passaria do `test_func`.

## 4.5 `form_valid` do assistente: o padrão “view magra”

```22:24:apps/assistente/views.py
    def form_valid(self, form):
        responder_pergunta(self._ambulante(), form.cleaned_data["pergunta"])
        return super().form_valid(form)
```

O form já garantiu pergunta não vazia (máx. 500). A view não pontua tokens nem escolhe o trecho da FAQ. `responder_pergunta` faz isso e grava o log. `super().form_valid` redireciona para `success_url` (PRG: POST-redirect-GET), então um F5 não reenvia a pergunta.

`get_context_data` busca as 20 últimas linhas, **inverte** a lista para a conversa aparecer em ordem cronológica (o queryset vinha da mais nova). As sugestões são a tupla `SUGESTOES_ASSISTENTE`, não algo gerado por IA.

A API do assistente chama a **mesma** `responder_pergunta` e devolve JSON. Mudar o fallback em `core/ia.py` altera site e app juntos.

## 4.6 HTMX: a view pergunta o header

Na triagem, aprovar documento é POST em `/api/documentos/<id>/aprovar/`. A view não é DRF: é Django `View` com `DocumentoHtmxMixin`. Se vier `HX-Request`, ela renderiza só `gestor/_documento_row.html` (a linha da tabela). Se não, `redirect("gestor_triagem")` — funciona com JS desligado.

Isso importa quando você copiar o padrão: o “endpoint `/api/`” da triagem ainda usa sessão e CSRF, não JWT. O prefixo `/api/` aqui é histórico da tela, não o contrato do app móvel.

## 4.7 Por que `services.py` importa models **dentro** da função

Em `abrir_requerimento` você vê `from apps.licenciamento.models import LicencaAlvara` no corpo. Isso evita import circular: `models` de licença importam serviços no `rejeitar()`, e serviços importam models. Iniciante que subir o import para o topo do arquivo pode ganhar `AppRegistryNotReady` ou ciclo. Siga o padrão do arquivo: import tardio onde o ciclo já existe.

`@transaction.atomic` em `abrir_requerimento`, `aplicar_parecer` e `emitir_alvara` significa: se a validação estourar no meio, o `save()` anterior daquela função desfaz. Emissão grava licença + escalas + QR + score; sem atomic, um crash depois de `ocupar()` deixaria ponto ocupado sem alvará.

Próximo capítulo: como o HTML recebe o `context` que essas views montaram.
