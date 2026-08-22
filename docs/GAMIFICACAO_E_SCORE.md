# Módulo de Gamificação e Gestão de Score

Este documento detalha todas as implementações, modificações estruturais e regras de negócio aplicadas no sistema APAL para a criação e automação do módulo de Gamificação e Gestão de Score dos ambulantes.

## 1. Visão Geral das Regras de Negócio Implementadas

A gamificação visa incentivar boas práticas através de um sistema de pontuação de 0 a 100, onde todos os ambulantes iniciam com 100 pontos.

### Categorias e Consequências
* **Diamante (100 a 90 pontos):** Operação normal. (Privilégios adicionais poderão ser aplicados, como isenção de taxas).
* **Ouro (89 a 70 pontos):** Operação normal.
* **Prata (69 a 40 pontos):** Estado de alerta. O ambulante visualiza um alerta vermelho em seu painel informando que sua licença está sob observação.
* **Bronze / Suspensão Temporária (39 a 1 ponto):** Licença suspensa (Status: `Suspenso`). O ambulante não pode operar na rua. A credencial digital (QR Code) se torna visível na cor vermelha com o aviso "LICENÇA SUSPENSA / PROIBIDO OPERAR".
* **Cassado (0 pontos):** Licença revogada permanentemente.

### Perda e Ganho de Pontos
* **Penalidades por Infrações:** Pontos são deduzidos automaticamente quando o Gestor aprova uma Ocorrência de Inspeção vinculada a uma infração. A quantidade de pontos depende da gravidade (Leve: -5, Média: -10, Grave: -20, Gravíssima: -40).
* **Recuperação de Pontos (Mensal/Tempo):** Se o ambulante passar um período (configurável, padrão de 30 dias) sem novas infrações aprovadas, ele recebe +2 pontos de bonificação, até o limite de 100 pontos.
* **Manutenção da Licença:** Manteve-se a regra de bônus por renovação (+5) e ativação de licença (+10), que também foram integradas.

---

## 2. Arquivos Editados e Funcionalidades Adicionadas

### Banco de Dados e Modelos
* `apps/fiscalizacao/models.py`:
  * Criação do modelo `CatalogoInfracao` (descrição, gravidade, pontos de desconto).
  * Adição dos campos `infracao` (ForeignKey nula) e `status_gestor` (Pendente, Aprovada, Rejeitada) no modelo `OcorrenciaInspecao`.
* `apps/usuarios/models.py`:
  * Adição da propriedade `nivel_score` no modelo `Ambulante`, que calcula e retorna a categoria (Diamante, Ouro, Prata, Bronze, Cassado).
  * Adição do campo `dias_recuperacao_score` no modelo global `ConfiguracaoSeguranca` para o Administrador controlar a janela de tempo da recuperação mensal.
* `apps/licenciamento/models.py`:
  * Alteração da property `qr_valido` do modelo `LicencaAlvara` para retornar `True` mesmo quando a licença estiver com status `Suspenso`, permitindo que o fiscal escaneie o crachá e veja a suspensão.

### Lógica de Pontuação e Serviços
* `apps/usuarios/score.py` (Novo arquivo):
  * Funções centrais: `pontuar_infracao`, `pontuar_renovacao`, `pontuar_licenca_ativa`.
  * `processar_ocorrencia`: Calcula e deduz os pontos, mudando o status da licença para `Suspenso` (se pontuação < 40) ou `Cancelado` (se pontuação == 0).
  * `verificar_recuperacao_mensal`: Lê a política no banco (`dias_recuperacao_score`), varre os ambulantes elegíveis e adiciona +2 pontos caso não existam infrações recentes. Retorna a quantidade de ambulantes afetados.
* `apps/fiscalizacao/services.py`:
  * Refatoração da função `auditar_ocorrencia` para o gestor. Ao aprovar uma infração, chama a `processar_ocorrencia` da lógica de gamificação.
  * O cancelamento/suspensão manual por parte do gestor foi substituído pela automação baseada na gravidade da infração.

### Comandos de Automação e Jobs
* `apps/core/management/commands/recuperacao_score.py` (Novo Comando):
  * Script CLI (`python manage.py recuperacao_score`) que executa a `verificar_recuperacao_mensal()`. Pode ser inserido em um Cron Job (ex: `0 0 1 * *` para rodar no primeiro dia de cada mês).
* `apps/core/management/commands/seed_inicial.py` e `scripts/seed_massivo.py`:
  * Atualizados para pré-popular a tabela `CatalogoInfracao` e vincular essas infrações na criação de ocorrências falsas de teste.

### Visões (Views) e Formulários (Forms)
* `apps/usuarios/forms.py`:
  * Atualização do `ConfiguracaoSegurancaForm` para incluir o campo de dias de recuperação de score.
