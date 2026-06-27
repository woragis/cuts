# Hooks, re-hooks e transições — plano de melhoria

Documentação da implementação atual + objetivos para cortes profissionais com melhor retenção **sem sacrificar completude informativa**.

## Filosofia v2

| Antes (v1) | Agora (v2) |
|------------|------------|
| Hook forte no segundo 0 | Tópico completo; hook opcional |
| Re-hook hardcoded MEI | Re-hook derivado do veredito / uselessParts |
| Zoom fixo reframing | Zoom dinâmico + reset em mudança de assunto |

---

## Implementação atual

### Re-hook preset

```237:254:backend/worker/scripts/treatment/treatment_lib.py
def default_rehook_for_cut(cut: dict[str, Any]) -> dict[str, Any] | None:
    """Re-hook preset: peak teaser -> context -> buildup -> finale."""
    cut_id = str(cut.get("id", ""))
    title = str(cut.get("title", "")).lower()
    if cut_id != "long-cut-03" and "mei" not in title:
        return None
    peak = float(cut.get("hookPeakSec", 52))
    teaser_end = peak + 4
    return {
        "type": "rehook",
        "peakSec": peak,
        "segments": [
            {"startSec": peak, "endSec": teaser_end, "role": "peak_teaser"},
            {"startSec": 0, "endSec": 25, "role": "context"},
            {"startSec": 25, "endSec": peak, "role": "buildup"},
            {"startSec": peak, "endSec": None, "role": "finale"},
        ],
    }
```

**Limitações:**
- Só ativa para `long-cut-03` ou título contendo "mei"
- `hookPeakSec` fixo (52s) — não vem do veredito ABC
- Concatena segmentos via `hook_segments_to_keeps` — jump cuts secos, sem transição visual

### Render re-hook

```279:306:backend/worker/scripts/treatment/treatment_lib.py
def render_rehook_only(...):
    """Re-hook: peak teaser, context, buildup, then finale (calculo ao vivo MEI)."""
    ...
    keeps = hook_segments_to_keeps(hook["segments"], info["duration"])
    return _concat_clip_segments(...)
```

Sem crossfade, zoom, ou áudio bridge entre segmentos.

---

## Plano de melhoria (testar em `tests/render/`)

### 1. Hook inteligente a partir do veredito

| Campo novo no cut | Uso |
|-------------------|-----|
| `hookPeakSec` | IA sugere momento de maior tensão/informação |
| `hookOptional` | `true` → pular re-hook, ir direto silence→music |
| `uselessParts` | Excluir do peak teaser se severity=trim |

**Teste:** comparar `RENDER_MODE=hook` com e sem `hookOptional` no mesmo corte.

### 2. Tipos de hook

| Tipo | Quando | Estrutura |
|------|--------|-----------|
| `direct` | Short informativo | Sem reorder — clip linear |
| `rehook` | Long ou short com payoff claro | peak → context → buildup → finale |
| `teaser_only` | Short viral pontual | 3–5s peak + resto linear |

### 3. Transições visuais (reframing step)

Matriz a validar manualmente:

| Transição | Descrição | Caso de uso |
|-----------|-----------|-------------|
| **Corte seco** | Hard cut, zoom default | Mudança de subtópico |
| **Zoom in hold** | Ken Burns lento durante explicação | Monólogo denso |
| **Zoom punch** | Zoom rápido no peak teaser | Re-hook abertura |
| **Zoom reset** | Volta crop/zoom default após punch | Antes de context |

**Implementação alvo:** estender `render_reframing_only` / plano Gemini layout com keyframes `zoomStart`, `zoomEnd`, `easing`.

### 4. Transições auditivas

- **Música:** ducking já via LUFS/dB sidechain — validar short vs long
- **Re-hook:** micro fade (2–4 frames) nos joins de segmento para evitar click
- **Outro long:** crossfade 0.5–1s conteúdo→card + música outro sobre fade

### 5. Outro (long only)

Fluxo desejado:

```
clip_subs.mp4 ──fade video──► outro_image.png
         └──crossfade audio──► outro_music.mp3
```

Validar em `RENDER_MODE=outro` com checklist seção 6.

---

## Matriz de testes sugerida

| Cut | Formato | Hook type | Transição | Prioridade |
|-----|---------|-----------|-----------|------------|
| merged-short-01 | short | direct | seco | P0 |
| merged-short-05 | short | teaser_only | zoom punch | P1 |
| long-cut-03 | long | rehook | zoom + outro | P0 |
| long-cut-01 | long | direct | zoom hold | P1 |

Rodar via [`RENDER-MATRIX.md`](RENDER-MATRIX.md).

---

## Critérios de sucesso

1. Viewer entende o assunto **mesmo sem** re-hook
2. Re-hook aumenta retenção nos primeiros 5s **sem** confundir
3. Zoom não distrai da fala
4. Outro long parece “encerramento de programa”, não append brusco
5. uselessParts `trim` refletidos no clip final

---

## Próximos passos código (pós-validação manual)

1. `build_treatment_brief()` — ler `hookPeakSec`, `hookOptional`, `uselessParts` do veredito v2
2. Generalizar `default_rehook_for_cut()` → `rehook_from_verdict(cut)`
3. FFmpeg: crossfade nos joins de re-hook
4. Reframing: keyframes zoom no plan JSON
