# Worker rename map (GitHub)

Local paths and GitHub remotes are aligned (renamed 2026-07-13):

| Path | GitHub repo |
|------|-------------|
| `worker-control` | `cuts-worker-control` |
| `worker-plan` | `cuts-worker-plan` |
| `worker-ffmpeg` | `cuts-worker-ffmpeg` |
| `worker-notify` | `cuts-worker-notify` |
| `worker-visual` | `cuts-worker-visual` |

Keep: analyze, transcribe, audio, thumbnail, publish.

Re-run after auth issues: `./scripts/rename-worker-repos.sh`

## Redis queue defaults

| Queue | Default | Env (preferred) | Legacy env fallback |
|-------|---------|-----------------|---------------------|
| plan | `cuts:jobs:plan` | `REDIS_QUEUE_PLAN` | `REDIS_QUEUE_TREATMENT` |
| ffmpeg | `cuts:jobs:ffmpeg` | `REDIS_QUEUE_FFMPEG` | `REDIS_QUEUE_RENDER` |
| visual | `cuts:jobs:visual` | `REDIS_QUEUE_VISUAL` | — |
| audio | `cuts:jobs:audio` | `REDIS_QUEUE_AUDIO` | — |

## Archived labs

- `woragis/render` (archived)
- `woragis/render-editly` (archived)
