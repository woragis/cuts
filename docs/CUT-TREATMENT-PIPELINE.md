# Cut treatment pipeline (SQL + parallel lanes)

Greenfield target after wipe. Artifacts live in Postgres; media in blob.

## Sequence (lanes)

```text
extract → silence → hook
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 PICTURE   AUDIO      META (early)
 captions∥  audio_prep
 effects
    ▼
 visual (mute)
    │
    ├─ thumbnail (from mute; no wait mux)
    └─ mux ← mixed.m4a
         │
      publish ← final + thumb + meta
```

## Workers (names + language)

| Worker | Queue | Lang | Role |
|--------|-------|------|------|
| worker-control | cuts:jobs | Go | ingest, continue, metadata |
| worker-analyze | cuts:jobs:analyze | Go | cut finding |
| worker-transcribe | cuts:jobs:transcribe | Python | Whisper + cut captions |
| worker-plan | cuts:jobs:plan | Go/Py | hook.plan (LLM) |
| worker-ffmpeg | cuts:jobs:ffmpeg | Python | extract, silence, hook apply, mux |
| worker-visual | cuts:jobs:visual | TS/Node | Remotion mute + effects seed |
| worker-audio | cuts:jobs:audio | Python | audio_prep → m4a |
| worker-thumbnail | cuts:jobs:thumbnail | Go | thumbs (high concurrency) |
| worker-publish | cuts:jobs:publish | Go | uploads |
| worker-notify | cuts:notify | Go | telegram/email |

Legacy env fallbacks: `REDIS_QUEUE_TREATMENT` → plan, `REDIS_QUEUE_RENDER` → ffmpeg.


> **Note:** `metadata.generate` still runs on **worker-ffmpeg** (Python) until a Go port lands on worker-control. It is enqueued early and does not wait for Remotion/mux.

## SQL

Migration `024_cut_treatment_pipeline.sql`: `cut_treatments`, `cut_treatment_steps`, silence keeps/removals, hook plan/segments, `cut_visual_effects`, `cut_caption_words`.

Lane deps + regen invalidate: `backend/server/internal/treatmentlane`.

## Regen / enable API

- `GET /v1/runs/{id}/cuts/{cutId}/treatment`
- `PATCH /v1/runs/{id}/cuts/{cutId}/treatment/steps/{step}` body `{ "enabled": true|false }`
- `POST /v1/runs/{id}/cuts/{cutId}/treatment/steps/{step}/regenerate` — marks downstream stale and re-enqueues

See also [LANGUAGE-CONCURRENCY.md](./LANGUAGE-CONCURRENCY.md) and [WORKER-RENAMES.md](./WORKER-RENAMES.md).
