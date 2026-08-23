# 6. Algoritmos do domínio — ler a função até o fim

Aqui não há lista de arquivos. Cada seção pega **uma função** e explica o que cada ramo decide. São essas funções que a web e a API compartilham.

---

## 6.1 Checklist de documentos: por que o gestor não consegue deferir

`tipos_obrigatorios` começa sempre com comprovante de residência e RG/CPF. Depois **soma** exigências:

- Se `ambulante.cnpj` está preenchido → entra MEI.
- Se a categoria tem `exige_laudo_sanitario` → laudo sanitário.
- Se tem `exige_laudo_bombeiros` → laudo de bombeiros.

A categoria vem de `categoria_do_ambulante`: primeiro o JSON `dados_complementares["categoria_id"]` (escolha da etapa 5); se vazio, a categoria da última `LicencaAlvara`. Sem categoria, só os tipos básicos.

`tipos_faltando_aprovacao` percorre essa lista e pergunta: existe `DocumentoAnexo` daquele tipo **e** `status_aprovacao == Aprovado`? Qualquer buraco entra na lista.

`pode_avancar_solicitacao` é `not tipos_faltando_aprovacao(...)`. O parecer de deferir chama exatamente isso. Aprovar na triagem não muda o status da licença sozinho: só faz aquele tipo deixar de “faltar”. Enquanto houver um obrigatório Pendente ou Rejeitado, `aplicar_parecer(..., "deferir")` levanta `ValidationError` com os nomes amigáveis (`TipoDocumento.RG_CPF.label` → “RG/CPF”).

Rejeitar é mais agressivo: `DocumentoAnexo.rejeitar` grava o motivo e chama `marcar_pendencia_documental`, que faz `licencas.filter(status=Em Análise).update(status=Pendência)`. Reenviar chama `reabrir_analise_se_sem_rejeicoes`: se **ainda** existir outro documento Rejeitado, a licença permanece em pendência. Só quando a última rejeição some é que volta Em Análise.

---

## 6.2 Abrir requerimento: não nascer dois protocolos

```135:158:apps/licenciamento/services.py
@transaction.atomic
def abrir_requerimento(ambulante, categoria=None):
    """Cria (ou reaproveita) um requerimento Em Análise para o ambulante."""
    from apps.licenciamento.models import LicencaAlvara

    existente = requerimento_em_aberto(ambulante)
    if existente:
        return existente, False
    if not ambulante.cadastro_completo:
        return None, False

    estrutura = ambulante.estruturas.order_by("id").first()
    if estrutura is None:
        return None, False

    categoria = categoria or categoria_do_ambulante(ambulante)
    licenca = LicencaAlvara.objects.create(
        ambulante=ambulante,
        estrutura_trabalho=estrutura,
        ponto_ocupacao=ambulante.ponto_pretendido,
        categoria_produto=categoria,
        status=StatusLicenca.EM_ANALISE,
    )
    return licenca, True
```

`requerimento_em_aberto` busca status em `STATUS_FILA` (Em Análise e Pendência). O segundo valor do retorno (`True`/`False`) diz se **criou** ou **reaproveitou**. A view do wizard usa isso para não mostrar “protocolo novo” quando o ambulante clica Enviar de novo.

Se o cadastro não está completo, `(None, False)` — a view trata como erro de formulário, não como bug de banco.

`objects.create` dispara o `save()` do model, que gera `REQ-{ano}-{pk}`. Ponto e categoria nesta hora são os **pretendidos**; o gestor pode trocar os dois no parecer.

---

## 6.3 Parecer: três ações, um funil

`aplicar_parecer` recusa se a licença já saiu da fila (já Aprovada, Ativa, Indeferida…). Sem isso, um segundo POST deferiria de novo.

Depois aplica ponto/categoria opcionais do form. Trocar de ponto só é permitido se o novo `disponivel_para_nova_atribuicao()`. `_gestor_do_usuario` resolve o `Gestor` pelo mesmo pk (MTI).

Os três ramos:

**Indeferir** — justificativa obrigatória; status Indeferido; acabou. Não mexe no ponto.

**Pendência** — justificativa obrigatória; status Pendência Documental. O ambulante vê o motivo no painel.

**Deferer** — não aceita outro string. Aí vêm as travas duras, nesta ordem:

1. Checklist de documentos (`pode_avancar_solicitacao`).
2. Tem ponto?
3. Ponto livre de verdade (`disponivel_para_nova_atribuicao`).
4. Metragem da estrutura ≤ máximo do ponto.
5. Tem categoria?

Só então `status = Aprovado` e `valor_taxa = metragem × fator_financeiro`. **Não** gera `ALV-`, **não** ocupa o ponto, **não** gera QR. Isso é de propósito: o produto separa “parecer técnico” de “emissão com validade e escala”. A view de análise, se a ação foi deferir, redireciona para `/gestor/emitir/<id>/`.

