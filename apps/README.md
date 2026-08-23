## 🏗️ Estrutura e Arquitetura de Apps

O sistema foi desenhado de forma modular, dividindo as responsabilidades em aplicativos focados em domínios específicos. Essa abordagem centraliza regras de negócio, evita duplicação de código e facilita a manutenção.

Os apps instalados estão em `config/settings/base.py`: `core`, `usuarios`, `licenciamento`, `espacos`, `fiscalizacao` e `assistente`. Não há apps separados de financeiro, notificações, analytics ou relatórios.

Abaixo estão os módulos que compõem o projeto:

### ⚙️ `core` (Fundação do Sistema)
Atua como o alicerce do projeto, abrigando recursos globais que são importados e reutilizados por diversas *views* e APIs de outros aplicativos.
- **Modelos Abstratos:** `ModeloBase` (campos `criado_em`, `atualizado_em` e `ativo`) herdado pela maioria das entidades.
- **Utilitários Compartilhados:** gerador/validador HMAC do QR Code, PNG da credencial, base local do assistente (`ia.py`), backup JSON e seeds (`seed_inicial`, `seed_massivo`).
- **Permissões Customizadas:** `IsAmbulante`, `IsFiscal`, `IsGestor`, `IsAdministrador` para a API JWT.
- **Páginas públicas:** home, sobre, FAQ, privacidade; handlers 404/500.

### 👥 `usuarios` (Autenticação e Perfis)
Gerencia o núcleo de autenticação, o controle de acesso e os painéis por perfil.
- **Modelos associados:** `UsuarioBase`, `Ambulante`, `Fiscal`, `Gestor`, `Administrador`, `EventoScore`, `ConfiguracaoSeguranca`, `LogAcessoDossie`.
- **Telas:** login por canal, wizard de cadastro, perfil do ambulante, score, Master, dossiê e exportações do gestor.

### 📄 `licenciamento` (Gestão Legal)
Responsável pelo ciclo de vida da autorização de trabalho, documentos comprobatórios, taxa e relatórios gerenciais.
- **Modelos associados:** `LicencaAlvara`, `CategoriaProduto`, `DocumentoAnexo`, `EscalaTrabalho`.
- **Regras:** requerimento, parecer, cálculo da taxa (`metragem × fator financeiro`), emissão, renovação e indicadores.

### 📍 `espacos` (Mapeamento Geográfico)
Isola a lógica espacial: endereço residencial, equipamento de trabalho e vagas municipais.
- **Modelos associados:** `Endereco`, `EstruturaTrabalho`, `PontoOcupacao`.

### 🚨 `fiscalizacao` (Operações de Rua)
Módulo dedicado à rotina dos agentes de campo: inspeção de QR/CPF/alvará e lavratura de autos.
- **Modelos associados:** `OcorrenciaInspecao` (tipos, status e evidência fotográfica).

### 🤖 `assistente` (IA Educativa)
Gerencia o chatbot educativo (base local, sem API externa) e o histórico auditável pelo Master.
- **Modelos associados:** `LogAssistente`.
