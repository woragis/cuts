# Linhagem dos scripts de teste

Scripts em `tests/` derivam dos experimentos em `backend/worker/scripts/`.

## Cuts

| Arquivo tests | Origem | Mudanças v2 |
|---------------|--------|-------------|
| `cuts/run_abc_pipeline.py` | `scripts/test_dual_merge_claude.py` | Fase B = OpenAI (não Claude); C duplo (Claude + OpenAI); schema `uselessParts`; prompts informativos |
| `cuts/prompts/*.md` | prompts inline do script antigo | Extraídos e revisados |

## Render

| Arquivo tests | Origem | Mudanças v2 |
|---------------|--------|-------------|
| `render/run_treatment_cut.py` | `scripts/treatment/run_first_test.py` | Paths → `tests/render/output/`; `CUTS_JSON` aponta para veredito ABC |
| `render/run_short_finish.py` | `scripts/treatment/run_short_finish_test.py` | Idem |
| `render/channels/` | `scripts/treatment/channels/` | Cópia simbólica via import do worker em runtime |

## Fixtures

| Path | Origem |
|------|--------|
| `fixtures/results/20260624T225609Z_eKxFuD3-pos/*` | `scripts/results/20260624T225609Z_eKxFuD3-pos/*` |

Para refrescar baseline Gemini-only: copiar nova pasta de `scripts/results/` após rodar sweep antigo.