---

## 6.4 Emitir alvará: o momento em que o mundo muda

Leia `emitir_alvara` como uma transação única (`@transaction.atomic`). Se qualquer `ValidationError` subir, ponto e QR não ficam pela metade.

**Guarda 1 — ainda pode emitir?** `licenca.pode_emitir` exige Aprovado e `numero_licenca` vazio. Chamar a função duas vezes na mesma linha falha na segunda.

**Guarda 2 — datas e escala.** Vencimento tem que ser depois da emissão; precisa de pelo menos um dia; horário fim > início. São regras de formulário repetidas no service para a API/admin não furarem o form HTML.

**Guarda 3 — ponto com cadeado.** `PontoOcupacao.objects.select_for_update().get(pk=...)` trava a linha no Postgres até o `commit`. Dois gestores emitindo ao mesmo tempo para o mesmo ponto: o segundo espera e depois vê o ponto já ocupado / com licença Ativa.

Se o ponto do form é outro que o da licença, valida disponibilidade e metragem de novo (o gestor pode ter trocado na tela de emissão).

**Escrita:**

1. Datas, número `ALV-{ano}-{pk:04d}`, status **Ativo**, parecer concatenado com observações.
2. `licenca.save()`.
3. `ponto_atual.ocupar()` → `status_ocupacao = Ocupado`.
4. Apaga escalas antigas e cria uma `EscalaTrabalho` por dia, mesmo `horario_inicio`/`horario_termino` (o form atual não admite horário diferente por dia).
5. `ambulante.codigo_qr_code = gerar_codigo_qr(licenca)` — ver 6.5.
6. `pontuar_licenca_ativa` — +10 com chave `licenca_ativa:{pk}` para não repetir.

O QR fica no **ambulante**, não na tabela da licença. A validação depois procura o ambulante pelo hash e confere se o HMAC ainda corresponde à licença Ativa.

---

## 6.5 HMAC do QR: por que não é um UUID

```11:14:apps/core/qrcode.py
def gerar_codigo_qr(licenca):
    mensagem = f"apal:licenca:{licenca.pk}:{licenca.numero_licenca or ''}"
    return hmac.new(_chave_secreta(), mensagem.encode(), hashlib.sha256).hexdigest()
```

HMAC-SHA256 com a `SECRET_KEY` do Django. Entrada: prefixo fixo + id da licença + número oficial. Mesma licença + mesma chave = **sempre o mesmo** hex de 64 caracteres. Por isso a credencial pode regenerar o PNG sem gravar a imagem no banco.

Não é UUID aleatório porque o fiscal precisa **recomputar** o hash e comparar. UUID só provaria “eu tenho este código no banco”; HMAC prova “este código foi gerado com o segredo da prefeitura para *esta* licença”.

`hmac.compare_digest` (na validação e na inspeção) compara em tempo constante — evita timing attack de ir parando no primeiro byte diferente.

`validar_codigo_qr` (credencial) é binário: acha o ambulante com aquele `codigo_qr_code`, pega a licença Ativa mais recente, recomputa o HMAC, exige `qr_valido`. Qualquer falha → `None` → a view do PNG dá 404. Ela **não** explica se está vencido ou adulterado. Quem explica é a fiscalização.

Trocar `SECRET_KEY` no servidor invalida **todos** os QR já impressos: o hash novo não bate com o gravado.

---

## 6.6 Inspeção: classificar o fracasso

`inspecionar_qr` não devolve só sim/não.

1. Código vazio → motivo `vazio`.
2. `marcar_licencas_vencidas()` — Ativo com data passada vira Vencido **antes** de julgar.
3. Nenhum ambulante com esse `codigo_qr_code` → `adulterado` (hash inventado ou de outro ambiente).
4. Percorre as licenças do ambulante, mais recente primeiro, e para na primeira cujo `gerar_codigo_qr(candidata)` tem o mesmo tamanho e passa no `compare_digest`. Se nenhuma → `adulterado` mesmo tendo achado o ambulante (hash antigo, chave mudou, número de alvará alterado).
5. `_ficha_da_licenca` olha o **status atual**:
   - Suspenso → `valido=False`, motivo `suspenso`, mas ainda devolve a ficha (o fiscal vê quem é).
   - Vencido ou `not qr_valido` → `vencido` ou `invalido`.
   - Ativo porém `esta_fora_do_horario` → `fora_horario`, `valido` continua False, `fora_horario=True`.
   - Senão → `valido=True`.

