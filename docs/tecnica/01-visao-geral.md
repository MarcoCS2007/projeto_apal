# 1. Visão geral do produto

## O que é o APAL

**APAL** significa “Aqui Pode, Aqui é Legal”. É o sistema da Prefeitura de Vitória da Conquista para **licenciar e fiscalizar o comércio ambulante**: o trabalhador se cadastra, a gestão analisa documentos e emite um alvará com QR Code, o fiscal valida isso na rua e o gestor acompanha indicadores e ocorrências.

Não é um site institucional solto. É uma **aplicação web Django** com quatro “mundos” no mesmo servidor:

| Mundo | Quem entra | Como entra |
| --- | --- | --- |
| Público | Qualquer visitante | `/`, `/sobre/`, `/faq/`, `/registro/` |
| Ambulante | Trabalhador | `/entrar/` (sessão) ou JWT no app |
| Fiscal | Agente de campo | `/fiscal/entrar/` ou JWT no app |
| Backoffice | Gestor e Administrador (Master) | `/login/` |

Os quatro mundos compartilham o **mesmo banco**. O que muda é o perfil do usuário e as telas/APIs liberadas.

## Os quatro perfis (atores)

O sistema não usa o `User` padrão do Django. Existe um modelo próprio, `UsuarioBase`, e **quatro subclasses** (herança em tabelas separadas):

1. **Ambulante** — pede licença, envia documentos, paga taxa simulada, imprime credencial, consulta o assistente, vê o score.
2. **Fiscal** — lê QR / busca CPF ou alvará, registra ocorrência com foto.
3. **Gestor** — triagem de documentos, parecer, emissão de alvará, dossiê, auditoria de autos, dashboard, catálogo de pontos e categorias.
4. **Administrador (Master)** — cadastra gestores e fiscais, matriz de permissões, logs da IA, backup.

Um CPF só pertence a **um** perfil. O login descobre o perfil pela subclasse (`user.role`).

## O ciclo que o código implementa

```text
Ambulante cria conta → completa cadastro (6 etapas) → anexa documentos → envia
        ↓
Gestor tria anexos → analisa requerimento → deferir / indeferir / pendência
        ↓
Ambulante confirma taxa (DAM simulado R$ 120)
        ↓
Gestor emite alvará (número ALV-…, escala, ponto Ocupado, QR HMAC)
        ↓
Ambulante mostra credencial  ·  Fiscal valida QR  ·  se irregular, lavra auto
        ↓
Gestor audita ocorrência (pode suspender/cancelar)  ·  dashboard e score atualizam
```

Tudo isso já está no ar (itens 2–17 da ordem de implantação). Web e app móvel **reutilizam as mesmas funções** de serviço: a API não duplica a regra, só devolve JSON.

## O que o sistema *não* é

- Não há um front-end React/Vue separado. As telas são **HTML gerado no servidor** (Django Templates) em `templates/`.
- A pasta `front/` guarda **protótipos estáticos** antigos. O que o usuário vê em produção/dev é `templates/` + `static/`.
- O assistente educativo **não chama ChatGPT**. A resposta sai de uma base local em `apps/core/ia.py`.
- O pagamento da taxa é **simulado** (`taxa_paga = True`). Não há gateway bancário.

## Mapa mental dos módulos

```text
config/          → “projeto Django”: urls, settings, wsgi
apps/core        → fundação: modelo base, QR, IA local, seed, backup
apps/usuarios    → quem é quem: login, cadastro, score, Master, gestor
apps/espacos     → onde: endereço, estrutura, ponto de ocupação
apps/licenciamento → o quê é autorizado: documentos, alvará, relatórios
apps/fiscalizacao  → o que aconteceu na rua: inspeção e ocorrência
apps/assistente    → dúvidas do ambulante + log para o Master
```

O próximo capítulo segue **uma request HTTP** até a view. A partir do capítulo 3 o texto abre o código: o que cada `if` decide, não só em que arquivo ele está.
