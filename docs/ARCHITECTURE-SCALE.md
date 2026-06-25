# Arquitetura em escala — Máquina de Cortes

Documento de referência para **produção multi-nicho, multi-canal e multi-plataforma**.

Complementa [ARCHITECTURE.md](./ARCHITECTURE.md) (MVP) e substitui a premissa “1 worker esporádico / sem scheduler interno” quando o volume de produção exigir operação contínua.

**Decisão (2026-06):** com 3–4 lives/dia por nicho, hub + satélites, e publicação em YouTube + TikTok + Instagram, o sistema precisa de **filas separadas**, **pools de workers**, **scheduler 24/7** e **catálogo de publicação**.

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Escala esperada](#2-escala-esperada)
3. [Componentes](#3-componentes)
4. [Filas Redis](#4-filas-redis)
5. [Worker pools](#5-worker-pools)
6. [Scheduler 24/7](#6-scheduler-247)
7. [Agentes de IA](#7-agentes-de-ia)
8. [Fluxo end-to-end](#8-fluxo-end-to-end)
9. [Fases de implementação](#9-fases-de-implementação)
10. [Deploy e infra](#10-deploy-e-infra)
11. [Referências](#11-referências)

---

## 1. Visão geral

```text
                         ┌──────────────────────────────────────┐
                         │  Frontend (Next.js) + API (Go)       │
                         │  runs · communities · catalog · agenda│
                         └───────────────────┬──────────────────┘
                                             │
           ┌─────────────────────────────────┼─────────────────────────────────┐
           ▼                                 ▼                                 ▼
     PostgreSQL                        Redis (filas)                    Object storage
  communities, runs, cuts,         ingest / analyze / render /          /data/runs/
  editorial_channels,              publish / planning                   templates, assets
  connected_accounts,
  publish_catalog, publish_plans
           ▲                                 ▲
           │                                 │
 ┌─────────┴──────────┐          ┌───────────┴────────────────────────────┐
 │ Scheduler (Go)     │          │ Worker pools (Python)                  │
 │ processo 24/7      │          │                                        │
 │ poll publish_plans │─────────▶│ ingest (N) · analyze (N) · render (N+) │
 │ enqueue publish.*  │          │ publish (N) · planning (batch IA)      │
 └────────────────────┘          └────────────────────────────────────────┘
                                              │
                         OAuth dev-servers (Railway): youtube / tiktok / meta
```

**Princípios:**

| Princípio | Descrição |
|-----------|-----------|
| Go dono do estado | Postgres + enqueue + scheduler |
| Workers stateless | Consomem Redis; estado em DB/storage |
| Render ≠ Publish | Filas e pools separados |
| Scheduler sempre on | Multi-plataforma exige disparo no horário |
| Nicho escolhido no início | Comunidade definida no `POST /v1/runs`; IA roteia hub/spoke e agenda |

---

## 2. Escala esperada

Ordens de grandeza para planejamento de capacidade (ajustar com métricas reais).

| Nicho | Lives/dia | Cortes/live | Renders/dia | Uploads/dia (×3 plataformas) |
|-------|-----------|-------------|-------------|------------------------------|
| Política | 3–4 | 8–15 | 30–60 | 90–180 |
| Tech (3–5 fontes) | 3–5 | 8–12 | 40–60 | 120–180 |
| Finanças (5+ canais) | 5+ | 8–12 | 60–80 | 180–240 |
| Games (ritmo alto) | 3+ | 15–25 | 80–120 | 240–360 |

**Total em operação plena:** centenas de renders + centenas de publicações agendadas por dia → **>24h de trabalho acumulado** se serializado em 1 processo.

**Conclusão:** escalar **horizontalmente** o pool `render` e `publish`; manter `scheduler` como singleton leve.

---

## 3. Componentes

| Componente | Runtime | Réplicas | Responsabilidade |
|------------|---------|----------|------------------|
| **API** | Go | 1–N | REST, CRUD, enqueue produção |
| **Scheduler** | Go | 1 (leader) | `publish_plans` due → enqueue publish |
| **Worker ingest** | Python | 2–4 | download, cache source |
| **Worker analyze** | Python | 2–4 | Gemini analyze |
| **Worker render** | Python | **8–16+** | treatment, FFmpeg, thumb |
| **Worker publish** | Python | 4–8 | YT / TikTok / IG upload |
| **Worker planning** | Python | 1–2 | job batch `scheduling.plan` (IA) |
| **Postgres** | managed | 1 | fonte da verdade |
| **Redis** | managed | 1 | filas + rate limit tokens |
| **Storage** | volume/S3 | — | vídeos, assets (GB/TB) |

Detalhes de entidades: [COMMUNITIES-AND-CATALOG.md](./COMMUNITIES-AND-CATALOG.md).

---

## 4. Filas Redis

Substituir fila única `cuts:jobs` por **filas por estágio** (mesmo envelope JSON):

```json
{
  "schema_version": 1,
  "type": "render.short",
  "payload": { "runId": "...", "cutId": "..." }
}
```

| Fila | Job types | Consumidor |
|------|-----------|------------|
| `cuts:jobs:ingest` | `ingest.youtube.download` | worker-ingest |
| `cuts:jobs:analyze` | `analyze.gemini.url` | worker-analyze |
| `cuts:jobs:render` | `render.short`, `render.long`, `metadata.generate`, `thumbnail.generate`, `subtitle.generate` | worker-render |
| `cuts:jobs:publish` | `publish.youtube`, `publish.tiktok`, `publish.instagram` | worker-publish |
| `cuts:jobs:planning` | `routing.assign`, `scheduling.plan` | worker-planning |
| `cuts:jobs:dlq` | falhas após N tentativas | alerta + retry manual |

**Prioridade:** jobs de `publish` nunca competem com `render` na mesma fila.

**Rate limiting:** token bucket Redis por `connected_account_id` + plataforma antes de executar upload.

---

## 5. Worker pools

### Padrão de consumo

Cada réplica do pool executa:

```text
BRPOP cuts:jobs:{stage} → dispatch(type) → atualiza DB → enqueue próximo job
```

Workers **não** mantêm estado entre jobs (exceto cache local opcional).

### Variáveis de ambiente por pool

```bash
WORKER_STAGE=render          # ingest | analyze | render | publish | planning
WORKER_CONCURRENCY=1         # jobs paralelos por réplica (render: 1 recomendado)
REDIS_URL=...
DATABASE_URL=...
STORAGE_ROOT=/data
```

### Escalonamento

| Pool | Gargalo | Estratégia |
|------|---------|------------|
| render | CPU (FFmpeg) | mais réplicas; 1 job CPU-intensivo por réplica |
| publish | API rate limit | réplicas moderadas + rate limiter |
| analyze | Gemini quota | réplicas + backoff |
| scheduler | — | 1 instância |

---

## 6. Scheduler 24/7

Serviço Go separado do API e dos workers Python.

**Loop (30–60s):**

```sql
SELECT id FROM publish_plans
 WHERE status = 'pending'
   AND scheduled_at <= now()
 ORDER BY scheduled_at
 LIMIT 100;
```

Para cada plano:

1. Marcar `enqueued`
2. `LPUSH cuts:jobs:publish` com `{ type: "publish.{platform}", payload: { planId } }`
3. Worker publish executa upload e atualiza `done` + `external_post_id`

**Regras por plataforma:**

| Plataforma | Comportamento no horário |
|------------|-------------------------|
| YouTube | Upload com `publishAt` (pode subir minutos/horas antes) |
| TikTok | Upload no horário (sem `publishAt` nativo) |
| Instagram | Criar container **≤30 min antes** do horário (expira em 24h) |

Spec completa: [SCHEDULER.md](./SCHEDULER.md).

---

## 7. Agentes de IA

Três papéis **distintos** (jobs separados, prompts separados):

| Agente | Job | Quando | Input | Output |
|--------|-----|--------|-------|--------|
| **Analyze** | `analyze.gemini.url` | Início do run | URL + `communityId` + cutBrief | cortes propostos |
| **Routing** | `routing.assign` | Após approve | cuts + scores + hub/spoke | `targetEditorialChannelId` |
| **Scheduling** | `scheduling.plan` | Batch fim do dia | `publish_catalog` ready + regras nicho | `publish_plans[]` |

### Escolha de nicho no início (UX)

```json
{
  "youtubeUrl": "https://...",
  "communityId": "politica",
  "sourceProfileId": "mbl-arthur-live",
  "options": {
    "burnSubtitles": true,
    "routingMode": "hub_and_spoke"
  }
}
```

A comunidade **pré-filtra** editoriais, templates, música e contas conectadas. A IA só distingue **flagship vs satélite** ([HUB-SPOKE-ROUTING.md](./HUB-SPOKE-ROUTING.md)).

### Regras de cadência (exemplo)

```json
{
  "games": {
    "shortsPerChannelPerDay": 8,
    "peakHoursLocal": ["18:00", "22:00"],
    "platforms": ["youtube", "tiktok", "instagram"]
  },
  "politica": {
    "longsPerChannelPerDay": 5,
    "peakHoursLocal": ["12:00", "19:00"]
  }
}
```

Fase 1: humano aprova agenda gerada. Fase 2: auto com override.

---

## 8. Fluxo end-to-end

```text
POST /v1/runs (communityId + sourceProfileId)
  → analyze.gemini.url
  → awaiting_approval
  → POST approve
  → routing.assign
  → ingest → transcribe → metadata → render (por cut, editorial destino)
  → publish_catalog (status: ready)
  → scheduling.plan (batch) → publish_plans (status: pending)
  → [humano revisa agenda — opcional fase 1]
  → scheduler 24/7 → publish.* → status: published
```

---

## 9. Fases de implementação

```text
FASE 0 — Fundação de escala
├── migrations: communities, editorial_channels, connected_accounts
├── migrations: publish_catalog, publish_plans
├── Filas Redis separadas
├── Scheduler Go (mínimo viável)
└── Split worker: render + publish (mesmo código, env WORKER_STAGE)

FASE 1 — Catálogo + agenda
├── scheduling.plan job
├── UI: agenda do dia
├── Port publish libs (YT, TT, IG) → worker publish
└── Import JSON OAuth → connected_accounts

FASE 2 — Multi-nicho operacional
├── POST /v1/runs com communityId
├── routing.assign integrado
├── treatment lê editorial de destino
└── Rate limiter por conta

FASE 3 — Escala operacional
├── Métricas (lag fila, tempo render, falhas publish)
├── Réplicas Railway / migrar render pesado
├── Agentes refinados por nicho
└── Settings UI + guias OAuth
```

Atualizar também [ROADMAP-POS-TREATMENT.md](./ROADMAP-POS-TREATMENT.md) (fases F33+).

---

## 10. Deploy e infra

Railway **suporta parte** dessa arquitetura hoje; limites importantes para FFmpeg e autoscaling.

**Leia:** [DEPLOYMENT-RAILWAY.md](./DEPLOYMENT-RAILWAY.md) — réplicas, o que Railway faz/não faz, caminho para AWS/K8s.

Resumo:

| Capacidade | Railway | AWS/K8s |
|------------|---------|---------|
| Múltiplos serviços (API, scheduler, workers) | ✅ | ✅ |
| Réplicas horizontais (manual) | ✅ | ✅ |
| Autoscaling horizontal nativo (CPU/fila) | ❌ (manual / script) | ✅ (HPA/KEDA) |
| Jobs longos (FFmpeg >5 min) | ✅ em worker background* | ✅ |
| Volume persistente grande | ⚠️ limitado/caro | ✅ EBS/S3 |
| Escala para centenas de renders/dia | ⚠️ possível, caro | ✅ ideal |

\*Timeout de 5 min aplica-se a **requests HTTP**, não a processos worker consumindo Redis.

---

## 11. Referências

- [COMMUNITIES-AND-CATALOG.md](./COMMUNITIES-AND-CATALOG.md) — entidades SQL
- [SCHEDULER.md](./SCHEDULER.md) — scheduler e publish_plans
- [DEPLOYMENT-RAILWAY.md](./DEPLOYMENT-RAILWAY.md) — Railway vs AWS
- [METRICS-OPS.md](./METRICS-OPS.md) — métricas Redis + `/v1/ops/overview`
- [EDITORIAL-CHANNELS.md](./EDITORIAL-CHANNELS.md) — canais flagship/satélite
- [HUB-SPOKE-ROUTING.md](./HUB-SPOKE-ROUTING.md) — roteamento hub/spoke
- [PUBLISH-YOUTUBE.md](./PUBLISH-YOUTUBE.md) — OAuth + publishAt
- [backend/worker/scripts/post/ROADMAP.md](../backend/worker/scripts/post/ROADMAP.md) — ordem multi-plataforma
