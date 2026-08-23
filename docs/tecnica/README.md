# Documentação técnica do APAL

Este conjunto ensina a **ler o código** do APAL. Não é um índice de arquivos: cada capítulo abre trechos reais, explica o que o Python/HTML/SQL está fazendo e por que a decisão está ali.

Leia na ordem na primeira vez. Os capítulos 3–7 são o miolo (banco, views, templates e algoritmos).

## Capítulos

| # | Capítulo | O que você aprende |
| --- | --- | --- |
| 1 | [Visão geral do produto](01-visao-geral.md) | Para que o APAL existe e o ciclo operacional |
| 2 | [Arquitetura: o caminho de uma request](02-arquitetura.md) | Stack, pastas e o que o Django faz com um GET/POST |
| 3 | [Banco e models](03-banco-de-dados.md) | Como as classes viram tabelas e como as propriedades decidem status |
| 4 | [Back-end: views e APIs](04-backend.md) | Mixins, wizard de cadastro, JWT, por que a regra não fica na view |
| 5 | [Front-end: templates](05-frontend.md) | `extends`, context e como o HTML consome o que a view calculou |
| 6 | [Algoritmos do domínio](06-funcoes-reutilizadas.md) | QR, parecer, emissão, inspeção, score e assistente, passo a passo |
| 7 | [Um ciclo completo no código](07-fluxos.md) | Do “Enviar cadastro” até o fiscal recusar o QR |
| 8 | [Guia do iniciante](08-guia-do-iniciante.md) | Onde mexer quando for alterar comportamento |

## Como usar estes capítulos

Quando o texto cita um trecho, abra o arquivo no editor e acompanhe linha a linha. O objetivo é você conseguir responder sozinho: *“se eu mudar isso, o que quebra?”*

Documentos de **uso operacional** (botões, URLs por perfil) continuam em `docs/USUARIOS.md`, `docs/LICENCIAMENTO.md`, etc. Contratos HTTP: `docs/API-AUTENTICACAO.md` e `docs/API-MOVEL.md`.
