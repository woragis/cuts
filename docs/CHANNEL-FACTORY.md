# Channel factory

Weekly (or manual) niche generator with **SQL/JSONB authority** — no proposal JSON files.

## Placement

| Piece | Role |
|--------|------|
| API | CRUD `visual_identities`, `channel_proposals`; approve / reject / materialize; `POST /v1/channel-factory/run`; `POST .../generate-assets` |
| Scheduler | If `CHANNEL_FACTORY_ENABLED=1`, once per ISO week inserts `factory_runs` and enqueues **one** `channel.factory.tick` |
| `worker-factory` | Consumes `cuts:jobs:factory` (concurrency 1). Research + propose → SQL; assets → kit-locked PNGs in blob |

## Schema

- `visual_identities.spec` **jsonb** — design kits (seeded in migration `025`)
- `channel_proposals` — `research_snapshot`, `pitch`, `bootstrap_draft`, `live_watch_draft`, `model_meta`, `assets_meta` as **jsonb**
- `channel_proposals.assets_status` — `none` \| `queued` \| `running` \| `ready` \| `failed` \| `skipped`
- `factory_runs` — period gate + research snapshot

Blob is **only** for PNG binaries (`channels/{treatmentSlug}/logo.png`, `watermark.png`, `thumbnail-pattern.png`).

## Materialize

Approved proposals call existing catalog + live_watch import services and create a treatment channel stub. Humans still attach OAuth accounts.

Materialize also enqueues `channel.factory.assets`:

1. Load kit `spec` (palette / motif / `promptLocks` / surfaces)
2. `gpt-image-2` generations with locked prompts (no free-form style)
3. Near-white → alpha strip for logo + watermark (kit `bgPolicy`); watermark resized ~320×90
4. Put PNGs under `channels/{slug}/…` and patch treatment `config.factoryAssets`

## Env

| Var | Where |
|-----|--------|
| `CHANNEL_FACTORY_ENABLED` | scheduler |
| `REDIS_QUEUE_FACTORY` | api / scheduler / worker (default `cuts:jobs:factory`) |
| `CHANNEL_FACTORY_MAX_PROPOSALS` | default 5 |
| `GEMINI_API_KEY` / `SERPER_API_KEY` | worker-factory (propose) |
| `OPENAI_API_KEY` / `OPENAI_IMAGE_MODEL` | worker-factory (assets) |
| `S3_*` / `DATA_DIR` | worker-factory blob puts |

UI: `/factory`
