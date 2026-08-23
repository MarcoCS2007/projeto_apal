# Módulo Licenciamento — Ciclo da autorização de trabalho

Pasta: `apps/licenciamento`

Cuida do ciclo de vida da licença/alvará: documentos, fila de análise, parecer, taxa municipal, emissão, credencial com QR, renovação e relatórios gerenciais.

Telas de fila, parecer, emissão e exportação do dashboard ficam nas views do gestor (`apps/usuarios/views_gestor.py`), mas as **regras** estão neste módulo (`services.py` e `relatorios.py`).

---

## Para que serve

- Definir categorias de produto, laudos exigidos e o **fator financeiro** (R$ por m²).
- Receber, aprovar e rejeitar documentos do ambulante (com entrega controlada do arquivo).
- Abrir requerimento (`REQ-AAAA-NNNN`) quando o cadastro está completo.
- Deferir / indeferir / devolver com pendência.
- Calcular a taxa no deferimento (`metragem da estrutura × fator da categoria`) e simular o pagamento do DAM.
- Emitir o alvará (`ALV-AAAA-NNNN`), gerar a credencial digital e o PNG do QR.
- Renovar licença vencida e marcar automaticamente as que passaram da validade.
- Alimentar o dashboard do gestor com ocupação, indicadores e retrato sociodemográfico.

---

## Modelos

### `CategoriaProduto`

Nome, descrição, flags `exige_laudo_sanitario` / `exige_laudo_bombeiros` e `fator_financeiro` (R$ por m², usado no cálculo da taxa). Categorias com licença ativa não podem ser excluídas (são só inativadas).

O seed inicial já cadastra fatores (ex.: alimentos R$ 15,00/m²).

### `DocumentoAnexo`

Um arquivo por tipo e ambulante (RG/CPF, comprovante, MEI, laudo sanitário, laudo de bombeiros). Status: **Pendente**, **Aprovado**, **Rejeitado**. Rejeição exige justificativa e coloca o requerimento em **Pendência Documental**. Reenvio volta o documento a Pendente e, se não houver outras rejeições, reabre a análise.

Formatos aceitos: PDF, PNG, JPG, JPEG, WEBP.

O arquivo não é servido direto de `/media/` para qualquer um: `/documentos/<id>/arquivo/` exige login e `pode_ver_documento`.

### `LicencaAlvara`

Vínculos com ambulante, estrutura, ponto, categoria e gestor. Campos-chave:

| Campo | Significado |
| --- | --- |
| `protocolo` | `REQ-{ano}-{pk}` gerado no primeiro save |
| `numero_licenca` | `ALV-{ano}-{pk}` na emissão |
| `status` | Ver máquina de estados abaixo |
| `taxa_paga` | DAM simulado confirmado |
| `valor_taxa` | Valor calculado no deferimento (default R$ 120,00 se ainda não calculado) |
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

## Taxa municipal

Não é mais um valor único fixo na tela. No **deferimento**, `aplicar_parecer` grava:

```text
valor_taxa = metragem da estrutura (m²) × fator_financeiro da categoria
```

Se faltar estrutura ou categoria, o fallback é R$ 0,00. O default do campo no banco continua `VALOR_TAXA_DAM` (R$ 120,00) até o parecer calcular.

O ambulante confirma o DAM simulado em `/api/alvara/<id>/simular-pagamento/`. Isso **não emite** o alvará — só libera a gestão para emitir.

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
| `/gestor/categorias/` | Gestor | Listar e cadastrar |
| `/gestor/categorias/<id>/` | Gestor | Editar |
| `/gestor/categorias/<id>/excluir/` | Gestor | Inativar (`POST`) |
| `/gestor/triagem/` | Gestor | Fila de documentos pendentes |
| `/documentos/<id>/arquivo/` | Autenticado com permissão | Visualizar o anexo |
| `/api/documentos/<id>/aprovar/` | Gestor | `POST` (HTMX) |
| `/api/documentos/<id>/rejeitar/` | Gestor | `POST` com justificativa |
| `/api/relatorios/ocupacao/` | Gestor | JSON ou HTML (HTMX) dos indicadores |
| `/api/ambulante/documentos/` | Ambulante (JWT) | Lista e envio de anexos |
| `/api/ambulante/solicitacao/` | Ambulante (JWT) | Status da licença |
| `/api/ambulante/credencial/` | Ambulante (JWT) | Código HMAC e PNG do QR |