* `apps/fiscalizacao/forms.py`:
  * Criação do `CatalogoInfracaoForm`.
  * Modificação do `AuditoriaOcorrenciaForm` para remover os campos antigos de cancelamento manual e adicionar um `ModelChoiceField` de infrações do catálogo.
* `apps/usuarios/views_gestor.py`:
  * Atualização da `GestorOcorrenciaDetalheView` para suportar as decisões baseadas no novo workflow.
  * Criação da `GestorProcessarScoreView` que permite o acionamento manual do script de recuperação de pontos através de um botão no painel.
* `apps/usuarios/views.py`:
  * Atualização da `PainelAmbulanteView` para buscar não só a licença "Ativa", mas também a "Suspensa" para montar a credencial visual vermelha.
* `apps/usuarios/urls_web.py`:
  * Adição da rota `gestor/score/processar/` para a nova funcionalidade.

### Interface Gráfica e Templates (UX/UI)
* `templates/master/gerenciar-permissoes.html`: 
  * Inserção do campo de configuração `dias_recuperacao_score` no Painel do Administrador (TI).
* `templates/backoffice_inicio.html`: 
  * Criação da seção "Ações Globais" com um botão para processar a recuperação de score diretamente pelo dashboard do Gestor.
* `templates/ambulante/painel.html`: 
  * Adição de blocos de alerta (Callout vermelho) exibidos quando o ambulante entra no nível Prata ou Bronze/Cassado.
* `templates/ambulante/_credencial_conteudo.html`: 
  * Regras visuais aplicadas: Se a licença estiver Suspensa (Bronze), todo o fundo, as bordas, e o gradiente do crachá digital mudam para vermelho. É adicionada a tag `LICENÇA SUSPENSA / PROIBIDO OPERAR` onde ficava a prefeitura.
* `templates/gestor/ocorrencia-detalhe.html`:
  * Renderiza dinamicamente as `_regras_score.html` listando como a tabela de pontuação funciona e permitindo o envio do form com a infração.

---

## 3. Checklist de Testes (Para validação no dia seguinte)

Esta é a lista de testes rigorosos que devem ser feitos para homologar a versão final em produção:

- [ ] **1. Teste de Auditoria e Redução de Pontos:**
  * Acesse o perfil Gestor, crie uma ocorrência no nome de um ambulante com 100 pontos.
  * Audite a ocorrência selecionando uma Infração "Grave" (-20).
  * O score do ambulante deve cair para 80 pontos (Nível Ouro).
  
- [ ] **2. Teste de Transição para o Status Bronze (Suspenso):**
  * Submeta o mesmo ambulante a múltiplas infrações Gravíssimas até que o score fique entre 39 e 1.
  * Verifique se o nível mudou para Bronze.
  * Verifique se a licença (`LicencaAlvara`) dele alterou o status para `Suspenso`.

- [ ] **3. Teste de Interface Prata e Bronze:**
  * Acesse o Painel do Ambulante com o usuário testado no passo anterior (Bronze).
  * Valide se o banner vermelho superior está visível relatando a suspensão.
  * **Verifique a Credencial:** O QR Code deve carregar. A credencial inteira (frente e verso) deve estar em tons de vermelho com a mensagem "Proibido Operar".
  * Suba a pontuação de um ambulante para 50 (no Django Admin ou shell). Veja se o Painel dele mostra o "Alerta Prata".

- [ ] **4. Teste da Recuperação de Pontos (Botão do Gestor):**
  * Com o ambulante do teste anterior possuindo ocorrências de "hoje", clique no botão *"Rodar Recuperação Mensal de Score"* no Dashboard do Gestor.
  * Como a ocorrência é de hoje, o ambulante **não** deve ganhar 2 pontos. O gestor receberá a mensagem que X ambulantes foram processados (só os elegíveis).
  * Edite a data da Ocorrência Inspecao do ambulante no Django Admin para 40 dias no passado (ex: `-40 days`).
  * Clique novamente no botão do Gestor. O ambulante agora deve recuperar +2 pontos (se estava com 30, deve ir para 32).

- [ ] **5. Teste da Configuração do Admin (TI):**
  * Acesse o painel Master (Administrador).
  * Vá em Permissões Globais e altere a janela de recuperação de 30 para 15 dias. Salve.
  * Simule uma infração de 20 dias atrás.
  * Rode novamente o botão do Gestor. O ambulante deverá recuperar pontos, confirmando que a variável do banco está sendo respeitada.

- [ ] **6. Teste do Comando no Terminal (Cron):**
  * Rode no terminal: `make cmd="python manage.py recuperacao_score"`.
  * Verifique se o output printa no console o número de ambulantes bonificados de forma correta e limpa.

- [ ] **7. Teste de Cassação (0 Pontos):**
  * Faça as auditorias caírem até o ambulante ficar com 0 pontos ou menos (O código possui uma trava com `max(0, ...)` e `min(100, ...)` mas é bom validar).
  * O Status dele deve ser Cassado e a Licença deve estar como `Cancelado` (revogação permanente).
