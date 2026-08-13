# Documentação do APAL

O APAL (Aqui Pode, Aqui é Legal) é o sistema municipal de licenciamento e gestão de comércio ambulante. A documentação está **separada por módulo** (`apps/`), com o propósito do domínio, as telas, as regras e o passo a passo de uso.

## Módulos

| Módulo | Pasta | Documento | Quem usa no dia a dia |
| --- | --- | --- | --- |
| Fundação | `apps/core` | [CORE.md](CORE.md) | Equipe de desenvolvimento |
| Usuários e acessos | `apps/usuarios` | [USUARIOS.md](USUARIOS.md) | Ambulante, fiscal, gestor e Master |
| Licenciamento | `apps/licenciamento` | [LICENCIAMENTO.md](LICENCIAMENTO.md) | Ambulante e gestor |
| Espaços | `apps/espacos` | [ESPACOS.md](ESPACOS.md) | Gestor (cadastro de pontos) |
| Fiscalização | `apps/fiscalizacao` | [FISCALIZACAO.md](FISCALIZACAO.md) | Fiscal de rua e gestor |
| Assistente de IA | `apps/assistente` | [ASSISTENTE.md](ASSISTENTE.md) | Ambulante (consulta) e Master (auditoria) |

## Outros guias

| Documento | Conteúdo |
| --- | --- |
| [API-AUTENTICACAO.md](API-AUTENTICACAO.md) | Contrato JWT (`/api/login/`, `/api/me/`) |
| [API-MOVEL.md](API-MOVEL.md) | App ambulante/fiscal (licença, QR, ocorrência) |
| [DEPLOY.md](DEPLOY.md) | Publicação em produção (Gunicorn, Docker, variáveis) |
| [../README.md](../README.md) | Como subir o projeto localmente (Docker, Git Flow, CI) |

## Como os módulos se encaixam

```text
Público (core)          → home, sobre, FAQ
     │
Usuários                → login, cadastro, painéis por perfil, score, Master
     │
     ├── Licenciamento  → documentos, fila, parecer, taxa, alvará, QR, relatórios
     ├── Espaços        → endereço, estrutura, ponto de ocupação
     ├── Fiscalização   → leitura de QR, ocorrência, auditoria
     └── Assistente     → pergunta educativa + log para o Master
```

O ciclo operacional típico:

1. O ambulante cria a conta e completa o cadastro (`usuarios` + `espacos` + `licenciamento`).
2. O gestor faz triagem dos documentos, deferimento e emissão do alvará.
3. O ambulante paga a taxa (simulada), imprime a credencial com QR e consulta o assistente.
4. O fiscal valida o QR em campo e, se preciso, registra ocorrência.
5. O gestor audita a ocorrência (pode suspender/cancelar a licença) e acompanha o dashboard.

## Contas de demonstração

Depois de `python manage.py seed_inicial` (ou equivalente no container):

| Perfil | CPF | Senha | Entrada |
| --- | --- | --- | --- |
| Administrador (Master) | `00000000000` | `admin123` | `/login/` |
| Gestor | `11111111111` | `gestor123` | `/login/` |
| Fiscal | `22222222222` | `fiscal123` | `/fiscal/entrar/` |
| Ambulante | `33333333333` | `amb123` | `/entrar/` |

Detalhes e demais usuários fictícios: [API-AUTENTICACAO.md](API-AUTENTICACAO.md).
