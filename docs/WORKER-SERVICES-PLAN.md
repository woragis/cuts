# Plano: separação de serviços (workers, scheduler, bots)

> **Branch:** `feat/worker-services-split`  
> **Status:** Fase 4 (scheduler Go) implementada — submodule `scheduler/` + docker-compose.  
> **Decisão:** `worker-general` passa a **Go** (goroutines + I/O); IA permanece **Python**.

---

## 1. Problema hoje

Tudo vive em `backend/worker/cuts_worker/` — um pacote Python com ~130 arquivos:

- Mesmo **Dockerfile** para general, analyze, render, publish, transcribe
- Mesmas **deps** (Gemini, Whisper, ffmpeg bindings, treatment…) em todo container
- **`handlers.py`** concentra orquestração + ingest + analyze + render
- Deploy lógico já separado (`WORKER_STAGE`), mas **código e imagem não**

```text
backend/
  server/          ← Go API
  worker/          ← Python monolith (todos os stages)
  scheduler/       ← dentro de worker/
  telegram-bot/
  orchestrator/    ← HTTP sidecar dentro de worker/
  migrations/
```

---

## 2. Visão alvo (monorepo)

Pastas de **top-level** no `maquina-de-cortes/` (ou equivalente dentro de `backend/` na transição):

```text
maquina-de-cortes/
├── api/                      # Go — REST, enqueue, preflight (hoje server/)
├── migrations/
├── contracts/                # job types, filas, envelope JSON (fonte única)
│
├── scheduler/                # Go — tick, recover_stale, live_watch, publish_plans
├── worker-general/           # Go — ingest, orquestração leve, fan-out paralelo
├── worker-analyze/           # Python — Gemini chunks, Claude merge (IA)
├── worker-transcribe/        # Python — transcribe.plan/chunk/merge (legendas)
├── worker-render/            # Python — FFmpeg render (Go shell futuro)
├── worker-thumbnail/         # Go shell (+ Python opcional para gpt-image)
├── worker-publish/           # Python — YouTube / TikTok / Instagram APIs
│
├── orchestrator/             # HTTP — scheduling IA (Python por enquanto)
├── telegram-bot/             # notificações Redis → Telegram
│
├── libs/
│   ├── go-pipeline/          # consumer, claim, envelope, pg, redis
│   └── py-pipeline/          # espelho mínimo para workers Python
│
└── frontend/
```

**Princípio:** um **serviço Railway / um Dockerfile** por pasta. Contrato compartilhado em `contracts/`.

---

## 3. Mapa completo de serviços

| Serviço | Fila Redis | Job types (hoje) | Stack alvo | Escala |
|---------|------------|------------------|------------|--------|
| **api** | enqueue only | — | Go | 1–2 instâncias |
| **scheduler** | all (recover) | — | **Go** | 1 instância |
| **worker-general** | `cuts:jobs` | ver §4 | **Go** | N instâncias, goroutines |
| **worker-analyze** | `cuts:jobs:analyze` + parte de general | gemini/transcript chunks | Python | N (API-bound) |
| **worker-transcribe** | `cuts:jobs:transcribe` | transcribe.* | Python | N (CPU/GPU) |
| **worker-render** | `cuts:jobs:render` | metadata, render.*, subtitle, outro | Go + py subprocess | N (CPU/RAM) |
| **worker-thumbnail** | `cuts:jobs:render` ou fila própria | thumbnail.* | Go + py IA | N |
| **worker-publish** | `cuts:jobs:publish` | publish.* | Go | baixo |
| **orchestrator** | — (HTTP) | scheduling tools | Python | 1 |
| **telegram-bot** | `cuts:notify` | — | Python/Go | 1 |

---

## 4. worker-general em Go — escopo

### Por que Go (e não manter Python)

A fila `general` hoje mistura **I/O paralelo** e **orquestração**:

