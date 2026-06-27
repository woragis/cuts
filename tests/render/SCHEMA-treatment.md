# Schema — Treatment long v2

Artefatos entre veredito ABC e FFmpeg.

## cut_treatment.json (brief)

Envelope existente em `cut_treatment.json` + campos novos:

```json
{
  "cutId": "long-cut-03",
  "cutFormat": "long",
  "vod": { "startSec": 4000, "endSec": 5200 },
  "clip": { "path": "clip_raw.mp4", "durationSec": 1200 },
  "silence": { "removals": [] },
  "hook": { },
  "editPlan": { },
  "audio": { },
  "subtitles": { },
  "outro": { }
}
```

---

## hookCandidates (no veredito / cut)

```json
{
  "startSec": 4120,
  "endSec": 4128,
  "score": 0.91,
  "reason": "string",
  "clipRelativeSec": 180
}
```

Gerado na fase C (futuro). O picker escolhe um.

---

## hookPlan

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `hookType` | `direct \| rehook \| teaser_only` | long usa `rehook` ou `teaser_only` |
| `hookStyle` | `imperceptible \| marked` | long default `imperceptible` |
| `peakSec` | number | clip-local |
| `teaserEndSec` | number | peak + 2–4s |
| `segments` | array | ordem concat |
| `effects.visual` | `none \| vignette \| bw` | long: `none` |
| `effects.audio` | `none \| swell` | long: `none` |
| `pickedFrom` | string | id ou índice candidato |
| `pickerReason` | string | log humano |

---

## editPlan

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `schemaVersion` | 1 | |
| `format` | `long` | |
| `aspect` | `16:9` | |
| `segments[].startSec` | number | clip-local pós-hook |
| `segments[].visual.type` | string | hold, focus_content, … |
| `segments[].visual.zoom` | number | 1.0–1.15 v1 |
| `limits.maxDynamicEventsPerMin` | number | default 0.5 |

---

## silence.removals

| Campo | Descrição |
|-------|-----------|
| `startSec` / `endSec` | clip-local |
| `source` | `silencedetect \| uselessParts` |
| `reason` | opcional |
