# Railway — Máquina de Cortes (multi-service)

Um **Railway Project** com Postgres + Redis + serviços da stack. Use **reference variables** `${{Service.VAR}}`.

## Importante: um repo por serviço worker

Cada worker é um **repositório Git próprio** (`cuts-worker-ffmpeg`, etc.). O monorepo `cuts-machine` usa **submodules** — o archive do Railway **não inclui** o conteúdo dos submodules, então paths como `worker-ffmpeg/Dockerfile` no monorepo **falham**.

**Configure cada serviço Railway assim:**

| Setting | Valor |
|---------|--------|
| Source repo | `woragis/cuts-worker-ffmpeg` (repo do worker) |
| Root Directory | `/` |
| Dockerfile Path | `Dockerfile` |

O `railway.toml` em cada repo já define `dockerfilePath = "Dockerfile"`.

## Nomes sugeridos dos serviços

| Serviço Railway | Repo GitHub | Stack |
|-----------------|-------------|-------|
| `Postgres` | plugin | — |
| `Redis` | plugin | — |
| `api` | `cuts-machine-backend` | Go |
| `frontend` | `cuts-machine-frontend` | Next.js |
| `scheduler` | `cuts-scheduler` | Go |
| `worker-control` | `cuts-worker-control` | Go |
| `worker-analyze` | `cuts-worker-analyze` | Go |
| `worker-publish` | `cuts-worker-publish` | Go |
| `worker-thumbnail` | `cuts-worker-thumbnail` | Go |
| `worker-transcribe` | `cuts-worker-transcribe` | Python |
| `worker-ffmpeg` | `cuts-worker-ffmpeg` | Python |
| `worker-notify` | `cuts-worker-notify` | Go |
| `worker-factory` | `cuts-worker-factory` | Go |
| `telegram-bot` | `cuts-machine-backend` | Python (`telegram-bot/Dockerfile`) |

## Build: repos privados

Dockerfiles clonam `cuts-machine-backend` e/ou `cuts-machine` em build time. Se os repos forem privados, adicione **Build Variable**:

```env
GITHUB_TOKEN=<PAT com read:packages ou repo>
```

## Variáveis de runtime

1. Copie o `.env.railway.example` do repo do serviço.
2. Railway → serviço → **Variables** → **RAW Editor**.
3. Ajuste nomes em `${{...}}` se seus services tiverem outros nomes.

## Rede privada

```env
CUTS_API_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

## Local (docker-compose)

```bash
docker compose -f backend/docker-compose.yml build worker-ffmpeg
```

Cada serviço usa `context: ../worker-XXX` — mesmo Dockerfile que o Railway.

## Concurrency por stage

| Stage | `WORKER_CONCURRENCY` default |
|-------|------------------------------|
| general | 4 |
| analyze | 16 |
| publish | 8 |
| thumbnail | 8 |
| notification | 8 |
| render | 1 |
| transcribe | 1–2 |

## Checklist pós-deploy

- [ ] Cada worker aponta para **seu repo**, não o monorepo
- [ ] `GITHUB_TOKEN` se repos privados
- [ ] Workers + scheduler + notification running
- [ ] `/ops` mostra filas e heartbeats
