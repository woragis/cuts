# Pipeline ABC — Detecção de cortes (v2)

Teste local do workflow completo com **4 vereditos** para comparar qual IA decide melhor.

## Vereditos

| Fase | Arquivo | IA | Input |
|------|---------|-----|-------|
| **A** | `verdict_a.json` | Gemini (nativo YouTube) | URL do VOD |
| **B** | `verdict_b.json` | OpenAI | Transcript Whisper |
| **C-Claude** | `verdict_c_claude.json` | Claude Sonnet | A + B + transcript |
| **C-OpenAI** | `verdict_c_openai.json` | GPT-4o | A + B + transcript |

## Filosofia v2

Ver [`PROMPTS-v2.md`](PROMPTS-v2.md) e [`SCHEMA-verdict.md`](SCHEMA-verdict.md).

Resumo:

1. **Completude > hook no início** — o corte deve entregar o assunto inteiro (setup → desenvolvimento → conclusão).
2. **Shorts ~70s ideal, até ~130s** — resumo com contexto; até ~2 min se a explicação exigir.
3. **Fase C estende com transcript** — `transcriptBefore` corrige cortes que começam na discussão.
4. **`uselessParts`** — marcar desde A e B; C consolida e propõe trim no render.
5. **Long cuts** — ideal ~8 min, até ~15 min se explicar tudo; podem ficar <8 min se focados.

## Como rodar

```bash
cd backend/worker

# Reutilizar fase A existente + rodar B + C duplo
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export WHISPER_REUSE=1

python ../../tests/cuts/run_abc_pipeline.py \
  --fixture ../../tests/fixtures/default-run.json

# Só merge (A e B já existem em output/)
SKIP_PHASE_A=1 SKIP_PHASE_B=1 python ../../tests/cuts/run_abc_pipeline.py
```

### Variáveis de ambiente

| Var | Default | Descrição |
|-----|---------|-----------|
| `OUTPUT_DIR` | `tests/cuts/output/{runId}` | Pasta de saída |
| `VIDEO_CUTS_JSON` | baseline Gemini em fixtures | Atalho para fase A |
| `SKIP_PHASE_A` | — | Reutiliza `verdict_a.json` |
| `SKIP_PHASE_B` | — | Reutiliza `verdict_b.json` |
| `SKIP_TRANSCRIPT` | — | Reutiliza `transcript.json` |
| `WHISPER_REUSE` | `1` | Não re-transcreve se transcript existe |
| `PHASE_B_MODEL` | `gpt-4o` | OpenAI fase B |
| `PHASE_C_CLAUDE_MODEL` | `claude-sonnet-4-6` | Merge Claude |
| `PHASE_C_OPENAI_MODEL` | `gpt-4o` | Merge OpenAI |
| `RUN_GEMINI_A` | — | Se `1`, re-roda Gemini (caro/lento) |

## Outputs

```
tests/cuts/output/{run_id}/
  transcript.json
  verdict_a.json          # Gemini vídeo
  verdict_b.json          # OpenAI transcript
  verdict_c_claude.json   # merge Claude
  verdict_c_openai.json   # merge OpenAI
  validation.md           # checklist humano com links YouTube
  abc_run.log
```

## Próximo passo

Escolher veredito C (Claude ou OpenAI) → [`../render/README.md`](../render/README.md).

## Baseline histórico

`fixtures/results/20260624T225609Z_eKxFuD3-pos/` contém run antigo (B era Claude). Compare com novos runs v2.
