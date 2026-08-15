# Backup e restauração — APAL

O banco de produção é PostgreSQL (`config/settings/base.py`). Os dumps ficam em `backups/` (fora do Git) ou no caminho de `BACKUP_ROOT`.

## 1. Gerar backup

Pelo painel Master (Administrador com `acesso_painel_tecnico`): **Painel TI** (`/master/`) → **Gerar backup restaurável** (`POST /master/backup/`).

Pela linha de comando:

```bash
python manage.py backup_banco
python manage.py backup_banco --listar
```

O comando grava um JSON compatível com `loaddata` (funciona no Windows e no Docker). Em produção, prefira também um dump nativo do PostgreSQL:

```bash
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f backups/apal.dump
```

## 2. Restaurar

### Dump JSON do APAL

Em um banco vazio (após `migrate`):

```bash
python manage.py loaddata backups/apal_backup_AAAAMMDD_HHMMSS.json
```

### Dump nativo PostgreSQL

```bash
pg_restore --clean --if-exists -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB backups/apal.dump
```

Arquivos enviados pelos ambulantes (`MEDIA_ROOT`, pasta `media/`) devem ser copiados junto com o dump. Sem a mídia, os registros de `DocumentoAnexo` apontam para arquivos inexistentes.

## 3. Retenção LGPD

A política de meses está em `/master/permissoes/` (`retencao_logs_meses`). Para aplicar:

```bash
python manage.py purgar_retencao
```

Remove `LogAssistente` e `LogAcessoDossie` anteriores ao prazo configurado.
