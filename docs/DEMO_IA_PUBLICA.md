# Guia de Demonstração: Assistente de IA Público (Mock Engine)

O Assistente Consultor da APAL é uma ferramenta interativa simulada (mock) adicionada à página inicial pública do sistema (`/`). Seu propósito principal é ilustrar o valor agregado da Inteligência Artificial em consultas públicas e orientações sem a necessidade de login. 

Este documento detalha o roteiro ideal de demonstração (Pitch/Showcase) da ferramenta para partes interessadas (stakeholders), prefeituras ou investidores.

## 🌟 Onde encontrar
Na página pública (Home) do sistema, localizada no canto inferior direito da tela, você verá um **Botão Flutuante (FAB)** com um ícone de brilho (✨). 
Basta clicar nele para abrir ou fechar a janela de diálogo do Assistente.

## 🎭 Como funciona o Motor de Simulação (Mock Engine)
A IA não está integrada a uma API externa de LLM (como OpenAI ou Gemini) nesta interface pública para evitar custos e abusos. Em vez disso, ela funciona no Front-end (JavaScript) identificando **palavras-chave (gatilhos)** na pergunta enviada e respondendo com casos de uso cruciais da APAL. A interface simula de maneira realista:
- A mensagem *"Analisando..."* junto com uma animação de digitação de 3 pontinhos.
- Um delay (atraso) randômico de 1.2 a 1.8 segundos imitando latência de processamento de rede/banco de dados.
- O scroll automático do histórico de mensagens acompanhando a evolução da conversa.

## 📝 Roteiro de Demonstração (Scripts de Pitch)

Para garantir uma demonstração fluida e apresentar o recurso com segurança (sem falhas na extração de gatilhos), digite frases que contenham as **palavras-chave** descritas abaixo. 

---

### Cenário 1: Consulta de Oportunidades de Venda
**Objetivo da Demonstração:** Mostrar como a IA ajuda o ambulante a tomar decisões de negócio baseadas em dados do município (evitando áreas saturadas e explorando bairros com alta demanda).

🗣️ **O que o apresentador pode digitar:**
- *"Onde é o melhor lugar para vender espetinho?"*
- *"Quero vender lanche, qual local você recomenda?"*
- *"Onde posso vender comida?"*

🤖 **O que a IA vai responder:**
> *"Analisando os registros do município: Os bairros **Candeias** e **Patagônia** possuem atualmente a menor densidade de vendedores de alimentação cadastrados, representando uma excelente oportunidade de faturamento. Evite o **Centro**, que já conta com alta saturação."*

*(Gatilhos ativados pelo código: "onde", "melhor lugar" ou "local" combinados com "espetinho", "lanche", "comida" ou "vender")*

---

### Cenário 2: Análise de Saturação de um Bairro Específico
**Objetivo da Demonstração:** Mostrar que a IA também atua no sentido reverso, avaliando um local que o usuário já escolheu e sugerindo categorias comerciais carentes na região.

🗣️ **O que o apresentador pode digitar:**
- *"O que eu posso vender na Olívia Flores?"*
- *"Qual produto vender no Candeias?"*
- *"O que vender no Centro da cidade?"*

🤖 **O que a IA vai responder:**
> *"Na **Av. Olívia Flores**, já temos alta concentração de barracas de alimentação e bebidas. Recomendamos investir em segmentos com demanda reprimida no local, como **Artesanato** e **Artigos Sazonais**."*

*(Gatilhos ativados pelo código: "olivia flores", "candeias" ou "centro" combinados com "o que vender" ou "produto")*

---

### Cenário 3: Tira-dúvidas Burocrático / Legislação
**Objetivo da Demonstração:** Destacar a IA como uma facilitadora da burocracia pública, guiando o usuário passo a passo com clareza antes mesmo dele iniciar um cadastro.

🗣️ **O que o apresentador pode digitar:**
- *"Quais são os documentos para tirar o alvará?"*
- *"Tem alguma taxa para atestado?"*
- *"Como funciona para pedir meu alvará provisório?"*

🤖 **O que a IA vai responder:**
> *"Para obter o alvará provisório, você precisará apresentar RG/CPF, comprovante de residência e laudo sanitário (apenas para comércio de alimentos). O processo pode ser iniciado 100% online pela nossa aba de cadastro."*

*(Gatilhos ativados pelo código: "taxa", "alvara", "alvará", "documento" ou "atestado")*

---

### Cenário 4: Interação Genérica (Boas-vindas ou Fallback)
**Objetivo da Demonstração:** Mostrar a resiliência do robô ao receber mensagens curtas ou termos não mapeados nos gatilhos acima.

🗣️ **O que o apresentador pode digitar:**
- *"Olá"*
- *"Tudo bem?"*
- *"Oi, como você funciona?"*

🤖 **O que a IA vai responder:**
> *"Olá! Sou o Assistente Consultor da APAL. Posso te orientar sobre quais bairros possuem maior demanda para o seu produto ou tirar dúvidas sobre a legislação municipal. Como posso te ajudar hoje?"*

---

## 💡 Dicas Adicionais para uma Apresentação de Sucesso
1. **Comece quebrando o gelo (Cenário 4):** Mande um *"Olá"*. Isso força o sistema a listar imediatamente suas próprias capacidades.
2. **Sincronize sua fala com o Delay:** Use o atraso simulado de ~1.5s entre o envio da pergunta e a resposta do chat para explicar como essa inteligência desonera os canais de suporte humano da prefeitura.
3. **Erros de Digitação não quebram o código:** O JavaScript valida as palavras-chave usando `includes` e normaliza tudo para *lowercase*. Logo, desde que as palavras-chave raízes (ex: "vender", "alvará", "centro") existam dentro da string e sem erros ortográficos na própria raiz, a IA saberá contextualizar corretamente a resposta.
