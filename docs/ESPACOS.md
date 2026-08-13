# Módulo Espaços — Pontos, estruturas e endereços

Pasta: `apps/espacos`

Isola o cadastro geográfico e físico: onde o ambulante mora, com que equipamento trabalha e quais vagas municipais existem na rua.

---

## Para que serve

- Guardar o endereço residencial do ambulante (obrigatório para cadastro completo).
- Registrar a estrutura de trabalho (carrinho, barraca, food truck etc.) e a metragem em m².
- Catalogar pontos de ocupação (vagas) com capacidade máxima e status.
- Impedir dois alvarás ativos no mesmo ponto e estrutura maior do que o limite da vaga.

---

## Modelos

### `Endereco`

CEP, logradouro, número, complemento, bairro, cidade e UF, ligados ao ambulante (`related_name="enderecos"`). Preenchido na etapa 2 do cadastro.

### `EstruturaTrabalho`

Tipo, metragem (`dimensoes_metragem`), foto e descrição. O cadastro só é considerado completo se existir estrutura com tipo e metragem **maior que zero**. Na emissão, essa metragem é comparada com `metragem_maxima` do ponto.

### `PontoOcupacao`

| Campo | Uso |
| --- | --- |
| `nome_identificacao` | Nome amigável (ex.: Praça Central) |
| `logradouro` / `bairro` | Localização |
| `coordenadas` | Texto livre (lat,long no seed) |
| `metragem_maxima` | Teto em m² para a estrutura |
| `status_ocupacao` | Livre, Ocupado, Bloqueado, Reservado |

Métodos:

| Método | Comportamento |
| --- | --- |
| `disponivel_para_nova_atribuicao()` | Ativo, status Livre e **sem** licença Ativa |
| `ocupar()` | Status → Ocupado (chamado na emissão) |
| `liberar_se_livre()` | Volta a Livre se não houver licença Ativa |
| `metragem_compativel(m)` | `m <= metragem_maxima` |
| `tem_licenca_ativa()` | Existe `LicencaAlvara` Ativa neste ponto |

O queryset `PontoOcupacao.objects.livres()` filtra `ativo=True` e status Livre.

O ambulante escolhe um `ponto_pretendido` no cadastro; o gestor pode trocar o ponto no parecer/emissão, desde que esteja livre.

---

## Rotas

`apps/espacos/urls_web.py` — somente backoffice:

| URL | Método | Função |
| --- | --- | --- |
| `/gestor/pontos/` | GET/POST | Listar e cadastrar |
| `/gestor/pontos/<id>/` | GET/POST | Editar |
| `/gestor/pontos/<id>/excluir/` | POST | Inativa (`ativo=False`) |

Exclusão é lógica. Ponto com **licença ativa** não pode ser excluído.

Endereço e estrutura **não** têm URL própria: entram pelo wizard `/ambulante/cadastro/` (módulo usuarios).

---

## Instruções de uso

### Gestor — cadastrar uma vaga

1. Entre no backoffice e abra **Pontos** (`/gestor/pontos/`).
2. Preencha identificação, logradouro, bairro, metragem máxima e, se quiser, coordenadas.
3. O status inicial deve ser **Livre** para o ponto aparecer na escolha do ambulante e no deferimento.
4. Use **Bloqueado** quando a via estiver interditada (o ponto deixa de ser atribuível).
5. Para corrigir, abra o ponto na lista; para remover, exclua apenas se não houver alvará Ativo.

O seed (`python manage.py seed_inicial`) já cria pontos no Centro e em outros bairros de Vitória da Conquista.

### Ambulante — informar endereço, estrutura e ponto

No cadastro completo:

1. **Etapa 2** — endereço. Sem ele o cadastro não fecha.
2. **Etapa 4** — tipo de estrutura, metragem em m² e foto. Se a metragem for maior que a do ponto escolhido, o gestor verá alerta e **não conseguirá deferir** naquele ponto.
3. **Etapa 5** — escolha um ponto **Livre** do catálogo e a categoria de produto.

Depois disso, quem ocupa ou libera o ponto é a emissão / vencimento da licença, não o ambulante.

### Gestor — o que conferir no parecer

- Ponto ainda **Livre** e sem outra licença Ativa.
- Metragem da estrutura ≤ máximo do ponto.
- Se precisar, troque o ponto no formulário de análise antes de deferir.

Quando o alvará é emitido o ponto passa a **Ocupado**. Quando a licença vence (ou é cancelada e não resta outra ativa), `liberar_se_livre()` devolve a vaga.

---

## Dependências

- Referenciado por [usuarios](USUARIOS.md) (`Ambulante.ponto_pretendido`) e pelo cadastro.
- Referenciado por [licenciamento](LICENCIAMENTO.md) na licença (ponto + estrutura).
- Relatórios de ocupação por bairro usam `status_ocupacao`.

---

## Arquivos de referência

| Arquivo | Papel |
| --- | --- |
| `apps/espacos/models.py` | Endereço, estrutura, ponto |
| `apps/espacos/forms.py` | Formulário de ponto |
| `apps/espacos/views.py` | CRUD do gestor |
| `apps/espacos/urls_web.py` | Rotas `/gestor/pontos/` |
| `templates/gestor/gerenciar-pontos.html` | Tela |
