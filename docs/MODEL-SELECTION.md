# Seleção de modelos por step

Permitir no frontend escolher qual modelo executa cada etapa, para comparar **qualidade vs custo** sem alterar código.

---

## Modelos por step

| Step | Opções (v1) | Default produção |
|------|-------------|------------------|
| **analyze** (cortes) | `gemini-2.5-pro`, `gemini-3.5-flash` | `gemini-2.5-pro` |
| **reframing** | `gemini-2.5-pro`, `gemini-3.5-flash` | `gemini-2.5-pro` |
| **frame_pick** (thumbnail) | `gemini-2.5-pro`, `gemini-3.5-flash` | `gemini-2.5-pro` |
| **thumbnail** | `gpt-image-2` apenas | `gpt-image-2` |
| **subtitles** | `whisper-1` | `whisper-1` |

Fallback chain reframing (já no worker): `2.5-pro` → `3.5-flash` → `3.1-flash-lite` em 404/503/429.

---

## Contrato no run

```json
{
  "options": {
    "models": {
      "analyze": "gemini-2.5-pro",
      "reframing": "gemini-2.5-pro",
      "framePick": "gemini-3.5-flash",
      "thumbnail": "gpt-image-2",
      "subtitles": "whisper-1"
    }
  }
}
```

Defaults podem vir do `editorial_channel` e ser sobrescritos no run.

---

## UI (NewRunForm / RunDetail)

Seção **“Modelos”** (avançado, colapsável):

- Dropdown por step
- Tooltip com custo relativo (barato / médio / caro)
- Preset buttons: “Qualidade máxima” | “Custo-benefício”

### Presets sugeridos

| Preset | analyze | reframing | framePick |
|--------|---------|-----------|-----------|
| Qualidade | 2.5-pro | 2.5-pro | 2.5-pro |
| Custo-benefício | 3.5-flash | 3.5-flash | 3.5-flash |
| Misto | 2.5-pro | 2.5-pro | 3.5-flash |

---

## Telemetria (futuro)

Gravar por cut em `cut_treatment.json` ou job log:

```json
{
  "modelsUsed": {
    "reframing": "gemini-2.5-pro",
    "framePick": "gemini-3.5-flash",
    "thumbnail": "gpt-image-2"
  },
  "durationsMs": { "reframing": 45000, "thumbnail": 12000 }
}
```

Permite comparar runs no UI.

---

## Implementação (2026-06)

| Step | Override | UI |
|------|----------|-----|
| analyze | `options.models.analyze` + `options.modelCompare.analyze[]` | ModelStepPicker |
| framePick | `options.models.framePick` | ModelStepPicker |
| reframing | `REFRAMING_VISION_MODEL` env | — |
| thumbnail | gpt-image-2 fixo | — |

OpenAI analyze: baixa VOD + amostra até 48 frames (`OPENAI_ANALYZE_MAX_FRAMES`).

Compare mode: `compare/analyze/{model}.json` no run dir; `cuts.json` usa o primeiro modelo.

---

## Catálogo de preços (referência Jun/2026 — conferir billing antes de escalar)

| Modelo | Step ideal | Input (ordem de grandeza) | Quando usar |
|--------|------------|---------------------------|-------------|
| **gemini-3.5-flash** | analyze URL | ~$0.10–0.35 / VOD 1h (video low res) | Default barato; URL YouTube nativa |
| **gemini-2.5-pro** | analyze, framePick, reframing | ~$1–3 / VOD 1h | Qualidade máxima; lives densas |
| **gpt-4o-mini** | framePick, analyze curto | ~$0.15–0.40 / 48 frames | A/B barato vs Gemini |
| **gpt-4o** | framePick, analyze compare | ~$1–2 / 48 frames low detail | Comparar qualidade visual |
| **heuristic-keywords** | framePick | $0 | Baseline offline |

**Não recomendado v1:** Grok/xAI (API instável para video longo), Claude video (só merge texto hoje).

**Regra prática:** analyze = 1 call grande; framePick = N calls pequenos (1 por corte). Por isso framePick pode usar Flash/mini sem explodir custo.

---

## Implementação anterior
