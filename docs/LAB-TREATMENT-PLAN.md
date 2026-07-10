# Lab Treatment — plano e direção

Documento vivo para não perder contexto. Atualizado em Sprint 1.

## Objetivo

Pipeline de tratamento long (16:9) que diferencia o hash do vídeo no YouTube (EDL, filtros, hook, música, outro, watermark) sem reprocessar lives inteiras a cada teste.

## Decisões fechadas

| # | Decisão |
|---|---------|
| 1 | Run lab isolada; reutilizar download + corte **long-02** da run `0ddb9410` |
| 2 | **Pular metadata** no lab — copiar de run de referência |
| 3 | **Hook** vem de análise automática do corte (transcript + IA), fundido no step **EDL** |
| 4 | Sequência: Sprint 1 (EDL+hook) → baixar `clip_edl.mp4` → avaliar → Sprints 2+ |

## Run lab (Opção A)

```http
POST /v1/runs
{
  "pipeline": "render_from_cuts",
  "youtubeUrl": "https://www.youtube.com/watch?v=LR6-esOiX3c",
  "thumbnailTemplateId": "11111111-1111-1111-1111-111111111111",
  "language": "pt",
  "cuts": {
    "longCuts": [{
      "id": "lab-01",
      "startSec": 1334,
      "endSec": 1990,
      "title": "Lab EDL+hook (long-02)",
      "status": "approved"
    }]
  },
  "options": {
    "treatmentChannel": "politica-mbl",
    "burnSubtitles": false,
    "requireApproval": false,
    "skipMetadata": true,
    "labStopAfterStep": "edl",
    "referenceRunId": "0ddb9410-5c16-480e-a2ef-9e478c856233",
    "referenceCutId": "long-02"
  }
}
```

- **Ingest:** cache hit (`source_id` igual) — não baixa a live de novo.
- **Artefatos:** `runs/{lab-uuid}/long/lab-01/` — não mexe na run boa.

## Pipeline long — lab (Sprint 1)

```
raw → edl (hook embutido + filtros) → [STOP]
```

| Step | Lab |
|------|-----|
| silence | **OFF** (`silence.stepEnabled: false`) |
| hook | **Fundido no EDL** (`hook.mergedIntoEdl: true`) |
| subtitles | **OFF** (`burnSubtitles: false`) |
| music / final | **OFF** (`labStopAfterStep: edl`) |

### Lego de artefatos

```
clip_raw.mp4      ← extract (1334–1990s)
clip_edl.mp4      ← hook reorder + EDL + contrast/sat + mirror-on-zoom  ★ checkpoint
editPlan.json
hookPlan.json
cut_treatment.json
```

## Hook + EDL

1. `analyze_hook_for_cut()` — OpenAI + transcript do corte → `hookPeakSec`
2. `build_rehook_plan()` — peak teaser → context → buildup → finale
3. No step **edl:** concat re-hook → `analyze_edit_plan` → `render_edit_plan`

Transições/SFX completas ficam para Sprint 2+.

## Sprints

### Sprint 1 — Lab + EDL + hook (atual)

- [x] `silence.stepEnabled` no canal
- [x] Hook automático + merge no EDL
- [x] `skipMetadata` + `referenceRunId` + `labStopAfterStep`
- [ ] Deploy + run lab na Railway
- [ ] Baixar `clip_edl.mp4` e avaliar

### Sprint 2 — Assets

- Script watermark: OpenAI image → fundo branco → PIL remove → PNG 320×90
- `music-download` → música + SFX → upload API canal
- yt-dlp → transições VFX (opcional)
- Expandir `allowedAssets` na API

### Sprint 3 — Final da pipeline

- Música (`music`) + outro + watermark (`final`)
- Re-run lab `fromStep: music`

### Sprint 4 — UI

- `WatermarkPreview` (estilo `SubtitlePreview`)
- Upload watermark no painel do canal

## Testes Railway (long only)

```bash
API="https://cuts-machine.api.woragis.me"
RUN="<lab-uuid>"

# Status
curl -fsS "$API/v1/runs/$RUN"
curl -fsS "$API/v1/runs/$RUN/jobs?limit=10"

# Checkpoint Sprint 1
curl -fsS -o clip_edl.mp4 "$API/v1/runs/$RUN/files/long/lab-01/clip_edl.mp4"
curl -fsS "$API/v1/runs/$RUN/files/long/lab-01/editPlan.json"
curl -fsS "$API/v1/runs/$RUN/files/long/lab-01/hookPlan.json"

# Iterar só EDL
curl -fsS -X POST "$API/v1/runs/$RUN/cuts/lab-01/pipeline" \
  -H "Content-Type: application/json" \
  -d '{"fromStep":"edl","continuePipeline":false}'

railway logs -s cuts-worker-render
```

## Referência long-02 (run `0ddb9410`)

| Campo | Valor |
|-------|-------|
| startSec | 1334 |
| endSec | 1990 |
| duração | ~656s (~11 min) |

## Config canal `politica-mbl` (trecho)

```json
{
  "models": { "edl": "gemini-2.5-pro", "hook": "gemini-2.5-pro" },
  "silence": { "stepEnabled": false, "enabled": true, ... },
  "hook": { "enabled": true, "mergedIntoEdl": true },
  "video": { "contrast": 1.08, "saturation": 1.12, "mirrorOnZoom": true }
}
```

**Modelos:** EDL e hook usam **Gemini 2.5 Pro** por padrão (vídeo inteiro no EDL; transcript no hook). Alternativa: `gpt-4o` via `run.options.models`. Não usar `gpt-4o-mini` para esses steps.