`esta_fora_do_horario`: se não há escalas, devolve False (não pune quem foi emitido sem grade — não deveria acontecer após o item 8). Senão pega `timezone.localtime()` (Bahia), `weekday()` 0=segunda alinhado com `DIAS_SEMANA_ORDEM`, e testa se **alguma** escala daquele dia contém a hora atual. Fora de todos os intervalos → True.

`consultar_campo` é o mesmo julgamento depois de achar a licença por outro caminho: 32+ caracteres trata como QR; senão tenta `numero_licenca`; senão CPF de 11 dígitos; senão nome (até 8 candidatos). Vários nomes → `motivo=varios` para a tela pedir escolha. Sem licença emitida → `sem_licenca`.

`tipo_sugerido` mapeia motivo → tipo de auto (`fora_horario` → irregularidade de horário, etc.) para o form já abrir preenchido.

---

## 6.7 Score: teto, piso e chave

```80:102:apps/usuarios/score.py
def registrar_evento_score(ambulante, tipo, descricao, chave=""):
    if ambulante is None:
        return None
    chave = (chave or "").strip()
    if chave and EventoScore.objects.filter(ambulante=ambulante, chave=chave).exists():
        return None
    delta = PONTOS[tipo]
    atual = ambulante.pontuacao
    novo = max(PONTUACAO_MIN, min(PONTUACAO_MAX, atual + delta))
    aplicado = novo - atual
    evento = EventoScore.objects.create(...)
    if aplicado:
        ambulante.pontuacao = novo
        ambulante.save(update_fields=["pontuacao", "atualizado_em"])
    return evento
```

Leitura:

- Sem ambulante (ocorrência de não identificado) → não pontua.
- Se a `chave` já existe para aquele ambulante → **não cria evento e não soma**. Emitir o mesmo alvará duas vezes (se alguém furasse `pode_emitir`) não daria +20.
- `delta` vem do dicionário `PONTOS` (+10, +8, −20, −15, −25).
- `novo` é grampeado em 0–100. Se o saldo é 5 e a multa é −20, `aplicado` vira −5, não −20. O extrato mostra o que **de fato** saiu, não a regra bruta.
- Se `aplicado == 0` (já estava no teto e veio +10), o evento ainda é gravado com `pontos=0`, mas o `save` do ambulante é pulado.

`faixa_score` percorre `FAIXAS` do Diamante (90) ao Bronze (0) e para na **primeira** cujo `minimo <= pontos`. Por isso 90 é Diamante, 89 é Ouro. “Faltam N para a próxima” usa a faixa imediatamente acima.

Quem chama o registrador nunca passa o inteiro na mão: `pontuar_licenca_ativa` monta a chave `licenca_ativa:{licenca.pk}`. Suspensão usa `suspensa:{ambulante.pk}:{pontuacao}` — inclui o saldo para **permitir** uma segunda suspensão futura pontuar de novo (senão a chave fixa bloquearia para sempre).

---

## 6.8 Assistente: não é uma rede neural

`consultar_conhecimento` não chama API. Faz busca por sobreposição de palavras.

1. `_normalizar` — minúsculas e tira acento (`renovação` = `renovacao`).
2. `_tokens` — quebra em palavras, joga fora stopwords (`de`, `para`, `quais`) e tokens de 1 letra.
3. Para cada `TrechoConhecimento` da tupla `BASE_CONHECIMENTO`, `_pontuar`:
   - token bate numa **tag** → +4
   - bate no **título** → +2
   - bate no **corpo** → +1
   - bônus +8 se o trecho é `documentos_alimentos` e a pergunta mistura comida **e** documento (senão “documento” sozinho ganharia o trecho genérico).
4. Fica com o trecho de maior pontuação. Empate: o **primeiro** da tupla que alcançou aquele máximo (não há desempate sofisticado).
5. Zero pontos → texto `_FALLBACK` pedindo para reformular.

`responder_pergunta` só recusa string vazia, chama isso e dá `LogAssistente.objects.create` com `fonte=resultado.fonte` (o título do trecho). O Master lê essa tabela; a “IA” do widget de acessibilidade no `script.js` é outro recurso (texto da página), não este log.

Para ensinar um tema novo: acrescente um `TrechoConhecimento` com tags que o ambulante realmente digitaria. Sem tag boa, a pergunta cai no fallback.

---

## 6.9 Vencimento preguiçoso

`marcar_licencas_vencidas` lista Ativas com `data_vencimento < hoje`, dá `update` em lote para Vencido, e para cada ponto distinto chama `liberar_se_livre()`. Não há cron. Quem dispara: credencial, `licenca_ativa`, inspeção, dashboard. Testes de “amanhã a licença vence” precisam chamar essa função ou bater numa view que chama.

---

O próximo capítulo costura esses algoritmos na ordem em que o usuário clica, com o que a view passa para cada um.
