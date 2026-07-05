# Railway — Máquina de Cortes (multi-service)

Um **Railway Project** com Postgres + Redis + serviços da stack. Use **reference variables** `${{Service.VAR}}` — no mesmo project elas resolvem pela **rede privada** (`*.railway.internal`).

## Nomes sugeridos dos serviços

Renomeie no dashboard para bater com os exemplos (case-sensitive):

| Serviço Railway | Repo / build | Notas |
|-----------------|--------------|-------|
| `Postgres` | plugin | `${{Postgres.DATABASE_URL}}` (privado entre services) |
| `Redis` | plugin | `${{Redis.REDIS_URL}}` |
| `api` | `cuts-machine-backend` | Go API |
| `frontend` | `cuts-machine-frontend` | Next.js |
| `scheduler` | `cuts-scheduler` | 1 réplica |
| `worker-general` | `cuts-worker-general` | Go; ver nota Python abaixo |
| `worker-analyze` … | submodules Python | **build context = monorepo** `cuts-machine` |
| `worker-notification` | `cuts-worker-notification` | monorepo root |
| `telegram-bot` | `backend/telegram-bot` | repo backend |
| `minio` | opcional | S3-compatible; ou use R2 com vars manuais |

## Como aplicar variáveis

1. Copie o `.env.railway.example` do serviço.
2. No Railway → serviço → **Variables** → **RAW Editor** → cole o conteúdo.
3. Ajuste nomes em `${{...}}` se seus services tiverem outros nomes.
4. Secrets reais (API keys) → preferir **Settings UI** do app; env só como fallback.

## Rede privada (service → service)

```env
# API a partir de outro serviço no mesmo project:
CUTS_API_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}

# Postgres / Redis (service-to-service, sem egress):
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

`RAILWAY_PRIVATE_DOMAIN` só funciona **em runtime** dentro do container — não em build nem no browser.

Frontend Next.js: chame a API via URL **pública** (`NEXT_PUBLIC_API_URL` em `frontend/railway.env.example`), não `*.railway.internal`.

## Build context monorepo (workers Python)

Dockerfiles em `worker-analyze/`, `worker-render/`, etc. fazem `COPY backend/worker/...`.

No Railway:

- Conecte o serviço ao repo **`cuts-machine`** (monorepo).
- Root Directory: `/` (raiz do monorepo).
- `railway.toml` em cada pasta define `dockerfilePath = "worker-analyze/Dockerfile"`.

## worker-general + Python delegate

`scheduling.plan` ainda delega para Python. Opções:

1. Deploy **monorepo** com Dockerfile custom que copia `backend/worker` para `/python-worker`.
2. Ou desativar delegate quando `scheduling.plan` for portado para Go.

## Checklist pós-deploy

- [ ] Migrations 019 + 020 no Postgres
- [ ] Todos os workers + scheduler + notification + telegram-bot running
- [ ] `/ops` mostra filas e heartbeats
- [ ] Settings → Telegram / Email test
