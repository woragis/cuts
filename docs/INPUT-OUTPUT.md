# Contratos de entrada e saída

Schemas e formatos de arquivo compartilhados entre API, workers e frontend.

---

## POST /v1/runs — criar pipeline run

```json
{
  "pipeline": "shorts_only",
  "youtubeUrl": "https://www.youtube.com/watch?v=XXXXXXXX",
  "thumbnailTemplateId": "550e8400-e29b-41d4-a716-446655440000",
  "cutBrief": "Achar momentos engraçados, reações fortes e frases polêmicas",
  "cutBriefPreset": "funny",
  "channelContext": "podcast de tecnologia em português",
  "language": "pt",
  "targets": {
    "shorts": {
      "count": 10,
      "minSec": 15,
      "maxSec": 60
    },
    "longCuts": {
      "count": 3,
      "minMin": 5,
      "maxMin": 15
    }
  },
  "cuts": null,
  "options": {
    "requireApproval": true,
    "downloadQuality": "720p",
    "transcriptionSource": "youtube_captions",
    "burnSubtitles": true
  }
}
```

### Campos

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `pipeline` | sim | Ver [PIPELINES.md](./PIPELINES.md) |
| `youtubeUrl` | sim* | URL pública YouTube (* MVP) |
| `thumbnailTemplateId` | sim | Template salvo em `/v1/templates` |
| `cutBrief` | sim** | Texto livre para Gemini (** exceto pipeline 5) |
| `cutBriefPreset` | não | Atalho; expande para prompt base |
| `cuts` | pipeline 5 | `cuts.json` completo ou parcial |
| `targets` | não | Limites de quantidade/duração |
| `options.requireApproval` | não | Default `true` — pausa antes do render |

---

## cuts.json

Contrato central entre analyze → approve → render.

```json
{
  "schemaVersion": 1,
  "runId": "550e8400-e29b-41d4-a716-446655440001",
  "sourceUrl": "https://www.youtube.com/watch?v=XXXXXXXX",
  "analyzedAt": "2026-06-19T12:00:00Z",
  "cutBrief": "momentos engraçados",
  "shorts": [
    {
      "id": "short-01",
      "start": "00:12:15.000",
      "end": "00:12:55.000",
      "startSec": 735.0,
      "endSec": 775.0,
      "title": "Erro que reprova candidatos",
      "description": null,
      "score": 0.92,
      "reason": "frase forte + reação imediata",
      "status": "proposed"
    }
  ],
  "longCuts": [
    {
      "id": "long-01",
      "start": "00:05:23.000",
      "end": "00:21:10.000",
      "startSec": 323.0,
      "endSec": 1270.0,
      "title": "Two Sum — explicação completa",
      "description": null,
      "score": 0.88,
      "reason": "bloco contínuo sobre um tópico",
      "status": "proposed"
    }
  ]
}
```

### Status de cut

| Status | Significado |
|--------|-------------|
| `proposed` | Gemini sugeriu; aguardando review |
| `approved` | OK para render |
| `rejected` | Ignorado |
| `rendering` | Job em andamento |
| `done` | Arquivo final pronto |
| `failed` | Erro no render |

---

## transcript.json

```json
{
  "schemaVersion": 1,
  "runId": "...",
  "language": "pt",
  "source": "youtube_captions",
  "durationSec": 697.3,
  "segments": [
    {
      "startSec": 0.0,
      "endSec": 4.2,
      "text": "Fala galera, hoje vamos falar sobre..."
    }
  ]
}
```

---

## manifest.json (saída final do run)

```json
{
  "schemaVersion": 1,
  "runId": "...",
  "pipeline": "full",
  "youtubeUrl": "...",
  "thumbnailTemplateId": "...",
  "status": "completed",
  "outputs": {
    "shorts": [
      {
        "cutId": "short-01",
        "path": "shorts/short-01/video.mp4",
        "thumbnail": "shorts/short-01/thumbnail.png",
        "title": "...",
        "description": "..."
      }
    ],
    "longCuts": []
  }
}
```

---

## Estrutura de pastas de saída

```text
/data/runs/{runId}/
├── source/
│   └── video.mp4
├── transcript.json
├── cuts.json
├── cuts.approved.json
├── manifest.json
├── long/
│   └── long-01/
│       ├── video.mp4
│       ├── thumbnail.png
│       ├── title.txt
│       ├── description.txt
│       └── metadata.json
└── shorts/
    └── short-01/
        └── ...
```

---

## metadata.json (por cut)

```json
{
  "cutId": "short-01",
  "title": "Esse erro reprova em entrevista",
  "description": "Trecho do podcast X sobre...\n\n#shorts #tech",
  "tags": ["shorts", "entrevista", "tech"],
  "youtube": {
    "suggestedCategory": "Science & Technology"
  }
}
```

---

## Run status (API)

| Status | Descrição |
|--------|-----------|
| `queued` | Criado, aguardando ingest |
| `downloading` | yt-dlp |
| `transcribing` | |
| `analyzing` | Gemini |
| `awaiting_approval` | Pipeline 4 ou approve gate |
| `generating_metadata` | |
| `rendering` | |
| `completed` | |
| `failed` | |
