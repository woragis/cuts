# Fases futuras — Máquina de Cortes

Roadmap pós-MVP (F12–F15 concluídas). Ordem sugerida: estabilizar observabilidade (F16) → pipelines 6–8 → curto prazo → médio → longo.

---

## F16 — Observabilidade do worker (prioridade)

**Problema:** API expõe `errorMessage` e `GET /v1/runs/{id}/jobs`, mas o worker só fazia `update_run_status(..., "failed")` sem gravar `runs.error_message` nem atualizar `jobs_log`.

**Entrega:**
- Worker grava `runs.error_message` ao falhar
- Worker atualiza `jobs_log` (`processing` → `completed` / `failed` / `skipped`)
- Retry passa a encontrar o último job falho de verdade

**Commit:** `feat(worker): persist run errors and job log status`

---

## Pipelines documentados — 6 a 8 (pós-MVP)

| # | Nome | `pipeline` / job | Input | Output |
|---|------|-------------------|-------|--------|
| 6 | Arquivo local (Woragis) | `local_file` (novo) | `video.mp4` local, sem yt-dlp | cortes LeetCode / OBS |
| 7 | Só metadados + thumb | `packaging_only` (variante) | URL + intervalo | frame + metadata + thumb, sem render |
| 8 | Outro no final | `outro.append` | vídeo + `outro.png` + song | append 12s no final |

Ver detalhes em [PIPELINES.md](./PIPELINES.md).

---

## Curto prazo — alto valor, baixo risco

| Fase | Feature | Descrição |
|------|---------|-----------|
| F17 | `re_render_cut` | Re-enfileirar metadata + thumb + render de um cut já aprovado (corrige timestamp pós-approve sem novo run) |
| F18 | `duplicate_run` | Copiar URL + cutBrief + templates → novo run idempotente |
| F19 | Capítulos do YouTube | Parser de descrição/capítulos → pré-popula `cuts.json` no pipeline 5 |
| F20 | Batch de URLs | `POST` com array de URLs → N runs na fila (curadoria em massa) |

---

## Médio prazo — produto

| Fase | Feature | Descrição |
|------|---------|-----------|
| F21 | `packaging_only` | Frame extract + metadata + thumb, export ZIP para Premiere (variante do pipeline 7) |
| F22 | A/B de thumbnail | 2–3 variantes por cut, escolher no UI |
| F23 | Tradução de metadata | EN/ES em `title.txt` / `description.txt` |
| F24 | Integração postar-mvp | Upload direto ao YouTube após render ([woragis/canal/postar-mvp](../../woragis/canal/postar-mvp)) |

**Evolução (2026-06):** F24+ detalhado em [ROADMAP-POS-TREATMENT.md](./ROADMAP-POS-TREATMENT.md) — editorial channels, hub/spoke, OAuth multi-conta, `publishAt` nativo YouTube (sem scheduler próprio), thumbnail sempre gpt-image-2.

| Fase | Feature | Doc |
|------|---------|-----|
| F25–F28 | Editorial channels, source profiles, hub/spoke, treatment por editorial | [EDITORIAL-CHANNELS.md](./EDITORIAL-CHANNELS.md), [HUB-SPOKE-ROUTING.md](./HUB-SPOKE-ROUTING.md), [SOURCE-PROFILES.md](./SOURCE-PROFILES.md) |
| F29–F30 | Thumbnail gpt-image-2, modos frame/character, model picker | [THUMBNAIL-MODES.md](./THUMBNAIL-MODES.md), [MODEL-SELECTION.md](./MODEL-SELECTION.md) |
| F31–F32 | OAuth Google por satélite, upload + `publishAt` | [PUBLISH-YOUTUBE.md](./PUBLISH-YOUTUBE.md) |
| — | Testes e validação | [TESTING-VALIDATION.md](./TESTING-VALIDATION.md) |

---

## Longo prazo — diferenciação

| Fase | Feature | Descrição |
|------|---------|-----------|
| F25 | Pipeline `react` | Detectar momentos de reação + sugerir layout split-screen |
| F26 | Pipeline `podcast_diarize` | Cortes longos por speaker/tópico (Whisper + diarization) |
| F27 | Compare presets | Dois `cutBriefPreset` no mesmo vídeo, side-by-side na revisão |

---

## Gaps menores (não bloqueiam MVP)

Itens conscientemente fora do escopo atual; vários sobem para as fases acima:

| Item | Destino sugerido |
|------|------------------|
| Editar cut depois do render | F17 `re_render_cut` |
| Duplicar run | F18 |
| Retry inteligente por estágio (metadata/render) | F16 + melhorar `POST /v1/runs/{id}/retry` após job logs |
| Upload `config.json` na UI de thumbnail | F14 extensão (hoje: pattern + character) |
| E2E real dos 5 pipelines em produção | Validação operacional contínua, não feature |

---

## O que não fazer (por enquanto)

- CRUD completo de **Source** (entidade derivada/cache)
- **UPDATE/DELETE** de **Run** (audit trail; `cancel` basta)
- **Auth / multi-tenant** até uso compartilhado
