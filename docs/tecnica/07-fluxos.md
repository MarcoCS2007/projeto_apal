# 7. Um ciclo completo no código

Esta é a história de um ambulante seed (Maria) até o fiscal recusar o QR fora do horário. Cada passo aponta a **decisão** no código, não só a URL.

---

## Passo 1 — Conta

`CadastroAmbulanteForm.save` cria `Ambulante` com senha hasheada e, no mesmo `create_user`, `aceite_lgpd=True`, `aceite_lgpd_em=timezone.now()`, `base_legal_lgpd="execucao_politicas_publicas"`. Sem o checkbox, `is_valid()` falha e **nenhuma** linha nasce.

`RegistroAmbulanteView.form_valid` chama `login(..., backend="apps.usuarios.backends.CPFOuEmailBackend")` para a sessão já nascer com o backend certo (senão o Django pode reclamar de múltiplos backends). Redirect: `/ambulante/`.

Nesse momento `cadastro_completo` é False: não há endereço nem estrutura. O painel cai no `{% else %}` “Complete seu cadastro”.

---

## Passo 2 — Seis POSTs no mesmo `CadastroCompletoAmbulanteView`

Cada POST traz `etapa` escondido no form. A view escolhe a classe em `ETAPAS_CADASTRO`, valida, `form.save()`.

- Etapa 1: dados pessoais (nascimento, gênero, renda, escolaridade, telefones, NIS). Foto 3x4 fica em `/ambulante/perfil/`.
- Etapa 2: o form cria/atualiza `Endereco` com `related_name="enderecos"`. A propriedade `cadastro_completo` passa a ver `.enderecos.exists()`.
- Etapa 3: CNPJ/MEI e nome fantasia. Sem CNPJ, a flag `sem_cnpj` vai para o JSON.
- Etapa 4: `tipo_atuacao` + `EstruturaTrabalho` com `dimensoes_metragem`. Se o usuário mandar 0, o form recusa — a propriedade também recusaria.
- Etapa 5: queryset do campo ponto já vem filtrado para Livre. O form ainda compara metragem com o ponto escolhido. `gravar_categoria_pretendida` escreve `categoria_id` no JSON do ambulante — é isso que `tipos_obrigatorios` lerá na etapa 6 (laudo sanitário se a categoria exigir).
- Etapa 6 + `acao=enviar`: `form.save()` grava anexos; a view recarrega o ambulante; se `cadastro_completo`, chama `abrir_requerimento`. O segundo retorno `True` dispara a mensagem com o protocolo. Redirect para `ambulante_alvara`, não para o painel — o critério de pronto do item 6 era o trabalhador **ver** o `REQ-`.

Clicar Enviar de novo: `requerimento_em_aberto` acha a mesma linha, devolve `False`, a view não cria `REQ-0002`.

---

## Passo 3 — Triagem

O gestor abre `/gestor/triagem/`. A query é “todos os anexos Pendente”. POST aprovar: `documento.aprovar()` zera motivo e grava Aprovado. A licença continua Em Análise — **documentos aprovados não mudam o status do requerimento**. Só destravam o deferimento.

POST rejeitar sem texto: `ValidationError`, HTMX recebe 400. Com texto: status da licença vira Pendência. O painel da Maria mostra `documentos_rejeitados` porque o `get_context_data` filtrou `status_aprovacao="Rejeitado"`.

Ela reenvia o arquivo: `reenviar` volta Pendente e, se era o único rejeitado, `reabrir_analise_se_sem_rejeicoes` devolve Em Análise. A fila `/gestor/fila/` usa `STATUS_FILA`; os dois status aparecem lá, Pendência inclusive, para o gestor não “perder” o processo.

---

## Passo 4 — Deferir não é emitir

`GestorAnalisarLicencaView.post` valida `ParecerLicencaForm` e chama `aplicar_parecer`. Se o ponto da Praça 9 já tiver outra Ativa, a mensagem de erro volta **no mesmo template** (`render`, não redirect) para o gestor não perder o form.

Deferer com sucesso: `messages.success` + `redirect("gestor_emitir", pk=licenca.pk)`. Status Aprovado. `pode_emitir` agora é True. `qr_valido` ainda é False (não está Ativo). A credencial da Maria, se ela abrir agora, **não** mostra QR: a view da credencial exige `licenca_ativa` + `validar_codigo_qr`.

Maria pode confirmar a taxa: `simular_pagamento_taxa` checa `aguardando_taxa` e `licenca.ambulante_id == ambulante.pk` (não pagar a taxa da vizinha). Seta `taxa_paga=True`. O valor já foi gravado no deferimento (`metragem × fator`). Continua sem HMAC.

---

## Passo 5 — Emissão

O form de emitir manda dias da semana + um par de horários. `emitir_alvara` trava o ponto, grava `ALV-2026-00xx`, Ativo, escalas, HMAC em `codigo_qr_code`, +10 no score.

Se outro gestor emitir no mesmo ponto na mesma fração de segundo, `select_for_update` serializa. O segundo toma `ValidationError` de ponto ocupado.

