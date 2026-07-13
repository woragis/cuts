# Language and concurrency matrix

Locked guidance for the parallel-lane worker fleet. Prefer waiting style over fashion.

| Worker | Language | Why | Default `WORKER_CONCURRENCY` |
|--------|----------|-----|------------------------------|
| worker-control | Go | Ingest, metadata, fan-out — IO wait | 16 |
| worker-analyze | Go (+ thin Py) | Many LLM chunk waits | 16 |
| worker-plan | Python interim → Go | Hook plan = LLM HTTP | 8 |
| worker-transcribe | Python | Whisper / GPU-CPU heavy | 1 |
| worker-ffmpeg | Python | FFmpeg spine + mux | 2 |
| worker-visual | TypeScript / Node | Remotion + Chromium | 1 |
| worker-audio | Python | loudnorm / mix | 2 |
| worker-thumbnail | Go | Image API waits + light ffmpeg | 32 |
| worker-publish | Go | Platform uploads | 8 |
| worker-notify | Go | Telegram / SMTP | 16 |

## Rules

- Scale **replicas** for transcribe / visual / ffmpeg before raising per-box concurrency.
- **Defer Rust** — only a later media helper if profiling proves a hot path.
- Runtime caps live in `backend/server/internal/workerruntime` and Redis `cuts:runtime:limits`.

## Queues

See [CUT-TREATMENT-PIPELINE.md](./CUT-TREATMENT-PIPELINE.md) and [WORKER-RENAMES.md](./WORKER-RENAMES.md).
