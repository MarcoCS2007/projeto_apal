# Documentação do APAL

O APAL (Aqui Pode, Aqui é Legal) é o sistema municipal de licenciamento e gestão de comércio ambulante.

Há dois jeitos de ler a docs:

1. **[Documentação técnica](tecnica/README.md)** — capítulos sobre back-end, front-end, banco e funções reutilizadas. Comece por aqui se você é desenvolvedor novo no repositório.
2. **Módulos abaixo** — como usar cada painel no dia a dia (URLs, perfis, regras de tela).

## Módulos

| Módulo | Pasta | Documento | Quem usa no dia a dia |
| --- | --- | --- | --- |
| Fundação | `apps/core` | [CORE.md](CORE.md) | Equipe de desenvolvimento |
| Usuários e acessos | `apps/usuarios` | [USUARIOS.md](USUARIOS.md) | Ambulante, fiscal, gestor e Master |
| Licenciamento | `apps/licenciamento` | [LICENCIAMENTO.md](LICENCIAMENTO.md) | Ambulante e gestor |
| Espaços | `apps/espacos` | [ESPACOS.md](ESPACOS.md) | Gestor (cadastro de pontos) |
| Fiscalização | `apps/fiscalizacao` | [FISCALIZACAO.md](FISCALIZACAO.md) | Fiscal de rua e gestor |
| Assistente de IA | `apps/assistente` | [ASSISTENTE.md](ASSISTENTE.md) | Ambulante (consulta) e Master (auditoria) |

Não existem apps separados de financeiro, notificações, analytics ou relatórios: indicadores, taxa e exportações ficam em `licenciamento`; backup e seed ficam em `core`.

## Outros guias

| Documento | Conteúdo |
| --- | --- |
| [tecnica/README.md](tecnica/README.md) | Documentação técnica em 8 capítulos |
| [API-AUTENTICACAO.md](API-AUTENTICACAO.md) | Contrato JWT (`/api/login/`, `/api/me/`) |
| [API-MOVEL.md](API-MOVEL.md) | App ambulante/fiscal (licença, QR, ocorrência) |
| [BACKUP.md](BACKUP.md) | Dump JSON, restauração e retenção LGPD |
| [DEPLOY.md](DEPLOY.md) | Publicação em produção (Gunicorn, Docker, variáveis) |
| [../README.md](../README.md) | Como subir o projeto localmente (Docker, Git Flow, CI) |

## Como os módulos se encaixam

```text
Público (core)          → home, sobre, FAQ, privacidade, 404/500
     │
Usuários                → login, cadastro, perfil, painéis, score, Master, LGPD
     │
     ├── Licenciamento  → documentos, fila, parecer, taxa, alvará, QR, relatórios
     ├── Espaços        → endereço, estrutura, ponto de ocupação
     ├── Fiscalização   → leitura de QR, ocorrência, auditoria
     └── Assistente     → pergunta educativa + log para o Master
```

O ciclo operacional típico:

1. O ambulante cria a conta, completa o cadastro e, se quiser, ajusta e-mail/CPF/foto em **Meu perfil**.
2. O gestor faz triagem dos documentos, deferimento (com cálculo da taxa) e emissão do alvará.
3. O ambulante paga a taxa (simulada), imprime a credencial com QR e consulta o assistente.
4. O fiscal valida o QR em campo e, se preciso, registra ocorrência.
5. O gestor audita a ocorrência (pode suspender/cancelar a licença), acompanha o dashboard e exporta relatórios.

## Contas de demonstração

Depois de `python manage.py seed_inicial` (ou equivalente no container):

| Perfil | CPF | Senha | Entrada |
| --- | --- | --- | --- |
| Administrador (Master) | `52998224725` | `admin123` | `/login/` |
| Gestor | `11144477735` | `gestor123` | `/login/` |
| Fiscal | `12345678909` | `fiscal123` | `/fiscal/entrar/` |
| Ambulante | `10020030088` | `amb123` | `/entrar/` |

Para volume de dados nos gráficos: `python manage.py seed_massivo` (atalho: `make seed_massivo`).

Detalhes e demais usuários fictícios: [API-AUTENTICACAO.md](API-AUTENTICACAO.md).
