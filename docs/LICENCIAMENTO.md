# Módulo Licenciamento — Ciclo da autorização de trabalho

Pasta: `apps/licenciamento`

Cuida do ciclo de vida da licença/alvará: documentos, fila de análise, parecer, taxa municipal, emissão, credencial com QR, renovação e relatórios gerenciais.

Telas de fila, parecer e emissão ficam nas views do gestor (`apps/usuarios/views_gestor.py`), mas as **regras** estão neste módulo (`services.py`).

---

## Para que serve

- Definir categorias de produto e quais laudos cada uma exige.
- Receber, aprovar e rejeitar documentos do ambulante.
- Abrir requerimento (`REQ-AAAA-NNNN`) quando o cadastro está completo.
- Deferir / indeferir / devolver com pendência.
- Simular o pagamento da taxa (DAM de R$ 120,00) e emitir o alvará (`ALV-AAAA-NNNN`).
- Gerar a credencial digital e o PNG do QR.
- Renovar licença vencida e marcar automaticamente as que passaram da validade.
- Alimentar o dashboard do gestor com ocupação e indicadores.

---

## Modelos

### `CategoriaProduto`

Nome, descrição e flags `exige_laudo_sanitario` / `exige_laudo_bombeiros`. Categorias com licença ativa não podem ser excluídas (são só inativadas).

### `DocumentoAnexo`

Um arquivo por tipo e ambulante (RG/CPF, comprovante, MEI, laudo sanitário, laudo de bombeiros). Status: **Pendente**, **Aprovado**, **Rejeitado**. Rejeição exige justificativa e coloca o requerimento em **Pendência Documental**. Reenvio volta o documento a Pendente e, se não houver outras rejeições, reabre a análise.

Formatos aceitos: PDF, PNG, JPG, JPEG, WEBP.

### `LicencaAlvara`

Vínculos com ambulante, estrutura, ponto, categoria e gestor. Campos-chave:

| Campo | Significado |
| --- | --- |
| `protocolo` | `REQ-{ano}-{pk}` gerado no primeiro save |
| `numero_licenca` | `ALV-{ano}-{pk}` na emissão |
| `status` | Ver máquina de estados abaixo |
| `taxa_paga` | DAM simulado confirmado |
| `licenca_origem` | Preenchido em renovação |

### `EscalaTrabalho`

Dias e horários autorizados, gravados na emissão. O fiscal usa essa escala para detectar atuação fora do horário.

---

## Máquina de estados da licença

```text
Em Análise ──► Pendência Documental ──► Em Análise (após reenvio)
     │
     ├── Indeferido
     └── Aprovado ──► (taxa, se ainda não paga) ──► emissão ──► Ativo
                                                              │
                                              Vencido ◄───────┤ (data passou)
                                              Suspenso        │ (ocorrência / gestão)
                                              Cancelado       │ (ocorrência / gestão)
```

Fila do gestor (`STATUS_FILA`): **Em Análise** e **Pendência Documental**.

Listagem de licenças do gestor: **Aprovado**, **Ativo**, **Vencido**, **Suspenso**.

O QR só é válido com status **Ativo** e data de vencimento ainda no futuro (`qr_valido`).

---

## Documentos obrigatórios

Sempre: comprovante de residência e RG/CPF.

Condicionais:

- CNPJ preenchido → MEI
- Categoria com laudo sanitário → laudo sanitário
- Categoria com laudo de bombeiros → laudo dos bombeiros

O gestor **não consegue deferir** enquanto algum obrigatório não estiver **Aprovado**.

---

## Rotas

`apps/licenciamento/urls_web.py`

