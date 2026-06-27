# Matriz de render — batch de testes

Combinações recomendadas para inspecionar profissionalismo e retenção.

## Dimensões

| Eixo | Valores |
|------|---------|
| Formato | `short`, `long` |
| RENDER_MODE | silence → hook → reframing → music → subtitles → (outro) → thumbnail |
| Veredito | `verdict_c_claude.json`, `verdict_c_openai.json` |
| Hook | direct / rehook / teaser_only (futuro) |

## Batch script

```bash
# tests/render/run_render_batch.sh
# Uso: ./run_render_batch.sh CUT_ID [CUT_ID...]

CHANNEL_SLUG=politica-mbl
VERDICT=../../tests/cuts/output/20260624T225609Z_eKxFuD3-pos/verdict_c_claude.json
MODES="silence hook reframing music subtitles"

for CUT in "$@"; do
  for MODE in $MODES; do
    CUT_ID=$CUT RENDER_MODE=$MODE CUTS_JSON=$VERDICT \
      python ../../tests/render/run_treatment_cut.py
  done
  # Long: outro extra
  if [[ "$CUT" == long-* ]]; then
    CUT_ID=$CUT RENDER_MODE=outro CUTS_JSON=$VERDICT \
      python ../../tests/render/run_treatment_cut.py
  fi
done
```

## Cortes sugeridos (VOD eKxFuD3-pos)

### Shorts (prioridade)

| ID | Tópico | Testar |
|----|--------|--------|
| merged-short-01 | abertura / contexto | silence, music, subs |
| merged-short-03 | STF | hook direct |
| merged-short-07 | MEI | hook rehook se peak definido |
| merged-short-12 | Penélope | reframing zoom |

### Longs

| ID | Tópico | Testar |
|----|--------|--------|
| long-cut-01 | arco amplo | music LUFS longo |
| long-cut-03 | MEI cálculo | rehook + outro |
| long-cut-05 | — | outro transição |

> IDs exatos dependem do veredito C escolhido — ajustar após rodar ABC.

## Comparação A/B de veredito no render

1. Renderizar **mesmo CUT_ID** com `verdict_c_claude.json` e `verdict_c_openai.json`
2. Se timestamps diferem, comparar completude + duração + qualidade pós-tratamento
3. Documentar vencedor em `validation.md` (seção render)

## Tempo estimado

~3–8 min por modo por corte (extract + whisper cache). Batch 4 cortes × 5 modos ≈ 1–2h.