Exportações Excel/PDF e JSON dos gráficos: `/gestor/dashboard/exportar.xlsx`, `/gestor/dashboard/exportar.pdf`, `/gestor/dashboard/chart-data/` (módulo usuarios, dados daqui).

App móvel: [API-MOVEL.md](API-MOVEL.md).

Parecer e emissão: `/gestor/analisar/<id>/` e `/gestor/emitir/<id>/` (módulo usuarios, regras aqui).

---

## Instruções de uso

### Ambulante — protocolar e acompanhar

1. Conclua o cadastro (etapa 6) e clique em **Enviar**. O sistema chama `abrir_requerimento` e gera o protocolo.
2. Abra **Meu Alvará** (`/ambulante/alvara/`).
3. Se um documento for rejeitado, volte ao cadastro, reenvie o arquivo e aguarde nova triagem.
4. Quando o gestor deferir, aparece o painel da **taxa municipal** com o valor calculado. Confirme o pagamento simulado. Isso **não emite** o alvará — só libera a gestão para emitir.
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
   - **Deferir** — status Aprovado, calcula `valor_taxa`; redireciona para emissão.
   - **Pendência** — devolve com motivo.
   - **Indeferir** — encerra com justificativa obrigatória.

Não é possível deferir ponto ocupado, metragem incompatível ou documento faltando.

### Gestor — emitir alvará

1. Informe data de emissão, validade (posterior à emissão), ponto, dias da semana e horário.
2. Ao gravar: número `ALV-…`, status **Ativo**, ponto **Ocupado**, escalas criadas, QR gravado no ambulante, **+10** no score.

### Gestor — categorias

Em `/gestor/categorias/`, cadastre o ramo (ex.: Alimentos Manipulados), marque os laudos e o fator financeiro. Isso muda a checklist da etapa 6 e o valor da taxa no deferimento.

### Gestor — dashboard e relatórios

`/gestor/dashboard/` e `GET /api/relatorios/ocupacao/`.

Filtros: `bairro`, `origem=residentes|itinerantes`, `periodo` (dias), `cidade`, `genero`, `faixa` (etária), `escolaridade`.

O relatório inclui ocupação por bairro, categorias, infrações no período e retrato sociodemográfico (idade, gênero, renda, escolaridade). Alerta de lotação a partir de 90% dos pontos ocupados no bairro.

Exportar: Excel e PDF nas URLs do dashboard (mesmo conjunto de filtros).

---

## Regras importantes

- Um ambulante só tem **um requerimento aberto** na fila por vez.
- Pagamento da taxa não gera QR; só a **emissão** gera.
- `marcar_licencas_vencidas()` roda em consultas de credencial, fiscalização e relatórios: Ativo com data passada vira Vencido e o ponto é liberado se não houver outra licença ativa.
- Renovação só a partir de status **Vencido**.

---

## Dependências

- [usuarios](USUARIOS.md): ambulante, gestor, score, telas de parecer/exportação.
- [espacos](ESPACOS.md): ponto e estrutura.
- [core](CORE.md): geração/validação do QR.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/licenciamento/models.py` | Categoria, documento, licença, escala |
| `apps/licenciamento/services.py` | Requerimento, parecer, taxa, emissão, renovação |
| `apps/licenciamento/relatorios.py` | Indicadores, gráficos, planilha |
| `apps/licenciamento/views.py` | Credencial, alvará, triagem, categorias, arquivo |
| `apps/licenciamento/urls_web.py` | Rotas HTML e HTMX |
| `apps/licenciamento/urls.py` | API JWT do ambulante |
| `templates/gestor/relatorio_export.html` | Layout do PDF gerencial |
