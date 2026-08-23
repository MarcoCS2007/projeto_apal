# API do app móvel — Projeto APAL

Contrato JSON para o aplicativo de **ambulantes** e **fiscais**. A autenticação é a mesma da [API-AUTENTICACAO.md](API-AUTENTICACAO.md): `POST /api/login/` devolve `access`/`refresh` e o claim `role`. Todas as rotas abaixo exigem `Authorization: Bearer <access>`.

Não use o admin Django nem cookie de sessão neste fluxo.

Base: `/api/`

Permissões: `IsAmbulante` e `IsFiscal` em `apps/core/permissions.py`. Perfil errado → `403`. Sem token → `401`.

---

## 1. Fluxos cobertos pelo critério de pronto

### Ambulante: login → status da licença

```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d "{\"cpf\": \"10020030088\", \"password\": \"amb123\"}"

curl http://localhost:8000/api/ambulante/solicitacao/ \
  -H "Authorization: Bearer <access>"
```

**Resposta `200` (trecho):**

```json
{
  "licenca": {
    "id": 1,
    "protocolo": "REQ-2026-0001",
    "numero_licenca": null,
    "status": "Aprovado",
    "taxa_paga": false,
    "qr_valido": false
  },
  "historico": []
}
```

`licenca` é `null` se ainda não houver requerimento.

### Fiscal: login → validar QR → POST ocorrência

```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d "{\"cpf\": \"12345678909\", \"password\": \"fiscal123\"}"

curl "http://localhost:8000/api/fiscal/qr/?codigo=<hash-hmac>" \
  -H "Authorization: Bearer <access>"

curl -X POST http://localhost:8000/api/fiscal/ocorrencias/ \
  -H "Authorization: Bearer <access>" \
  -F "ambulante_id=1" \
  -F "local_ocorrencia=Feira do Bairro Brasil" \
  -F "tipo_ocorrencia=Irregularidade de horário" \
  -F "descricao=Fora da escala autorizada." \
  -F "evidencia_foto=@foto.jpg"
```

O código do QR é o `codigo_qr` da credencial do ambulante (HMAC gravado na emissão do alvará). Sem alvará emitido a validação devolve `valido: false`.

---

## 2. Ambulante (`role=ambulante`)

| Método | URL | Função |
| --- | --- | --- |
| `GET` / `PATCH` / `POST` | `/api/ambulante/cadastro/` | Snapshot do cadastro; `PATCH` com `etapa` 1–6 (mesmos campos da web); `POST` com `acao=enviar` protocola o requerimento |
| `GET` / `POST` | `/api/ambulante/documentos/` | Lista anexos; `POST` multipart `tipo_documento` + `arquivo` (+ `data_validade` opcional) |
| `GET` | `/api/ambulante/solicitacao/` | Status e histórico da licença |
| `GET` | `/api/ambulante/credencial/` | Se o QR está liberado e o código HMAC |
| `GET` | `/api/ambulante/credencial/qr.png` | PNG do QR (`?download=1` para baixar) |
| `GET` | `/api/ambulante/score/` | Pontuação, faixa, eventos e dicas |
| `GET` / `POST` | `/api/ambulante/assistente/` | Histórico + sugestões; `POST` `{"pergunta": "..."}` |

Tipos de documento: `comprovante_residencia`, `rg_cpf`, `mei`, `laudo_sanitario`, `laudo_bombeiros`.

`PATCH /api/ambulante/cadastro/` exemplo:

```json
{
  "etapa": 1,
  "nome_completo": "João Ambulante Silva",
  "data_nasc": "1991-05-20",
  "genero": "masculino",
  "renda_mensal_estimada": "1800.00",
  "telefone_whatsapp": "77999999999",
  "escolaridade": "medio_completo",
  "num_funcionarios": 0
}
```

O `GET` devolve um snapshot com os mesmos campos (incluindo `genero`, `renda_mensal_estimada`, endereço e estrutura). E-mail, CPF e foto 3x4 são alterados na web em `/ambulante/perfil/`, não neste endpoint.

---

## 3. Fiscal (`role=fiscal`)

| Método | URL | Função |
| --- | --- | --- |
| `GET` | `/api/fiscal/busca/?q=` | CPF, nome, número do alvará (`ALV-…`) ou hash do QR |
| `GET` | `/api/fiscal/qr/?codigo=` | Classifica o QR (`valido`, `motivo`, ficha) |
| `POST` | `/api/fiscal/ocorrencias/` | Lavra o auto (JSON ou multipart com foto) |

**Inspeção `200`:**

```json
{
  "valido": true,
  "motivo": "ok",
  "mensagem": "Credencial válida.",
  "fora_horario": false,
  "tipo_sugerido": "Outra irregularidade",
  "ambulante": {"id": 1, "nome_completo": "João Ambulante", "cpf": "10020030088"},
  "licenca": {"numero_licenca": "ALV-2026-0001", "status": "Ativo"},
  "candidatos": []
}
```

Motivos: `ok`, `adulterado`, `suspenso`, `vencido`, `invalido`, `fora_horario`, `sem_licenca`, `nao_encontrado`, `varios`, `vazio`.

**Ocorrência `201`:** campos `local_ocorrencia`, `tipo_ocorrencia` e `descricao` obrigatórios. `ambulante_id` ou `identificacao` (CPF/alvará) opcionais se o infrator não for identificado. Foto no campo `evidencia_foto`.

Tipos: `Advertência`, `Multa`, `Apreensão`, `Irregularidade de ponto`, `Irregularidade de horário`, `Comércio sem licença válida`, `Falta de credencial`, `Outra irregularidade`.

---

## 4. Contas do seed

As mesmas da autenticação (`python manage.py seed_inicial`):

| Perfil | CPF | Senha |
| --- | --- | --- |
| Fiscal | `12345678909` | `fiscal123` |
| Ambulante | `10020030088` | `amb123` |

O ambulante `10020030088` do seed começa sem alvará emitido: `GET /api/ambulante/solicitacao/` funciona, mas o QR só fica `valido` depois da emissão no backoffice.

---

## 5. Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/usuarios/api.py` | Cadastro e score |
| `apps/licenciamento/api.py` | Documentos, solicitação, credencial |
| `apps/fiscalizacao/api.py` | Busca, QR, ocorrência |
| `apps/assistente/api.py` | Chat educativo |
| `apps/core/permissions.py` | `IsAmbulante` / `IsFiscal` |
| `config/settings/base.py` | `LANGUAGE_CODE=pt-br`, `TIME_ZONE=America/Bahia` |
