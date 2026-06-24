# Fase 4 — Correções por step + apperrors enriquecidos

## Gemini `analyze.gemini.url` — três modos

| Modo | `options.analyzeMode` | Quando |
|------|----------------------|--------|
| **URL (default)** | `url` | Gemini vê o YouTube direto (áudio + visual) |
| **Híbrido** | `url_transcript` | Toggle no frontend — vídeo + legendas no prompt |
| **Profunda** | `deep` | Re-analisar / Retry com `deepAnalysis: true` — download + Gemini File API |

Job payload `analyze_mode` sobrescreve `options` (usado em retry profundo).

## Go API

- `apperrors.Error` opcional `Details map[string]any` para ops HTTP.
- Service/repo: wrap DB errors com `operation` (ex. `run.repository.GetByID`).
