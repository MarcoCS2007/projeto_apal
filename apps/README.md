## 🏗️ Estrutura e Arquitetura de Apps

O sistema foi desenhado de forma modular, dividindo as responsabilidades em aplicativos focados em domínios específicos. Essa abordagem centraliza regras de negócio, evita duplicação de código e facilita a manutenção.

Abaixo estão os módulos que compõem o projeto:

### ⚙️ `core` (Fundação do Sistema)
Atua como o alicerce do projeto, abrigando recursos globais que são importados e reutilizados por diversas *views* e APIs de outros aplicativos.
- **Modelos Abstratos:** Classes base, como um `TimeStampedModel` (contendo campos de auditoria como `criado_em` e `atualizado_em`), que servem de herança para quase todas as entidades do sistema.
- **Utilitários Compartilhados (Utils):** Funções globais, incluindo o gerador de hash único para o QR Code das credenciais, funções de formatação de CPF/CNPJ e scripts de integração com a API da Inteligência Artificial (RAG).
- **Permissões Customizadas:** Centralização das classes de permissão (ex: `IsFiscal`, `IsGestor`) que gerenciam a herança complexa de perfis de usuário (Master, Gestor, Fiscal, Ambulante).

### 👥 `usuarios` (Autenticação e Perfis)
Gerencia o núcleo de autenticação, o controle de acesso e a relação de dados residenciais e comerciais.
- **Modelos associados:** Usuário Base, Ambulante, Fiscal, Gestor, Administrador e Endereço.

### 📄 `licenciamento` (Gestão Legal)
Responsável por todo o ciclo de vida da autorização de trabalho, auditoria de documentos comprobatórios e cadastro detalhado dos equipamentos utilizados.
- **Modelos associados:** Licença / Alvará, Estrutura de Trabalho, Categoria de Produto, Documento Anexo e Escala de Trabalho.

### 📍 `espacos` (Mapeamento Geográfico)
Isola toda a lógica de organização espacial, mapeamento geográfico, zoneamento urbano e o controle da capacidade máxima das vias.
- **Modelos associados:** Ponto de Ocupação, Vagas e Coordenadas.

### 🚨 `fiscalizacao` (Operações de Rua)
Módulo dedicado à rotina operacional dos agentes de campo, facilitando o registro de ações fiscalizatórias, notificações e vistorias de forma ágil.
- **Modelos associados:** Ocorrência / Inspeção e Multas.

### 🤖 `assistente` (IA Educativa)
Focado no principal diferencial do projeto, gerenciando e armazenando o histórico de interações do chatbot educativo inteligente.
- **Modelos associados:** Log Assistente.