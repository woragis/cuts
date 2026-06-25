# Roadmap pós-treatment — índice

Plano de upgrades após integração do pipeline de treatment (reframing + legendas + thumb) no worker.

**Decisões fixadas (2026-06):**

| Área | Decisão |
|------|---------|
| Thumbnail | **Sempre `gpt-image-2`** — sem fallback PIL em produção |
| Frame do thumb | Modelos do step analyze: `gemini-2.5-pro` \| `gemini-3.5-flash` |
| Reframing | Mesmos modelos Gemini (`gemini-2.5-pro` \| `gemini-3.5-flash`) |
| Agendamento YouTube | **`publishAt` nativo** | upload antecipado; YouTube publica no horário |
| Agendamento TikTok/IG | **Scheduler interno 24/7** | ver [SCHEDULER.md](./SCHEDULER.md) |
| Distribuição | Hub/spoke + `editorial_channel` por satélite | + `community` no topo |
| OAuth | Conta por editorial × plataforma | `connected_accounts` multi-plataforma |
| Escala | Worker pools + filas Redis | ver [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md) |

---

## Documentos de spec

| Documento | Conteúdo |
|-----------|----------|
| [EDITORIAL-CHANNELS.md](./EDITORIAL-CHANNELS.md) | Entidade editorial, assets, música, outro, templates |
| [HUB-SPOKE-ROUTING.md](./HUB-SPOKE-ROUTING.md) | Flagship vs satélite, roteamento por score |
| [SOURCE-PROFILES.md](./SOURCE-PROFILES.md) | Presets por live, reframing, satélite default |
| [THUMBNAIL-MODES.md](./THUMBNAIL-MODES.md) | pattern+character \| pattern+frame, sempre gpt-image-2 |
| [MODEL-SELECTION.md](./MODEL-SELECTION.md) | Picker por step no frontend |
| [PUBLISH-YOUTUBE.md](./PUBLISH-YOUTUBE.md) | OAuth multi-conta, upload, `publishAt` |
| [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md) | Filas, worker pools, escala multi-nicho |
| [COMMUNITIES-AND-CATALOG.md](./COMMUNITIES-AND-CATALOG.md) | Communities, publish_catalog, publish_plans |
| [SCHEDULER.md](./SCHEDULER.md) | Scheduler 24/7 multi-plataforma |
| [DEPLOYMENT-RAILWAY.md](./DEPLOYMENT-RAILWAY.md) | Railway réplicas, limites, path AWS |
| [TESTING-VALIDATION.md](./TESTING-VALIDATION.md) | Testes e validação antes de publicar |

---

## Ordem de implementação

```text
F25  editorial_channels (DB + CRUD + uploads)
F26  source_profiles + reframing presets por live
F27  hub/spoke routing no approve
F28  treatment lê editorial do corte (música, outro, templates)
F29  thumbnail unificado (gpt-image-2 + modos + template CRUD)
F30  model picker no run (analyze / frame / reframing)
F31  connected_accounts + OAuth (multi-plataforma)
F32  publish YouTube com publishAt
───  ESCALA (2026-06) ───
F33  communities + publish_catalog + publish_plans (migrations)
F34  filas Redis separadas + WORKER_STAGE (render / publish)
F35  scheduler Go 24/7
F36  scheduling.plan (IA) + UI agenda
F37  publish.tiktok + publish.instagram no worker publish pool
F38  POST /v1/runs com communityId + routing.assign
F39  métricas fila + alertas lag
F40  escala Railway (réplicas) ou render em AWS/K8s
```

---

## Estado atual vs alvo

| Capacidade | Hoje | Alvo |
|------------|------|------|
| Treatment shorts | ✅ worker integrado | + editorial por corte |
| Thumbnail | ⚠️ gpt-image-2 com fallback PIL local | sempre gpt-image-2 |
| Frame pick | ⚠️ keywords no transcript | Gemini 2.5-pro / 3.5-flash |
| Reframing | ✅ Gemini (env override) | model picker + SourceProfile |
| Templates thumb/legenda | ✅ CRUD | ligados ao editorial_channel |
| editorial_channel | ❌ JSON em arquivo | Postgres + CRUD |
| Hub/spoke | ❌ | approve + routing |
| OAuth YouTube | ❌ `.env` único | conta por editorial |
| Publicar | ⚠️ private imediato | multi-plataforma + agenda |
| Communities / catálogo | ❌ | Postgres + scheduler |
| TikTok / Instagram | ⚠️ scripts validados | worker publish pool |
| Worker escala | ⚠️ monolito 1 fila | pools + réplicas |

---

## Relação com FUTURE-PHASES.md

F24 (postar-mvp) evolui para **F31–F32**. TikTok/Instagram e scheduler: **F33–F40** ([ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md)).
