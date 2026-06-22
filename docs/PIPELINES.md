# Pipelines

Catálogo de pipelines da Máquina de Cortes.

**MVP inclui os pipelines 1–5.** Pipelines 6–8 entram em fases posteriores.

---

## Resumo

| # | Nome | Input | Output | No MVP |
|---|------|-------|--------|--------|
| 1 | URL → Shorts | `youtubeUrl` + `cutBrief` + template | N Shorts 9:16 + metadados | ✅ |
| 2 | URL → Cortes longos | idem | N vídeos 5–15 min + metadados | ✅ |
| 3 | URL → Shorts + Longos | idem | ambos | ✅ |
| 4 | URL → Só análise | idem | `cuts.json` + títulos (sem render) | ✅ |
| 5 | URL + timestamps manuais | `youtubeUrl` + `cuts.json` | renders diretos | ✅ |
| 6 | Arquivo local (Woragis) | `video.mp4` | cortes LeetCode | 🔲 |
| 7 | Só metadados + thumb | URL + intervalo | packaging sem vídeo | 🔲 |
| 8 | Outro no final | vídeo + outro.png | append 12s | 🔲 |

---

## Pipeline 1 — URL → Shorts

**Uso:** curadoria de canais de terceiros; clips virais.

```text
youtubeUrl
  → ingest.youtube.download
  → transcribe.run
  → analyze.gemini (cutBrief → shorts[])
  → [approve cuts]
  → metadata.generate (por cut)
  → thumbnail.generate (template escolhido)
  → render.short (9:16, legenda opcional)
  → output/shorts/{cutId}/
```

**Entrega por cut:**

```text
video.mp4
thumbnail.png
title.txt
description.txt
metadata.json
```

---

## Pipeline 2 — URL → Cortes longos

**Uso:** resumos, “melhores momentos”, compilados 5–15 min.

```text
youtubeUrl + cutBrief
  → ingest → transcribe → analyze.gemini (long_cuts[])
  → [approve]
  → metadata + thumbnail
  → render.long (16:9)
  → output/long/{cutId}/
```

---

## Pipeline 3 — URL → Shorts + Longos

Combina pipelines 1 e 2 num único **run**.

```text
POST /v1/runs
{
  "pipeline": "full",
  "targets": {
    "shorts": { "count": 10 },
    "longCuts": { "count": 3 }
  }
}
```

Gemini devolve `cuts.json` com arrays `shorts[]` e `long_cuts[]`. Render dispara jobs paralelos.

---

## Pipeline 4 — URL → Só análise

**Uso:** validar `cutBrief` e qualidade dos timestamps **sem gastar encode**.

```text
youtubeUrl + cutBrief
  → ingest (pode ser só áudio / 720p)
  → transcribe
  → analyze.gemini
  → cuts.json + títulos sugeridos
  → STOP (status: analyzed)
```

Depois: `POST /v1/runs/{id}/approve` → dispara renders (pipeline 1, 2 ou 3).

---

## Pipeline 5 — URL + timestamps manuais

**Uso:** timestamps da IA do YouTube, capítulos, ou edição manual.

```text
youtubeUrl + cuts.json (fornecido pelo usuário)
  → ingest.youtube.download
  → SKIP analyze
  → metadata + thumbnail + render
```

`cuts.json` pode vir de:

- paste manual na UI
- export da IA do YouTube
- pipeline 4 anterior (approve)

---

## Pipeline 6 — Arquivo local (Woragis) — pós-MVP

```text
video.mp4 (OBS)
  → transcribe → analyze (cutBrief LeetCode default)
  → render
```

Sem yt-dlp. Reutiliza workers de transcrição/analyze/render.

---

## Pipeline 7 — Só metadados + thumb — pós-MVP

```text
youtubeUrl + { start, end } + template
  → frame extract OU thumb gerada
  → metadata.generate
```

Para quem edita vídeo manualmente no Premiere.

---

## Pipeline 8 — Outro no final — pós-MVP

Port do [`append-outro_v1.py`](../../woragis/canal/end-screen/append-outro_v1.py):

```text
video.mp4 + outro.png + outro-song.mp3
  → outro.append (fade-out voz + fade-in imagem/música)
```

Job type: `outro.append` no `worker-render`.

---

## Seleção de pipeline na API

```json
{
  "pipeline": "shorts_only" | "long_only" | "full" | "analyze_only" | "render_from_cuts",
  "youtubeUrl": "https://youtube.com/watch?v=...",
  "thumbnailTemplateId": "uuid",
  "cutBrief": "momentos engraçados e reações fortes",
  "cuts": null,
  "targets": { ... }
}
```

| `pipeline` | Equivalente |
|------------|-------------|
| `shorts_only` | Pipeline 1 |
| `long_only` | Pipeline 2 |
| `full` | Pipeline 3 |
| `analyze_only` | Pipeline 4 |
| `render_from_cuts` | Pipeline 5 (`cuts` obrigatório) |

---

## Matriz de cenários

| Cenário | Pipeline | cutBrief exemplo |
|---------|----------|------------------|
| Shorts engraçados | 1 | "risadas, fails, reações" |
| Resumo de podcast | 2 | "melhores tópicos, debates" |
| Repurpose completo | 3 | "hooks virais + blocos por tema" |
| Testar prompt barato | 4 | qualquer |
| Já tenho timestamps | 5 | N/A (cuts manual) |

Ver [CUT-BRIEF.md](./CUT-BRIEF.md) para presets.