`GestorEmitirAlvaraView` só mostra o form se `pode_emitir`. Abrir a URL de uma licença já Ativa mostra a página sem form — não dá para “reemitir” e gerar segundo QR por acidente.

---

## Passo 6 — Credencial

`CredencialAmbulanteView` chama `licenca_ativa` (que internamente marca vencidas). Monta `qr_liberado` só se:

- existe Ativa,
- `qr_valido`,
- tem `codigo_qr_code`,
- `validar_codigo_qr` não devolve None.

O `<img src="{% url 'ambulante_credencial_qr' %}">` bate na view PNG. Sem `qr_liberado`, essa URL 404. O hash impresso no PNG **é** o mesmo string HMAC, não um payload JSON. O fiscal lê 64 hex.

---

## Passo 7 — Fiscal fora do horário

O fiscal cola o hex em `/fiscal/?qr=...`. `FiscalizacaoView.get` chama `inspecionar_qr`.

Hoje é domingo, a escala foi seg–sáb 08:00–18:00. `esta_fora_do_horario` não acha intervalo para `domingo` → True. Resultado: `valido=False`, `motivo=fora_horario`, mas `licenca` e `ambulante` preenchidos. A ficha `_ficha.html` ainda mostra nome e alvará. O atalho para ocorrência já manda `tipo=Irregularidade de horário` via `tipo_sugerido`.

`RegistrarOcorrenciaView.form_valid` chama `registrar_ocorrencia` com o `request.user` (precisa existir linha `Fiscal` com aquele pk). Status **Registrada**. Score **ainda não** muda.

---

## Passo 8 — Gestor marca procedente

`auditar_ocorrencia` verifica se `Procedente` está em `transicoes_permitidas("Registrada")` — está. Grava o status. Como o destino é Procedente, chama `pontuar_ocorrencia_procedente` (−20, chave por id da ocorrência) e, se o form não pediu outra ação, `aplicar_efeito_licenca(..., "suspender")`: todas as Ativas da Maria viram Suspenso e entra −15 (chave inclui a pontuação daquele instante).

`qr_valido` passa a False pelo status. A credencial some o PNG. `inspecionar_qr` agora devolve motivo `suspenso` mesmo com o HMAC correto: o compare_digest ainda acha a licença, mas `_ficha_da_licenca` olha o status novo.

Improcedente **não** chama score nem suspende. Convertida em multa só é legal a partir de Procedente (dicionário `TRANSICOES_STATUS`).

---

## Passo 9 — Dashboard bate com o banco

`indicadores_gerenciais` chama `marcar_licencas_vencidas`, conta Ativas/Vencidas/fila, agrupa pontos por bairro, conta ocorrências no período e monta o retrato sociodemográfico (`genero`, faixa etária, escolaridade, renda). Não há array mockado no template. Filtros extras: `cidade`, `genero`, `faixa`, `escolaridade`. Se o filtro `origem=itinerantes` entra, `_aplicar_origem` restringe a `tipo_atuacao="movel"`. Lotação ≥ 90% preenche `alerta_lotacao` com o primeiro bairro que cruzar a linha.

A API `/api/relatorios/ocupacao/` reusa a mesma função e corta o dicionário em `indicadores_json` (sem querysets). Excel e PDF (`/gestor/dashboard/exportar.xlsx` e `.pdf`) chamam `indicadores_da_request` e geram o arquivo. Os gráficos do dashboard pedem JSON em `/gestor/dashboard/chart-data/`.

---

## Onde o app móvel entra nessa história

Maria no celular: `POST /api/login/` → `LoginSerializer` coloca `role=ambulante` no token. `GET /api/ambulante/solicitacao/` chama `licencas_do_ambulante` / `serializar_licenca` — os mesmos objetos do passo 4. O fiscal no app: `GET /api/fiscal/qr/?codigo=` → `inspecionar_qr` do passo 7, serializado. `POST /api/fiscal/ocorrencias/` → `registrar_ocorrencia` do passo 7.

Não existe um segundo motor. Se o status no app diverge do site, o bug está no dado ou num serializer que omitiu campo, não em “outra regra”.

---

## Como debugar um passo que “não aconteceu”

| Sintoma | O que olhar no código |
| --- | --- |
| Enviar não gera protocolo | `cadastro_completo` False? `abrir_requerimento` retornou `(None, False)`? Já havia fila? |
| Deferir recusa | `tipos_faltando_aprovacao` ainda tem itens? Ponto não Livre? m²? |
| Credencial sem QR | `pode_emitir` já era False (não emitiu)? `taxa_paga` não emite sozinha. Status não Ativo? |
| Taxa zerada ou estranha | Categoria sem `fator_financeiro`? Estrutura sem metragem no deferimento? |
| QR “adulterado” | `SECRET_KEY` mudou? `numero_licenca` alterado na mão? Hash truncado na câmera? |
| Score não andou | `chave` repetida? `ambulante` None na ocorrência? Já no piso 0? |
| Assistente genérico | tokens só de stopword, ou nenhum trecho pontuou > 0 |

Abra a função do capítulo 6 correspondente e siga os `if` com os dados reais no admin ou no shell (`python manage.py shell`).
