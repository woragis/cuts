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

## SQL

Migration `024_cut_treatment_pipeline.sql`: `cut_treatments`, `cut_treatment_steps`, silence keeps/removals, hook plan/segments, `cut_visual_effects`, `cut_caption_words`.
