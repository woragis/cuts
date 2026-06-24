# Fase 4 — Correções por step + apperrors enriquecidos

## Gemini `analyze.gemini.url` (HTTP 400) — **corrigido**

`gemini-3.5-flash` rejeita `fileData.fileUri` com URL YouTube (`INVALID_ARGUMENT`).

**Implementado:** `analyze_youtube_url` baixa legendas via yt-dlp (`captions.fetch_youtube`), grava `transcript.json`, e chama `analyze_transcript` (Gemini só com texto).

## Go API

- `apperrors.Error` opcional `Details map[string]any` para ops HTTP.
- Service/repo: wrap DB errors com `operation` (ex. `run.repository.GetByID`).
