# Scheduler de publicação

Serviço **Go**, processo separado, **24/7**, responsável por disparar uploads no horário correto em todas as plataformas.

Parte de [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md). Entidades: [COMMUNITIES-AND-CATALOG.md](./COMMUNITIES-AND-CATALOG.md).

---

## Por que existe

| Plataforma | Agendamento nativo | Quem dispara no horário |
|------------|-------------------|-------------------------|
| YouTube | ✅ `publishAt` | Scheduler enfileira upload (pode ser antes do horário) |
| TikTok | ❌ | Scheduler enfileira upload **no** horário |
| Instagram | ❌ | Scheduler enfileira upload **perto** do horário (container expira em 24h) |

Decisão anterior (“sem scheduler na v1”) vale apenas para **YouTube isolado + publish manual**. Em escala multi-plataforma, **scheduler interno é obrigatório**.

---

## Arquitetura

```text
┌─────────────────┐     poll 30–60s      ┌──────────────────┐
│  Postgres       │◀──────────────────────│  scheduler (Go)  │
│  publish_plans  │                       │  cmd/scheduler   │
└─────────────────┘                       └────────┬─────────┘
                                                   │ LPUSH
                                                   ▼
                                          cuts:jobs:publish
                                                   │
                                                   ▼
                                          worker-publish (N réplicas)
```

### Singleton

- **1 réplica** ativa (ou leader election simples via Redis lock `scheduler:leader`)
- Leve: só SQL + Redis, sem FFmpeg

---

## Loop principal

```go
// Pseudocódigo
for {
    plans := repo.ListDuePublishPlans(limit: 100)
    for _, p := range plans {
        if rateLimiter.Allow(p.ConnectedAccountID, p.Platform) {
            repo.MarkEnqueued(p.ID)
            queue.Push("cuts:jobs:publish", job)
        }
    }
    sleep(30 * time.Second)
}
```

### Query due

```sql
SELECT pp.*
FROM publish_plans pp
JOIN publish_catalog pc ON pc.id = pp.catalog_id
WHERE pp.status = 'approved'
  AND pp.scheduled_at <= now()
  AND pp.attempts < 5
ORDER BY pp.scheduled_at ASC
LIMIT 100;
```

Fase 1: exigir `approved` (humano). Fase 2: auto-approve na criação.

---

## Job publish

Envelope Redis:

```json
{
  "schema_version": 1,
  "type": "publish.instagram",
  "payload": {
    "planId": "uuid",
    "catalogId": "uuid",
    "connectedAccountId": "uuid",
    "renderPath": "/data/runs/.../clip.mp4",
    "caption": "...",
    "scheduledAt": "2026-06-26T20:00:00Z"
  }
}
```

Worker publish:

1. Carrega tokens de `connected_accounts`
2. Executa upload (lib por plataforma)
3. Atualiza `publish_plans`: `done`, `external_post_id`, `published_at`
4. Atualiza `publish_catalog`: `published`
5. Em falha: `attempts++`, `last_error`, backoff ou `failed`

---

## Regras por plataforma

### YouTube

- Upload assim que plano entra na janela (ex.: até 7 dias antes)
- `status.privacyStatus = private` + `status.publishAt = scheduled_at`
- Worker não precisa esperar horário exato após upload

### TikTok

- Disparar no `scheduled_at` (± tolerância 2 min)
- Respeitar rate limit inbox/direct post

### Instagram

- **Não** criar container dias antes
- Scheduler dispara quando `scheduled_at - 30min <= now()`
- Worker: container → upload → poll → publish (ou publish no horário se container já FINISHED)

---

## scheduling.plan (job IA)

Roda em batch (ex.: 22:00 após renders do dia):

```text
Input:
  - publish_catalog WHERE status = ready AND community_id = ?
  - communities.scheduling_rules
  - histórico opcional (fase 2)

Output:
  - INSERT publish_plans (status: pending)
  - UPDATE publish_catalog SET status = scheduled
```

Humano revisa na UI → bulk approve → plans ficam `approved` → scheduler assume.

### Exemplo de regra (games)

```json
{
  "shortsPerChannelPerDay": 8,
  "minGapMinutes": 45,
  "peakHoursLocal": ["18:00", "20:00", "22:00"],
  "platforms": ["youtube", "tiktok", "instagram"],
  "youtubeLeadMinutes": 120
}
```

---

## Rate limiting

Redis token bucket por conta:

```text
Key: ratelimit:publish:{platform}:{connected_account_id}
```

Limites conservadores iniciais:

| Plataforma | Max/hora | Max/24h |
|------------|----------|---------|
| YouTube | 10 | 50 |
| TikTok | 5 | 20 |
| Instagram | 5 | 25 |

Instagram API: ~100 publicações / 24h rolling (documentação Meta).

---

## Retry e DLQ

| Tentativa | Backoff |
|-----------|---------|
| 1 | imediato |
| 2 | 5 min |
| 3 | 15 min |
| 4 | 60 min |
| 5 | DLQ + alerta |

`publish_plans.status = failed` após esgotar tentativas.

---

## Métricas (fase 3)

- `scheduler_plans_enqueued_total`
- `scheduler_loop_duration_ms`
- `publish_plans_lag_seconds` (now - scheduled_at para pendentes)
- `publish_success_rate` por plataforma

---

## Implementação

| Item | Status |
|------|--------|
| `cmd/scheduler/main.go` | ❌ |
| Migration `publish_plans` | ❌ |
| Worker `publish.*` handlers | 🟡 parcial (só YT básico no monolith) |
| UI agenda | ❌ |

Ordem: migration → scheduler mínimo → port publish libs → UI approve.
