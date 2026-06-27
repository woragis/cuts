# Schema — Veredito de cortes v2

## Envelope

```json
{
  "schemaVersion": 2,
  "phase": "a|b|c_claude|c_openai",
  "runId": "20260624T225609Z_eKxFuD3-pos",
  "youtubeUrl": "https://www.youtube.com/watch?v=eKxFuD3-pos",
  "generatedAt": "2026-06-17T12:00:00Z",
  "model": "gemini-2.5-pro",
  "shorts": [],
  "longCuts": [],
  "decisions": []
}
```

`decisions` só na fase C.

## Cut candidate

```json
{
  "id": "merged-short-01",
  "startSec": 4120.0,
  "endSec": 4185.0,
  "title": "MEI: cálculo ao vivo",
  "reason": "Explica passo a passo o cálculo tributário com exemplo numérico",
  "score": 0.92,
  "topic": "MEI / tributação",
  "completeness": "full",
  "source": "both",
  "mergedFrom": ["video-short-03", "caption-short-07"],
  "action": "merge",
  "extendedBecause": "faltava contexto sobre quem é Penélope",
  "uselessParts": [
    {
      "startSec": 4140,
      "endSec": 4152,
      "reason": "repetição do valor já citado",
      "severity": "trim"
    }
  ]
}
```

### Campos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | string | ✅ | Identificador estável no run |
| `startSec` / `endSec` | number | ✅ | Timeline global do VOD |
| `title` | string | ✅ | Título editorial |
| `reason` | string | ✅ | Por que este intervalo |
| `score` | number 0–1 | ✅ | Confiança |
| `topic` | string | recomendado | Assunto principal |
| `completeness` | `full\|partial` | recomendado | `partial` → C deve extend ou merge |
| `source` | string | A/B/C | `video`, `caption`, `both`, `merged` |
| `uselessParts` | array | recomendado | Trechos internos dispensáveis |
| `mergedFrom` | string[] | C only | IDs originais |
| `action` | string | C only | merge/extend/keep_separate/reject |
| `extendedBecause` | string | C only | Por que startSec/endSec foi estendido (contexto) |

### Duração — shorts (fase C)

| | Segundos |
|---|----------|
| min | 45 |
| ideal | **70** |
| max | **130** |

Campo opcional `durationSec` (= endSec - startSec) pode ser incluído pelo merge.

### Duração — long cuts (fase C)

| | Segundos |
|---|----------|
| min | 240 (~4 min) |
| ideal | **480 (~8 min)** |
| max | **900 (~15 min)** |

Long ideal quando o tópico é focado; até ~15 min quando a explicação completa exige — **permitido, não obrigatório**.

### uselessParts.severity

- **`trim`** — removido automaticamente no passo **silence** (+ silencedetect)
- **`optional`** — avaliar no render manual
- **`keep_for_context`** — manter; anotado para referência

### hookCandidates (fase C — schema v2.1, implementação futura)

Por corte long (recomendado 2–5):

```json
"hookCandidates": [
  {
    "startSec": 4120,
    "endSec": 4128,
    "score": 0.91,
    "reason": "número MEI ao vivo",
    "clipRelativeSec": 180
  }
]
```

Hook **picker** (OpenAI barata) escolhe 1 → ver [`../render/SCHEMA-treatment.md`](../render/SCHEMA-treatment.md).

## Transcript

```json
{
  "schemaVersion": 1,
  "source": "whisper_openai",
  "language": "pt",
  "durationSec": 6560,
  "segments": [
    {"startSec": 0.0, "endSec": 4.2, "text": "..."}
  ]
}
```

## Validação manual

`validation.md` lista cada corte com:

- Link YouTube `&t=`
- uselessParts inline
- Checkbox vazio para reviewer

Ver template em `validation_template.md`.
