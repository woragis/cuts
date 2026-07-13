# Channel factory

Weekly (or manual) niche generator with **SQL/JSONB authority** — no proposal JSON files.

## Placement

| Piece | Role |
|--------|------|
| API | CRUD kits/proposals; approve / reject / materialize; `generate-assets`; `enrich`; `POST /v1/channel-factory/run` |
| Scheduler | If `CHANNEL_FACTORY_ENABLED=1`, once per ISO week inserts `factory_runs` and enqueues **one** `channel.factory.tick` |
| `worker-factory` | `cuts:jobs:factory` — research/propose → enrich (yt-dlp) → assets (kit-locked PNGs) |

## Schema

- `visual_identities.spec` **jsonb** — design kits (seeded in migration `025`)
- `channel_proposals` — drafts + `assets_meta` as **jsonb**; `assets_status` for asset pipeline
- `factory_runs` — period gate + research snapshot

Blob is **only** for PNG binaries (`channels/{treatmentSlug}/logo.png`, `watermark.png`, `thumbnail-pattern.png`) and seeded `templates/{id}/pattern.png`.

## Flow

1. **Tick / propose** — Serper + Gemini → `INSERT channel_proposals`
2. **Enrich (phase 3)** — yt-dlp channel `/videos` listing → refine `live_watch_draft` scheduleDays / startLocal / titleContains / avgDurationMinutes (cookies from `settings/youtube/cookies.txt` when present). Soft-fail per URL.
3. Human **approve** → **materialize** (catalog + live_watch import + treatment stub)
4. **Assets (phase 2)** — kit-locked `gpt-image-2` → white-strip → channel PNGs → seed thumbnail template + patch treatment `config.assets` / `watermark` / `templateDefaults`
5. Treatment **final** step overlays `watermark.png` when present

## Env

| Var | Where |
|-----|--------|
| `CHANNEL_FACTORY_ENABLED` | scheduler |
| `REDIS_QUEUE_FACTORY` | api / scheduler / worker (default `cuts:jobs:factory`) |
| `CHANNEL_FACTORY_MAX_PROPOSALS` | default 5 |
| `GEMINI_API_KEY` / `SERPER_API_KEY` | worker-factory (propose) |
| `OPENAI_API_KEY` / `OPENAI_IMAGE_MODEL` | worker-factory (assets) |
| `YTDLP_BIN` | worker-factory (enrich; image includes `yt-dlp`) |
| `S3_*` / `DATA_DIR` | worker-factory blob puts |

UI: `/factory`