| Job | Natureza | Go |
|-----|----------|-----|
| `ingest.youtube.download` | yt-dlp subprocess, S3, PG | ideal |
| `analyze.plan` | fan-out: enfileira N chunks | ideal (goroutines) |
| `analyze.gemini.url` | 1 chamada Gemini / URL | delegar → Python ou HTTP |
| `analyze.gemini.merge` | merge JSON leve | Go possível |
| `analyze.merge` | Claude merge | delegar → Python |
| `analyze.transcript` | Whisper path | delegar → Python |
| `transcribe.run` | Whisper legendas | delegar → fila transcribe |
| `scheduling.plan` | PG + enqueue | ideal |

**Papel do worker-general Go:** consumer Redis + claim PG + **dispatch**:

1. **Executa localmente** — ingest, plan, scheduling, merges JSON puros  
2. **Delega** — spawn `python -m …` one-shot **ou** re-enqueue em fila especializada (preferido)  
3. **Concorrência** — pool de goroutines (`WORKER_CONCURRENCY`, default 4–8) processando jobs independentes; ingest de run A + plan de run B em paralelo  

```text
                    worker-general (Go)
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ingest (local)    analyze.plan      scheduling.plan
   yt-dlp+S3         enqueue chunks     PG + Redis
         │                 │
         │                 └──────► worker-analyze (Python)
         └──────► early ingest done → transcribe queue
```

### O que **não** fica no general

- `analyze.gemini.chunk` / `analyze.transcript.chunk` → **worker-analyze**  
- `transcribe.plan/chunk/merge` → **worker-transcribe**  
- `render.*`, `metadata`, `thumbnail.*` → **worker-render** / **worker-thumbnail**  
- `publish.*` → **worker-publish**

Após migração, **`WORKER_STAGE=general`** deixa de existir no Python; só no binário Go.

---

## 5. contracts/ — contrato entre serviços

Extrair de `job_types.py`, `queues.py`, `server/internal/queue/client.go`:

```yaml
# contracts/queues.yaml (exemplo)
queues:
  general: cuts:jobs
  transcribe: cuts:jobs:transcribe
  analyze: cuts:jobs:analyze
  render: cuts:jobs:render
  publish: cuts:jobs:publish

envelope:
  schema_version: 1
  fields: [type, payload, enqueued_at]

artifacts:
  run_prefix: runs/{run_id}/
  video: source/video.mp4
  cuts: cuts.json
  transcript: transcript.json
```

Gerar stubs Go + Python na CI (ou manter YAML + testes de paridade).

**Regras:**

- Mesmo `idempotency_key` algorithm (`job_queue.make_idempotency_key`)  
- Mesmo `jobs_log` claim / lease / `recover_stale_jobs`  
- Paths S3 idênticos (`runs/{id}/…`)

---

## 6. libs/go-pipeline (shared Go)

Pacote usado por `scheduler`, `worker-general`, futuros workers Go:

| Pacote | Origem Python/Go atual |
|--------|------------------------|
| `consumer` | `consumer.py` + BRPOPLPUSH |
| `jobqueue` | `job_queue.py` |
| `envelope` | `envelope.py` |
| `pgconn` | `pg_conn.py` (port) |
| `blob` | alinhar com `server/internal/platform/blobstore` |

Evitar duplicar: preferir **módulo Go dentro do repo api** importado como `github.com/woragis/cuts-machine-backend/pipeline/...`.

---

## 7. Fases de execução

### Fase 0 — Preparação (esta branch)

- [x] Branch `feat/worker-services-split`  
- [ ] Documento aprovado (este file)  
- [ ] Estabilizar dual pipeline + pg reconnect em produção  

### Fase 1 — Esqueleto sem mudar runtime

- [ ] Criar pastas vazias + README por serviço  
- [ ] Extrair `contracts/`  
- [x] Mover `scheduler/` → top-level; Dockerfile Go stub  
- [ ] CI: listar serviços afetados por path  

### Fase 2 — worker-general Go (piloto)

- [x] Port consumer + claim + ack para Go  
- [x] Handlers Go: ingest, analyze.plan, gemini.merge, run control  
- [x] Python delegate só para IA/legacy (merge, scheduling, whisper, gemini.url)  
- [x] Feature flag: `GENERAL_WORKER_RUNTIME=go|python`  
- [ ] Railway: deploy serviço Go; remover mount Python quando IA migrar  

