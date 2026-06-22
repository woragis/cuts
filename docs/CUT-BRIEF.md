# cutBrief — o que procurar no vídeo

Campo de texto livre enviado ao **Gemini** no job `analyze.gemini`. Descreve **que tipo de corte** extrair do vídeo.

---

## Campo na API

```json
{
  "cutBrief": "Achar 10 shorts engraçados e 3 momentos onde falam de salário em tech",
  "cutBriefPreset": "funny"
}
```

- `cutBrief` — sempre enviado ao LLM (pode ser enriquecido pelo preset).
- `cutBriefPreset` — opcional; expande para prompt base + append do texto livre.

---

## Presets

| Preset | ID | Prompt base (Gemini) |
|--------|-----|----------------------|
| Viral hooks | `viral_hooks` | Frases fortes, punchlines, reações, momentos de alta energia |
| Engraçado | `funny` | Risadas, absurdos, fails, humor involuntário |
| Polêmico | `controversial` | Opiniões fortes, debates, takes controversos |
| Tutorial | `tutorial_steps` | Passos claros, “como fazer X”, explicações didáticas |
| Entrevista | `interview_tips` | Dicas de carreira, salário, processo seletivo, “cai no Google” |
| Story arc | `story_arc` | Mini-história com começo, conflito e conclusão |
| LeetCode / DSA | `leetcode_dsa` | Questões, complexidade, erros comuns, Accepted (Woragis) |
| Custom | `custom` | Usa só o texto livre do usuário |

---

## Exemplos de cutBrief (texto livre)

```text
"Momentos engraçados e reações exageradas do host"

"Trechos onde explicam algoritmos com exemplos visuais, 30-60 segundos cada"

"Partes polêmicas sobre IA substituir programadores"

"Melhores dicas de entrevista técnica, frases completas"

"Highlights de quando o convidado conta histórias pessoais"
```

---

## O que o Gemini recebe

```text
Contexto:
- URL / título do vídeo
- Duração total
- channelContext (opcional)
- transcript.json (segmentos com timestamps)
- targets (count, min/max duração)
- cutBrief + preset

Tarefa:
Retornar cuts.json com shorts[] e/ou longCuts[]
Cada cut: start, end, title, reason, score (0-1)
Timestamps precisos, sem sobreposição excessiva
Respeitar min/max de duração
```

---

## Pipeline 5 (sem cutBrief)

Quando `pipeline: "render_from_cuts"`, o usuário fornece `cuts` pronto — `cutBrief` é ignorado.

Fontes comuns:

- IA do YouTube (paste manual)
- Pipeline 4 + edição manual do JSON
- Capítulos do vídeo convertidos para intervals
