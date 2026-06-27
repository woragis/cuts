# Prompts v2 — Completude informativa

Instruções compartilhadas por **A, B e C**. Arquivos em `prompts/` são templates; o script injeta URL, chunk window e segments.

## System (todas as fases)

```
Você é editor de vídeo para canal político brasileiro (MBL / Arthur do Val).
Idioma: português do Brasil.
Retorne APENAS JSON válido, sem markdown.

Prioridade: cortes COMPLETOS e INFORMATIVOS sobre um assunto/tópico.
NÃO é obrigatório começar com hook forte — o viewer precisa entender o assunto inteiro.
Se houver trechos de perda de tempo (enrolação, repetição, pausa longa, off-topic breve),
liste em uselessParts com severity trim|optional|keep_for_context.
```

## Fase A — Gemini (vídeo)

Ver `prompts/phase_a_gemini.md`.

Diferencial: vê **expressão, gestos, reações da audiência, B-roll visual**. Use isso para marcar momentos emocionais, mas **não** sacrifice completude por clip curto.

Targets por chunk (~15 min):

- 2–4 shorts candidatos
- 0–1 long cut se arco completo couber na janela

## Fase B — OpenAI (transcript Whisper)

Ver `prompts/phase_b_openai_transcript.md`.

Diferencial: vê **exatamente o que foi dito**, ideal para argumentos, números, citações. Marque uselessParts quando o locutor repete ou divaga.

Targets por chunk (~900s):

- 2–3 shorts
- 0–1 long cut

## Fase C — Merge (Claude + OpenAI)

Ver `prompts/phase_c_merge.md`.

Inputs: clusters temporais de candidatos A+B, **transcript estruturado por cluster** (`transcriptBefore` + in-cluster + after), uselessParts de cada candidato.

A fase C é quem **corrige** cortes de A/B que começam no meio da discussão — lendo o texto anterior e aplicando `extend`.

Ações: `merge | extend | keep_separate | reject`

Output: cortes finais + `extendedBecause` + uselessParts consolidado + decisions log.

## Duração alvo

| Formato | Min | Ideal | Max |
|---------|-----|-------|-----|
| Short | 45s | **~70s** (resumido c/ contexto) | **130s** (explicativo) |
| Long | 4 min | **~8 min** (tópico focado) | **15 min** (explicação completa) |

Shorts e longs: **duração flexível** — ideal como guia, não teto rígido quando completude exige mais.
Longs podem ficar **abaixo** do ideal se o assunto for focado; acima quando “explica tudo”.

Estender (`extend`) se o candidato tem payoff mas falta setup — **preferível a rejeitar**.

## Transcript na fase C (config `merge` no fixture)

| Campo | Default | Uso |
|-------|---------|-----|
| `transcriptPadBeforeSec` | 240 | Texto **antes** dos candidatos (contexto) |
| `transcriptPadAfterSec` | 120 | Texto depois (conclusão) |
| `transcriptMaxSegmentsBefore` | 120 | Limite tokens — prioriza o “antes” |
| `longClusterPadBeforeSec` | 360 | Contexto extra para clusters long (≥3 min) |
| `longClusterMaxSegmentsInCluster` | 350 | Mais transcript in-cluster para longs |

## Anti-patterns (não incentivar)

- "Comece no momento mais chocante" como regra default
- Shorts < 40s salvo citação isolada excepcional
- Long cut que é só concatenação sem arco narrativo
