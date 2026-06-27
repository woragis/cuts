# Thumbnail — modos e geração

---

## Decisão fixa

**Thumbnail é sempre gerada por `gpt-image-2`.** Sem fallback PIL/local em produção.

Se a API falhar (billing, 429): job falha com erro claro; operador re-tenta ou troca modelo — não substituir silenciosamente por composição local.

---

## Modos de referência

Configurado no `editorial_channel` ou no `thumbnail_template.config`:

| Modo | Referências enviadas ao gpt-image-2 | Upload |
|------|-------------------------------------|--------|
| `pattern_character` | `pattern.png` + `character.png` | character obrigatório |
| `pattern_frame` | `pattern.png` + frame do vídeo | nenhum (extrai do clip) |

Não há modo “só pattern” sem segunda referência visual.

---

## Seleção do frame (`pattern_frame`)

| `frame_selection` | Comportamento |
|-------------------|---------------|
| `auto` | Modelo Gemini escolhe o segundo (ver MODEL-SELECTION.md) |
| `manual` | UI mostra candidatos; usuário escolhe antes do render ou no re-thumb |
| `fixed_sec` | `frame_fixed_sec` no editorial (ex.: 3.0) |

### Frame auto — modelos permitidos

Mesma família do step **analyze**:

- `gemini-2.5-pro` (default)
- `gemini-3.5-flash`

Entrada: transcript do corte + lista de segmentos no intervalo + opcionalmente 3–5 frames amostrados (1 fps).

Saída: `{ "frameSec": 12.4, "reason": "..." }`

**Não** usar apenas keyword heuristics em produção (hoje em `treatment_pipeline.suggest_thumbnail_frame_sec` — substituir).

### Frame manual — UI

1. Após `clip_framed` ou `clip_subtitled`, worker gera `frame_candidates/` (ex.: 6 jpgs)
2. UI exibe grid; escolha grava `cut.frameSec`
3. Thumb job usa `frameSec` explícito

---

## Template CRUD

Unificar com API existente (`/v1/templates`):

```json
{
  "outputSize": [1280, 720],
  "shortOutputSize": [1080, 1920],
  "imageModel": "gpt-image-2",
  "thumbnailMode": "pattern_frame",
  "promptSnippet": "Brazilian political commentary, orange/black...",
  "titleStyle": { "line1Color": "white", "line2Color": "#FFD700" }
}
```

Assets: `pattern.png`, `character.png` (opcional conforme modo), upload via `POST /v1/templates/{id}/assets`.

Worker treatment (`thumbnail_politica.py`) deve ler template do editorial, não prompts hardcoded.

---

## Tamanhos API gpt-image-2

| Formato | API size | Output |
|---------|----------|--------|
| Long 16:9 | `1792x1024` | resize → 1280×720 |
| Short 9:16 | `1024x1792` | resize → 1080×1920 |

---

## Implementação atual

| Item | Status |
|------|--------|
| gpt-image-2 | ✅ em `thumbnail_politica.py` |
| Fallback PIL | ⚠️ existe — **remover em produção** |
| Template CRUD + upload pattern | ✅ API + UI |
| Modos pattern_character / pattern_frame | ❌ não exposto |
| Frame via Gemini | ❌ hoje keywords |
| Ligação editorial → template | ❌ |
