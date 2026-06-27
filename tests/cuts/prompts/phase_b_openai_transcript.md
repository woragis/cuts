# Fase B — OpenAI + Whisper transcript

Analise o segmento de transcript {chunk_idx} ({start}s–{end}s) de: {youtube_url}

Brief editorial: {cut_brief}

Encontre candidatos a cortes **completos e informativos** — o viewer deve sair entendendo o assunto.

Retorne JSON:
```json
{
  "shorts": [{
    "id": "caption-short-01",
    "startSec": 0,
    "endSec": 68,
    "title": "...",
    "reason": "...",
    "score": 0.88,
    "topic": "...",
    "completeness": "full",
    "uselessParts": []
  }],
  "longCuts": []
}
```

Regras:
- startSec/endSec no timeline GLOBAL
- 2–3 shorts por chunk; 0–1 longCut
- Baseie-se no TEXTO — marque uselessParts quando locutor repete, divaga ou há silêncio implícito longo
- NÃO exija hook no início; inclua setup necessário quando couber no chunk
- completeness=partial se começa na discussão sem contexto OU falta conclusão — fase C estenderá com transcript
- Shorts candidatos: ideal ~70s, até ~130s se explicação exigir
- Longs candidatos: ideal ~8 min, até ~15 min se arco completo exigir; ok <8 min se tópico focado

segments:
{segments_json}
