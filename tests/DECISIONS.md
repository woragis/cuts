# Decisões fechadas — testes (Jun/2026)

Registro do que foi acordado antes de rodar testes. Atualizar aqui quando mudar política.

## Escopo atual

| Item | Decisão |
|------|---------|
| Formato foco | **Long 16:9** primeiro |
| Shorts / vertical 9:16 | **Depois** — quando long estiver redondo |
| Refraining + assets | **Por último** |

## Cortes (ABC)

| # | Decisão |
|---|---------|
| 1 | Testar **qualquer long** do veredito — sem lista fixa |
| 2 | **C-Claude vs C-OpenAI** — comparar depois; você escolhe o melhor manualmente |
| 3 | Run atual: **OpenAI** (B + C-OpenAI). Claude opcional (`SKIP_PHASE_C_CLAUDE=1`) |
| — | Shorts ~70–130s; longs ~8–15 min (flexível) |
| — | Fase C estende com `transcriptBefore`; `uselessParts` desde A/B |

## Render long (pipeline v2)

Ordem fixa:

```
extract → silence (+ uselessParts trim) → hook → EDL → legendas → música → outro
```

| # | Decisão |
|---|---------|
| 4 | Spec em [`render/PIPELINE-LONG-v2.md`](render/PIPELINE-LONG-v2.md) |
| 5 | **Re-hook no long: sim**, estilo `imperceptible` (2–4s teaser, mesmo look/som) |
| 6 | Shorts fora do escopo até long validado |

## Hook

- Veredito traz `hookCandidates[]` (futuro / schema)
- **Hook picker** (IA barata OpenAI) escolhe 1 candidato → `hookPlan`
- Long default: `hookStyle: imperceptible`
- Short (futuro): pode ser mais marcado

## Silence

- `uselessParts` com `severity: trim` → **corte automático** no passo silence (junto com silencedetect)
- `optional` / `keep_for_context` → não cortar auto

## EDL

- Input: clip **pós-silence + pós-hook** (probe baixo + transcript do clip final)
- Output: `editPlan.json` — zoom/hold leve, horizontal 16:9
- IA barata (OpenAI mini/flash)

## Modelos (run OpenAI)

Ver `fixtures/default-run.json` → `models` e `fixtures/openai-run.json`.

Nunca commitar API keys — só variáveis de ambiente.
