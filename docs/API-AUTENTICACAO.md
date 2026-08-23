# API de Autenticação - Projeto APAL

O sistema possui **dois canais de autenticação**, com propósitos distintos:

| Canal | Tecnologia | Uso | Cria sessão Django? |
| --- | --- | --- | --- |
| API JWT | SimpleJWT (Bearer token) | App móvel e clientes stateless | Não |
| Backoffice web | Cookie de sessão do Django | Gestores e Administradores no navegador | Sim |

Este documento descreve a **API JWT**. O login web fica em `/login/` e não faz parte deste contrato.

---

## 1. Visão geral

- Identificador de login: **CPF** (`USERNAME_FIELD`).
- Tokens: `access` (1 hora) e `refresh` (7 dias).
- O `access` inclui o claim customizado **`role`**, com o perfil do usuário.
- Usuário com `ativo=False` ou `is_active=False` não autentica.
- Rotas protegidas exigem o header `Authorization: Bearer <access>`.

### Perfis (`role`)

| Valor no token | Modelo | Canal esperado |
| --- | --- | --- |
| `ambulante` | `Ambulante` | API (app móvel) |
| `fiscal` | `Fiscal` | API (app móvel) |
| `gestor` | `Gestor` | Backoffice web (JWT também funciona) |
| `administrador` | `Administrador` | Backoffice web (JWT também funciona) |

A API de login **não bloqueia** Gestor/Administrador: qualquer perfil válido recebe token. A restrição de backoffice vale só para `/login/` (cookie).

---

## 2. Endpoints

Base: `/api/`

### 2.1 Login — `POST /api/login/`

Gera o par de tokens. **Não cria cookie `sessionid`.**

**Corpo (JSON):**

```json
{
  "cpf": "10020030088",
  "password": "amb123"
}
```

**Resposta `200`:**

```json
{
  "refresh": "<jwt>",
  "access": "<jwt>",
  "role": "ambulante"
}
```

O campo `role` também vai **dentro** do `access` (claim JWT), além do corpo da resposta.

**Erros:**

| Status | Quando |
| --- | --- |
| `401` | CPF/senha inválidos ou usuário inativo |
| `400` | Campos ausentes |

Exemplo:

```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d "{\"cpf\": \"10020030088\", \"password\": \"amb123\"}"
```

Usuários do seed local (`python manage.py seed_inicial`):

| Perfil | CPF | Senha | Observação |
| --- | --- | --- | --- |
| Administrador | `52998224725` | `admin123` | Painel Master |
| Gestor | `11144477735` | `gestor123` | Posturas |
| Gestor | `20030040094` | `gestor123` | Vigilância Sanitária |
| Gestor | `30040050009` | `gestor123` | SEFIN |
| Fiscal | `12345678909` | `fiscal123` | Centro |
| Fiscal | `40050060007` | `fiscal123` | Feira do Bairro Brasil |
| Fiscal | `50060070013` | `fiscal123` | Terminal |
| Fiscal | `60070080020` | `fiscal123` | Itinerante |
| Ambulante | `10020030088` | `amb123` | Cadastro pendente |
| Ambulante | `39053344705` | `amb123` | Cadastro completo (MEI) |
| Ambulante | `30405060726` | `amb123` | Só a conta |
| Ambulante | `20304050601` | `amb123` | Completo e inativo |

Há outros ambulantes fictícios (Antônio, Raimunda, Carlos, Pedro) com a mesma senha `amb123`, em situações de cadastro completo ou parcial.

### 2.2 Refresh — `POST /api/token/refresh/`

Troca um `refresh` válido por um novo `access`.

```json
{
  "refresh": "<jwt>"
}
```

**Resposta `200`:**

```json
{
  "access": "<jwt>"
}
```

O novo access também traz o claim `role`.

### 2.3 Usuário autenticado — `GET /api/me/`

Retorna os dados do dono do token. Exige Bearer.

```bash
curl http://localhost:8000/api/me/ \
  -H "Authorization: Bearer <access>"
```

**Resposta `200`:**

```json
{
  "id": 1,
  "cpf": "10020030088",
  "nome": "João",
  "sobrenome": "Ambulante",
  "email": "ambulante@apal.com",
  "role": "ambulante"
}
```

Sem token (ou token inválido/expirado): `401`.

---

## 3. Como autenticar as demais rotas

Todas as views DRF nascem com `IsAuthenticated`, salvo as de login/refresh (`AllowAny`).

```http
GET /api/alguma-rota/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Não envie CSRF no fluxo JWT. CSRF vale para o backoffice (cookie + POST).

### Claims relevantes do access token

| Claim | Origem | Exemplo |
| --- | --- | --- |
| `user_id` | SimpleJWT | `4` |
| `role` | customizado | `"fiscal"` |
| `exp` | SimpleJWT | timestamp de expiração |
| `token_type` | SimpleJWT | `"access"` |

---

## 4. Permissões por perfil

Use as classes em `apps/core/permissions.py` nas views da API:

```python
from apps.core.permissions import IsAmbulante, IsFiscal, IsGestor, IsAdministrador

class MinhaView(APIView):
    permission_classes = (IsFiscal,)
```

| Classe | Permite |
| --- | --- |
| `IsAmbulante` | `role == ambulante` |
| `IsFiscal` | `role == fiscal` |
| `IsGestor` | `role == gestor` |
| `IsAdministrador` | `role == administrador` |

Elas já exigem usuário autenticado. Combine com `|` do DRF se a rota aceitar mais de um perfil.

---

## 5. Relação com o backoffice

O login web usa sessão Django e cookie `sessionid`, em canais separados: `/login/` (Gestor/Master), `/entrar/` (Ambulante) e `/fiscal/entrar/` (Fiscal). No backoffice, ambulante e fiscal recebem erro de formulário e **não** ganham sessão.

O encerramento do expediente é `POST /logout/` (CSRF obrigatório). A view invalida a sessão, apaga o cookie `sessionid` e redireciona Gestor/Administrador para `/login/?encerrado=1`. Ambulante autenticado na web volta para `/entrar/`. `GET /logout/` não encerra a sessão (405).

Não misture os fluxos no cliente:

- App móvel → `/api/login/` → guardar `access`/`refresh` → header Bearer. Casos de uso em [API-MOVEL.md](API-MOVEL.md).
- Navegador backoffice → `/login/` → cookie gerenciado pelo Django.

---

## 6. Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/usuarios/urls.py` | Rotas `/api/login/`, `/api/token/refresh/`, `/api/me/`, cadastro e score |
| `apps/usuarios/serializers.py` | `LoginSerializer` (claim `role`) |
| `apps/usuarios/authentication.py` | JWT com `select_related` dos perfis |
| `apps/usuarios/urls_web.py` | Login/logout por cookie |
| `apps/core/permissions.py` | `IsAmbulante`, `IsFiscal`, `IsGestor`, `IsAdministrador` |
| `config/settings/base.py` | `REST_FRAMEWORK` e `SIMPLE_JWT` |