| URL | Perfil | Função |
| --- | --- | --- |
| `/ambulante/alvara/` | Ambulante | Histórico, protocolo, taxa, renovação |
| `/ambulante/alvara/<id>/renovar/` | Ambulante | `POST` — clona licença vencida |
| `/ambulante/credencial/` | Ambulante | Credencial para impressão |
| `/ambulante/credencial/qr.png` | Ambulante | PNG do QR (`?download=1` para baixar) |
| `/api/alvara/<id>/simular-pagamento/` | Ambulante | `POST` — confirma DAM (HTMX ou redirect) |
| `/gestor/categorias/` | Gestor | CRUD de categorias |
| `/gestor/triagem/` | Gestor | Fila de documentos pendentes |
| `/api/documentos/<id>/aprovar/` | Gestor | `POST` (HTMX) |
| `/api/documentos/<id>/rejeitar/` | Gestor | `POST` com justificativa |
| `/api/relatorios/ocupacao/` | Gestor | JSON ou HTML (HTMX) dos indicadores |
| `/api/ambulante/documentos/` | Ambulante (JWT) | Lista e envio de anexos |
| `/api/ambulante/solicitacao/` | Ambulante (JWT) | Status da licença |
| `/api/ambulante/credencial/` | Ambulante (JWT) | Código HMAC e PNG do QR |

App móvel: [API-MOVEL.md](API-MOVEL.md).

Parecer e emissão: `/gestor/analisar/<id>/` e `/gestor/emitir/<id>/` (módulo usuarios, regras aqui).

---

## Instruções de uso

### Ambulante — protocolar e acompanhar

1. Conclua o cadastro (etapa 6) e clique em **Enviar**. O sistema chama `abrir_requerimento` e gera o protocolo.
2. Abra **Meu Alvará** (`/ambulante/alvara/`).
3. Se um documento for rejeitado, volte ao cadastro, reenvie o arquivo e aguarde nova triagem.
4. Quando o gestor deferir, aparece o painel da **taxa municipal** (R$ 120,00). Confirme o pagamento simulado. Isso **não emite** o alvará — só libera a gestão para emitir.
5. Depois da emissão, a credencial com QR fica em `/ambulante/credencial/`. Imprima e mantenha visível no ponto.
6. Licença **Vencida**: use renovar. Abre um novo requerimento ligado à origem e soma pontos de renovação no score.

### Gestor — triagem de documentos

1. `/gestor/triagem/` lista anexos **Pendentes**.
2. **Aprovar** libera aquele tipo.
3. **Rejeitar** exige texto. O processo vai para Pendência Documental e o ambulante vê o motivo no painel.

### Gestor — parecer

1. `/gestor/fila/` → abrir o processo.
2. Confira ponto livre, metragem da estrutura ≤ metragem máxima do ponto, categoria e documentos aprovados.
3. Ações:
   - **Deferir** — status Aprovado; redireciona para emissão.
   - **Pendência** — devolve com motivo.
   - **Indeferir** — encerra com justificativa obrigatória.

Não é possível deferir ponto ocupado, metragem incompatível ou documento faltando.

### Gestor — emitir alvará

1. Informe data de emissão, validade (posterior à emissão), ponto, dias da semana e horário.
2. Ao gravar: número `ALV-…`, status **Ativo**, ponto **Ocupado**, escalas criadas, QR gravado no ambulante, **+10** no score.

### Gestor — categorias

Em `/gestor/categorias/`, cadastre o ramo (ex.: Alimentos Manipulados) e marque os laudos exigidos. Isso muda a checklist da etapa 6 do ambulante.

### Gestor — dashboard

`/gestor/dashboard/` e `GET /api/relatorios/ocupacao/` (filtros `bairro`, `origem=residentes|itinerantes`, `periodo` em dias). Alerta de lotação a partir de 90% dos pontos ocupados no bairro.

---

## Regras importantes

- Um ambulante só tem **um requerimento aberto** na fila por vez.
- Pagamento da taxa não gera QR; só a **emissão** gera.
- `marcar_licencas_vencidas()` roda em consultas de credencial, fiscalização e relatórios: Ativo com data passada vira Vencido e o ponto é liberado se não houver outra licença ativa.
- Renovação só a partir de status **Vencido**.

---

## Dependências

- [usuarios](USUARIOS.md): ambulante, gestor, score.
- [espacos](ESPACOS.md): ponto e estrutura.
- [core](CORE.md): geração/validação do QR.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/licenciamento/models.py` | Categoria, documento, licença, escala |
| `apps/licenciamento/services.py` | Requerimento, parecer, taxa, emissão, renovação |
| `apps/licenciamento/relatorios.py` | Indicadores do dashboard |
| `apps/licenciamento/views.py` | Credencial, alvará, triagem, categorias |
| `apps/licenciamento/urls_web.py` | Rotas |