### Fase 3 — Delegação analyze + transcribe

- [x] general Go re-enfileira jobs IA para `cuts:jobs:analyze`  
- [x] Python worker-analyze exclusivo (`worker-analyze/` submodule)  
- [x] general Go re-enfileira jobs transcribe para `cuts:jobs:transcribe`  
- [x] Python worker-transcribe exclusivo (`worker-transcribe/` submodule)  
- [ ] Remover handlers duplicados do monolith  

### Fase 4 — scheduler Go

- [x] Port `recover_stale_jobs`, live_watch, publish_plans  
- [x] Desliga `python -m scheduler.main` (docker-compose usa imagem Go; rollback: `SCHEDULER_RUNTIME=python` em dev)  

### Fase 5 — render / thumbnail / publish

- [x] Python worker-render exclusivo (`worker-render/` submodule)  
- [x] Python worker-publish exclusivo (`worker-publish/` submodule)  
- [ ] Go orchestration render + subprocess treatment pesado  
- [ ] Avaliar fila dedicada `cuts:jobs:thumbnail`  

### Fase 6 — Desmontar monolith

- [ ] `backend/worker/cuts_worker/` vira só libs Python especializadas  
- [ ] Imagens Docker &lt; 500MB onde possível  

---

## 8. goroutines — modelo sugerido (worker-general)

```go
// Pseudocódigo
func main() {
    pool := NewPool(env.Concurrency) // default 4
    for {
        job := consumer.Pop(ctx) // blocking
        pool.Go(func() {
            if err := dispatch(ctx, job); err != nil {
                failJob(...)
            } else {
                ack(...)
            }
        })
    }
}
```

- **Ingest longo** — 1 goroutine por job; sem bloquear fila inteira  
- **analyze.plan** — goroutine enfileira dezenas de chunks rapidamente  
- **Limite** — `WORKER_CONCURRENCY` + memória por job (ingest 1080p ≈ 2GB → concurrency 2 nesse host)  

Python hoje: **1 job por processo**, loop serial no BRPOP — gargalo para I/O paralelo.

---

## 9. bots e sidecars

| Componente | Mover? | Notas |
|------------|--------|-------|
| **telegram-bot** | pasta top-level (já quase) | só Redis notify; pode ficar Python |
| **orchestrator** | pasta top-level | HTTP + Claude agent; Python até port |
| **meta-dev-server** | fora do pipeline | dev only |
| **tiktok-dev-server** | fora do pipeline | dev only |

Não misturar com workers de fila — ciclo de vida diferente (long-running HTTP vs job consumer).

---

## 10. Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| Duplicar lógica `_continue_run_after_analyze` | Manter orquestração em **um** lugar (Go general ou Python analyze) até Fase 3 |
| Deploy drift entre serviços | `contracts/` + testes de paridade |
| Rollback | Flag `GENERAL_WORKER_RUNTIME`; filas unchanged |
| Submodule hell | Monorepo single git; submodules só se necessário |

---

## 11. Decisões em aberto

1. **Monorepo único** vs repo por serviço (recomendado: monorepo, deploy separado)  
2. **general Go** delega via **re-enqueue** vs **subprocess Python** (recomendado: re-enqueue)  
3. **thumbnail** fila separada agora ou na Fase 5? (recomendado: Fase 5)  
4. **orchestrator** migra para Go? (recomendado: não no curto prazo)

---

## 12. Referências

- [ARCHITECTURE.md](./ARCHITECTURE.md) — visão Go API + Python workers  
- [backend/docs/plan-rust-workers-migration.md](../backend/docs/plan-rust-workers-migration.md) — superseded para general/scheduler (Go, não Rust)  
- Conversa GPT: `conversas/gpt_troca-de-stack-workers-cut/` — princípio infra Go / IA Python  

---

## Próximo passo imediato

1. Revisar este plano (ajustar escopo do general Go)  
2. Fase 1: criar estrutura de pastas + `contracts/` sem alterar produção  
3. Fase 2: implementar `worker-general` Go com **só ingest** como piloto  
