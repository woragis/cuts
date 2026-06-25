# Métricas e ops — workers + filas

Observabilidade leve via **Redis** → API Go → frontend (polling).

Parte de [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md) (F34).

---

## Endpoint

```http
GET /v1/ops/overview
```

Resposta exemplo:

```json
{
  "updatedAt": "2026-06-25T20:00:00Z",
  "queues": {
    "jobs": 2,
    "render": 11,
    "publish": 3
  },
  "workers": [
    {
      "instanceId": "worker-render-1-42",
      "stage": "render",
      "status": "busy",
      "cpuPercent": 87.2,
      "memoryMb": 2048,
      "memoryPercent": 34.1,
      "currentJobType": "render.short",
      "jobsOk": 12,
      "jobsFail": 0,
      "updatedAt": "..."
    }
  ],
  "scheduler": {
    "alive": true,
    "status": "ok",
    "updatedAt": "..."
  },
  "hints": [
    {
      "stage": "render",
      "action": "scale_up",
      "reason": "fila render=11, CPU média 45.3%"
    }
  ]
}
```

Frontend: poll a cada **30–60s** (não websocket — dados estáticos/cacheáveis).

---

## Chaves Redis

| Chave | Quem escreve | TTL | Conteúdo |
|-------|--------------|-----|----------|
| `cuts:metrics:worker:{instance_id}` | cada worker | 90s | CPU, RAM, job atual, contadores |
| `cuts:metrics:queues` | scheduler | — | profundidade das filas |
| `cuts:metrics:scheduler` | scheduler | — | heartbeat |

Se worker não renovar métricas em 90s → some do overview (réplica morta ou scale-down).

---

## Filas

| Fila | `WORKER_STAGE` | Jobs |
|------|----------------|------|
| `cuts:jobs` | `general` | ingest, analyze, transcribe |
| `cuts:jobs:render` | `render` | metadata, thumb, subtitle, render |
| `cuts:jobs:publish` | `publish` | publish.youtube (+ TT/IG futuro) |

Enqueue automático por tipo de job (Python + Go).

---

## Serviços (Docker / Railway)

| Serviço | Réplicas sugeridas | Env |
|---------|-------------------|-----|
| `scheduler` | 1 | — |
| `worker-general` | 1 | `WORKER_STAGE=general` |
| `worker-render` | 2–4 | `WORKER_STAGE=render` |
| `worker-publish` | 2 | `WORKER_STAGE=publish` |

Local:

```bash
docker compose up -d --scale worker-render=3 --scale worker-publish=2
```

Railway: um **service** por stage; ajuste **Replicas** no painel.

---

## Hints de escala (heurística v1)

| Condição | Ação sugerida |
|----------|---------------|
| fila render ≥ 8 **e** CPU média render < 75% | `scale_up` render |
| fila render ≤ 1 **e** ≥ N−1 workers idle | `scale_down` render |
| fila publish ≥ 5 **e** CPU média < 70% | `scale_up` publish |
| scheduler `alive: false` | investigar serviço scheduler |

Thresholds ajustáveis no código (`ops.go`) conforme você ganha experiência por nicho.

---

## Variáveis

| Env | Default | Uso |
|-----|---------|-----|
| `WORKER_STAGE` | `all` | `general` \| `render` \| `publish` |
| `WORKER_INSTANCE_ID` | hostname-pid | id estável no Railway (ex. `${RAILWAY_REPLICA_ID}`) |
| `WORKER_METRICS_TTL_S` | 90 | expiração heartbeat worker |
| `SCHEDULER_INTERVAL_S` | 30 | tick do scheduler |

---

## Frontend

Rota **`/ops`** — poll a cada 45s em `GET /v1/ops/overview`:

- profundidade das filas (geral / render / publish)
- scheduler online/offline
- workers por stage (CPU, RAM, job atual)
- hints `scale_up` / `scale_down`

Link também em **Settings → Abrir painel Ops**.

Grafana opcional (export Redis → Prometheus) se precisar histórico longo.
