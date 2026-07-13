# Channel factory

Weekly (or manual) niche generator with **SQL/JSONB authority** — no proposal JSON files.

## Placement

| Piece | Role |
|--------|------|
| API | CRUD `visual_identities`, `channel_proposals`; approve / reject / materialize; `POST /v1/channel-factory/run` |
| Scheduler | If `CHANNEL_FACTORY_ENABLED=1`, once per ISO week inserts `factory_runs` and enqueues **one** `channel.factory.tick` |
| `worker-factory` | Consumes `cuts:jobs:factory` (concurrency 1). Research (Serper) + propose (Gemini) → `INSERT channel_proposals` |

## Schema

- `visual_identities.spec` **jsonb** — design kits (seeded in migration `025`)
- `channel_proposals` — `research_snapshot`, `pitch`, `bootstrap_draft`, `live_watch_draft`, `model_meta` as **jsonb**
- `factory_runs` — period gate + research snapshot

Blob is only for future PNG assets (phase 2).

## Materialize

Approved proposals call existing catalog + live_watch import services and create a treatment channel stub. Humans still attach OAuth accounts.

## Env

| Var | Where |
|-----|--------|
| `CHANNEL_FACTORY_ENABLED` | scheduler |
| `REDIS_QUEUE_FACTORY` | api / scheduler / worker (default `cuts:jobs:factory`) |
| `CHANNEL_FACTORY_MAX_PROPOSALS` | default 5 |
| `GEMINI_API_KEY` / `SERPER_API_KEY` | worker-factory |

UI: `/factory`
