# Railway — Máquina de Cortes (multi-service)

Um **Railway Project** com Postgres + Redis + serviços da stack. Use **reference variables** `${{Service.VAR}}` — no mesmo project elas resolvem pela **rede privada** (`*.railway.internal`).

## Nomes sugeridos dos serviços

Renomeie no dashboard para bater com os exemplos (case-sensitive):

| Serviço Railway | Repo / build | Stack | Notas |
|-----------------|--------------|-------|-------|
| `Postgres` | plugin | — | `${{Postgres.DATABASE_URL}}` |
| `Redis` | plugin | — | `${{Redis.REDIS_URL}}` |
| `api` | `cuts-machine-backend` | Go | REST API |
| `frontend` | `cuts-machine-frontend` | Next.js | |
| `scheduler` | `cuts-scheduler` | Go | 1 réplica |
| `worker-general` | `cuts-worker-general` | Go | pydelegate para `scheduling.plan` |
| `worker-analyze` | `cuts-worker-analyze` | Go | **build context = monorepo** |
| `worker-publish` | `cuts-worker-publish` | Go | monorepo root |
| `worker-thumbnail` | `cuts-worker-thumbnail` | Go | monorepo root |
| `worker-transcribe` | `cuts-worker-transcribe` | Python | monorepo root |
| `worker-render` | `cuts-worker-render` | Python | monorepo root, concurrency 1 |
| `worker-notification` | `cuts-worker-notification` | Go | monorepo root |
| `telegram-bot` | `backend/telegram-bot` | Python | repo backend |
| `minio` | opcional | — | S3-compatible; ou R2 |

## Como aplicar variáveis

1. Copie o `.env.railway.example` do serviço.
2. No Railway → serviço → **Variables** → **RAW Editor** → cole o conteúdo.
3. Ajuste nomes em `${{...}}` se seus services tiverem outros nomes.
4. Secrets reais (API keys) → preferir **Settings UI** do app; env só como fallback.

## Rede privada (service → service)

```env
CUTS_API_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

`RAILWAY_PRIVATE_DOMAIN` só funciona **em runtime** dentro do container — não em build nem no browser.

Frontend Next.js: chame a API via URL **pública** (`NEXT_PUBLIC_API_URL`), não `*.railway.internal`.

## Build context (monorepo)

Workers Go e Python usam Dockerfiles que copiam paths do monorepo (`libs/go-pipeline`, `backend/worker`, etc.).

**Railway:** conecte o repo **`cuts-machine`** (monorepo) e configure por serviço:

| Setting | Exemplo worker-analyze |
|---------|------------------------|
| Root Directory | `/` (repo root) |
| Dockerfile Path | `worker-analyze/Dockerfile` |

Localmente:

```bash
docker compose -f backend/docker-compose.yml build worker-analyze
# ou
docker build -f worker-analyze/Dockerfile .
```

## Go workers + Python delegate

`worker-general`, `worker-analyze`, `worker-publish`, `worker-thumbnail` delegam handlers ainda não portados via `python -m cuts_worker...`.

Variáveis obrigatórias quando usa delegate:

```env
PYTHON_WORKER_ROOT=/python-worker
WORKER_STAGE=analyze   # ou general, publish, thumbnail
```

No compose local, `backend/worker` é montado em `/python-worker`. No Railway, inclua `backend/worker` na imagem (Dockerfile multi-stage ou build context monorepo).

## Concurrency por stage

| Stage | `WORKER_CONCURRENCY` default |
|-------|------------------------------|
| general | 4 |
| analyze | 16 |
| publish | 8 |
| thumbnail | 8 |
| notification | 8 |
| render | 1 (Python, síncrono) |
| transcribe | 1–2 |

Limites dinâmicos via Redis key `cuts:runtime:limits` (ver worker-general).

## Checklist pós-deploy

- [ ] Migrations no Postgres
- [ ] Todos os workers + scheduler + notification + telegram-bot running
- [ ] `/ops` mostra filas e heartbeats
- [ ] Settings → Telegram / Email test
