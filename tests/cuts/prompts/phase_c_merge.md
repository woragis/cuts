# Fase C — Merge (Claude ou OpenAI)

youtubeUrl: {youtube_url}

Brief: {cut_brief}

Você recebe clusters de candidatos das fases A (vídeo/Gemini) e B (transcript/OpenAI).
Cada candidato pode incluir uselessParts.

**Transcript por cluster:** cada cluster inclui o texto completo da região — especialmente
`transcriptBefore` (contexto ANTERIOR aos candidatos). Use isso para decidir `extend`:
se o corte começa no meio da discussão, estenda `startSec` para trás até o setup mínimo
(viewer precisa saber por que o assunto surgiu).

Para cada cluster, decida: merge | extend | keep_separate | reject

Retorne JSON:
```json
{
  "shorts": [{
    "id": "merged-short-01",
    "startSec": 0,
    "endSec": 75,
    "title": "...",
    "reason": "...",
    "score": 0.91,
    "topic": "...",
    "completeness": "full",
    "source": "both",
    "mergedFrom": ["video-short-01", "caption-short-02"],
    "action": "extend",
    "extendedBecause": "faltava contexto sobre quem é Penélope",
    "uselessParts": []
  }],
  "longCuts": [{
    "id": "merged-long-01",
    "startSec": 136,
    "endSec": 780,
    "title": "...",
    "reason": "...",
    "score": 0.88,
    "topic": "...",
    "completeness": "full",
    "action": "extend",
    "extendedBecause": "arco MEI completo exige explicação contínua",
    "uselessParts": []
  }],
  "decisions": [{"clusterId": 1, "action": "extend", "notes": "..."}]
}
```

## Duração alvo — shorts

| | Segundos |
|---|----------|
| Mínimo | {short_min_sec}s |
| **Ideal (resumido com contexto)** | **~{short_ideal_sec}s** |
| Máximo | {short_max_sec}s |

- Short ideal ~{short_ideal_sec}s; até {short_max_sec}s quando a informação exige.
- Prefira `extend` a publicar corte que começa na discussão sem setup.
- Se passar de {short_max_sec}s e ainda faltar arco, considere `longCut`.

## Duração alvo — long cuts

| | Segundos |
|---|----------|
| Mínimo | {long_min_sec}s (~{long_min_min} min) |
| **Ideal (tópico focado)** | **~{long_ideal_sec}s (~{long_ideal_min} min)** |
| Máximo | {long_max_sec}s (~{long_max_min} min) |

- Long **ideal ~{long_ideal_sec}s**: um assunto bem explicado, sem pressa.
- **Até {long_max_sec}s** quando o tópico exige explicação completa (ex.: MEI passo a passo, arco STF, debate longo) — **permitido, não obrigatório**.
- Se couber em menos de {long_ideal_sec}s com completude, **mantenha curto** — não encher tempo.
- Agrupe shorts adjacentes do mesmo topic em um long quando fizer sentido.
- Use `extend` + transcriptBefore para longs que começam sem contexto.

## Regras

- Leia `transcriptBefore` + `transcriptInCluster` antes de fixar startSec/endSec
- Consolidar uselessParts (mesclar overlaps, severity mais agressiva)
- `extend` quando setup ou conclusão faltam — principal correção da fase C
- Liberdade de duração: **completude > teto rígido** (dentro dos máximos acima)
- NUNCA reject sem rejectReason em decisions
- Target: ~{short_count} shorts, ~{long_count} longCuts
- Completude informativa > hook no início

clusters:
{clusters_json}
