# Plano geral — Suite de testes Máquina de Cortes

Roadmap para validar **detecção ABC v2** e **render profissional** antes de merge em produção.

## Objetivos

1. **4 vereditos comparáveis** — Gemini (A), OpenAI+Whisper (B), merge Claude (C), merge OpenAI (C′)
2. **Cortes completos e informativos** — não priorizar hook no segundo 0; fase C estende com transcript
3. **Shorts ~70s ideal, até ~130s** — unidade temática, não unidade de tempo fixa
4. **Longs ~8 min ideal, até ~15 min** — flexível; curto se focado, longo se explicar tudo
5. **`uselessParts` + transcriptBefore na fase C** — enrolação marcada; contexto anterior para extend
6. **Render auditável** — silêncio, hook/re-hook, zoom, música LUFS, legendas, outro (long)
7. **Decisão data-driven** — qual IA (e qual merge C) produz cortes que você aprovaria

---

## Fase 1 — Documentação e baseline ✅

| Item | Path |
|------|------|
| Índice | [`README.md`](README.md) |
| Workflow ABC | [`cuts/WORKFLOW-ABC.md`](cuts/WORKFLOW-ABC.md) |
| Prompts v2 | [`cuts/PROMPTS-v2.md`](cuts/PROMPTS-v2.md) |
| Schema JSON | [`cuts/SCHEMA-verdict.md`](cuts/SCHEMA-verdict.md) |
| Checklist render | [`render/CHECKLIST-RENDER.md`](render/CHECKLIST-RENDER.md) |
| **Pipeline long v2** | [`render/PIPELINE-LONG-v2.md`](render/PIPELINE-LONG-v2.md) |
| Decisões fechadas | [`DECISIONS.md`](DECISIONS.md) |
| Hooks / transições | [`render/HOOKS-REHOOKS-TRANSITIONS.md`](render/HOOKS-REHOOKS-TRANSITIONS.md) |
| Baseline copiado | [`fixtures/results/20260624T225609Z_eKxFuD3-pos/`](fixtures/results/20260624T225609Z_eKxFuD3-pos/) |
| Decisões fechadas | [`DECISIONS.md`](DECISIONS.md) |

---

## Fase 2 — Rodar ABC v2 (OpenAI first)

Decisões: [`DECISIONS.md`](DECISIONS.md)

```bash
cd backend/worker
export OPENAI_API_KEY=...          # nunca commitar
export WHISPER_REUSE=1
export SKIP_PHASE_C_CLAUDE=1       # só OpenAI no merge C desta run

python ../../tests/cuts/run_abc_pipeline.py \
  --fixture ../../tests/fixtures/openai-run.json
```

Com Claude também (comparar 4 vereditos): omitir `SKIP_PHASE_C_CLAUDE` e setar `ANTHROPIC_API_KEY`.

**Entregável:** `cuts/output/{runId}/validation.md` + `verdict_c_openai.json` (fonte render long).

**Offline:** `python ../../tests/cuts/run_offline_baseline.py`

## Fase 2b — Pipeline long v2 (spec ✅, código 🔜)

[`render/PIPELINE-LONG-v2.md`](render/PIPELINE-LONG-v2.md)

---

## Fase 3 — Escolher veredito C

Critérios em [`cuts/WORKFLOW-ABC.md`](cuts/WORKFLOW-ABC.md):

- Completude do tópico
- Deduplicação A∩B
- Qualidade dos `uselessParts`
- Long cuts agrupados

Registrar escolha no topo de `validation.md`.

---

## Fase 4 — Render matriz

Por corte prioritário (ver [`render/RENDER-MATRIX.md`](render/RENDER-MATRIX.md)):

```bash
cd backend/worker
CUTS_JSON=../../tests/cuts/output/.../verdict_c_claude.json \
  bash ../../tests/render/run_render_batch.sh merged-short-01 long-cut-03
```

Preencher [`render/CHECKLIST-RENDER.md`](render/CHECKLIST-RENDER.md) por output.

---

## Fase 5 — Hooks, zoom, outro

Seguir plano em [`render/HOOKS-REHOOKS-TRANSITIONS.md`](render/HOOKS-REHOOKS-TRANSITIONS.md):

| Teste | O que validar |
|-------|---------------|
| Hook direct | Short informativo linear |
| Re-hook MEI | peak → context → buildup → finale |
| Zoom hold | Explicação longa sem distrair |
| Zoom reset | Mudança de assunto |
| Outro long | Fade visual + auditivo |

---

## Fase 6 — Promover para produção (após sua aprovação)

| Área | Arquivo produção |
|------|------------------|
| Prompts A | `cuts_worker/analyze.py` |
| Fase B OpenAI | `cuts_worker/dual_merge.py` (+ novo analyze OpenAI) |
| Merge C OpenAI | `dual_merge.py` → `merge_cuts_with_openai()` |
| Schema uselessParts | API + DB cut candidates |
| Hook from verdict | `treatment_pipeline.py`, `build_treatment_brief()` |
| Transições zoom | `reframing/gemini_layout.py` |

---

## VOD de referência

[Arthur do Val · eKxFuD3-pos](https://www.youtube.com/watch?v=eKxFuD3-pos) — ~1h49, política MBL.

---

## Status

| Fase | Status |
|------|--------|
| Docs + scripts + baseline | ✅ |
| ABC v2 run completo | ⏳ aguardando API keys |
| Render matriz | ⏳ após escolher veredito |
| Hooks/zoom/outro v2 | ⏳ após checklist manual |
| Produção | 🔒 após aprovação |
