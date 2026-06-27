# Fase A — Gemini (YouTube URL nativa)

Analise o trecho de vídeo {chunk_idx} ({start}s–{end}s) de: {youtube_url}

Brief editorial: {cut_brief}

Encontre candidatos a cortes **completos sobre um tópico** (não precisa hook no primeiro segundo).

Retorne JSON:
```json
{
  "shorts": [{
    "id": "video-short-01",
    "startSec": 0,
    "endSec": 72,
    "title": "...",
    "reason": "...",
    "score": 0.9,
    "topic": "...",
    "completeness": "full",
    "uselessParts": []
  }],
  "longCuts": [{
    "id": "video-long-01",
    "startSec": 0,
    "endSec": 420,
    "title": "...",
    "reason": "...",
    "score": 0.85,
    "topic": "...",
    "completeness": "full",
    "uselessParts": [{"startSec": 120, "endSec": 135, "reason": "pausa longa", "severity": "trim"}]
  }]
}
```

Regras:
- startSec/endSec no timeline GLOBAL do VOD (não relativo ao chunk)
- 2–4 shorts por chunk; 0–1 longCut se arco completo couber
- Shorts: candidatos ~45–130s; ideal ~70s com contexto (fase C refina e estende se faltar setup)
- Longs: candidatos ~4–15 min; ideal ~8 min; até ~15 min se explicar tudo; ok <8 min se focado
- Se o momento interessante começa no meio da fala, marque completeness=partial — C usará transcript para estender
- Marque uselessParts para repetição, enrolação, off-topic breve
- Preferir completude do assunto a punchline isolada
