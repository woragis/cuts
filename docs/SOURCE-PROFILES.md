# Source profiles

Perfil de **fonte** = uma live recorrente ou apresentador com composição espacial estável (OBS, reaction cam, painel de notícia).

Relaciona: live → satélite default → presets de reframing.

---

## Modelo (proposto)

```sql
CREATE TABLE source_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    default_satellite_editorial_id UUID REFERENCES editorial_channels (id),

    -- Presets reframing (normalizado 0–1 ou px; ver reframing-architecture.md)
    reframing_presets JSONB NOT NULL DEFAULT '{}'::jsonb,

    presenter_name TEXT,
    cohost_names JSONB DEFAULT '[]'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Exemplo `reframing_presets`

```json
{
  "scenes": {
    "solo_presenter": {
      "presenter": { "cx": 0.35, "cy": 0.42, "presenterZoom": 1.0 }
    },
    "news_reaction": {
      "presenter_pip": { "cx": 0.12, "cy": 0.18, "presenterZoom": 1.1 },
      "news_focus": { "focusCx": 0.68, "focusCy": 0.52, "contentFocusZoom": 1.3 }
    },
    "duo_panel": {
      "presenter": { "cx": 0.28, "cy": 0.45 },
      "cohost": { "cx": 0.72, "cy": 0.45 }
    }
  },
  "presenterTopRatio": 0.38,
  "duoSplitRatio": 0.50
}
```

---

## Run: editorial vs live

| Escolha no run | Comportamento |
|----------------|---------------|
| `editorialChannelId` | Defaults de thumb, legenda, música, outro |
| `sourceProfileId` | Presets reframing + satélite default no routing |
| `sourceProfileId: auto` | Sistema infere profile pela URL/canal da live (futuro) |

**Camadas (não misturar):**

1. **Composição da fonte** — o que o OBS mostra (`solo` / `news_reaction` / `duo`)
2. **Layout editorial** — o que o short 9:16 exibe (policy + presets)

IA barata classifica **qual scene** está ativa; coordenadas vêm do preset quando possível. Gemini full-video continua como fallback ou refinamento.

---

## Modelos Gemini (reframing)

Ver [MODEL-SELECTION.md](./MODEL-SELECTION.md):

- `gemini-2.5-pro` (default qualidade)
- `gemini-3.5-flash` (custo/velocidade)

Override em `run.options.models.reframing`.

---

## Roadmap técnico

1. Seed `mbl-arthur-live`, `mbl-ana-live`, etc.
2. Worker: se `sourceProfile` tem presets, merge com plano Gemini
3. Redis/Postgres learning loop (futuro): runs estáveis atualizam preset

Ref: `worker/scripts/treatment/docs/reframing-architecture.md`

---

## Implementação atual

- ❌ Tabela não existe
- ✅ Gemini reframing em runtime (`cuts_worker/reframing/`)
- ✅ `politica-mbl.json` = seed único global, não por live
