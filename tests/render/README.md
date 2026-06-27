# Render — Testes de tratamento (long first)

Foco atual: **long 16:9** — ver [`PIPELINE-LONG-v2.md`](PIPELINE-LONG-v2.md).

Reframing 9:16 e shorts **fora do escopo** até long validado.

## Pipeline v2 (spec)

```
extract → silence (+ uselessParts) → hook → EDL → legendas → música → outro
```

Decisões: [`../DECISIONS.md`](../DECISIONS.md)  
Schemas: [`SCHEMA-treatment.md`](SCHEMA-treatment.md)

## Wrapper legado

`run_treatment_cut.py` ainda expõe passos antigos (inclui `reframing`). Use para testes incrementais até o worker implementar v2.

### Render local (Windows — fonte pode falhar)

No Windows, libass via `fontsdir` costuma cair em fonte genérica. **Prefira Docker** (abaixo).

```bash
cd backend/worker

export CHANNEL_SLUG=politica-mbl
export CUT_ID=long-cut-03
export CUT_FORMAT=long
export RENDER_MODE=silence
export CUTS_JSON=../../tests/cuts/output/.../verdict_c_openai.json
export OUTPUT_ROOT=../../tests/render/output

python ../../tests/render/run_treatment_cut.py
```

### Render Docker (recomendado — igual Railway)

Mesma imagem do worker: `fontconfig` + Montserrat Bold em `/usr/share/fonts/truetype/mdc/`.

```bash
cd tests/render
chmod +x run_docker_render.sh

# Só legendas (reusa words.json se existir)
./run_docker_render.sh

# Outro / passo específico
RENDER_MODE=outro ./run_docker_render.sh
RENDER_MODE=music ./run_docker_render.sh
```

Build manual:

```bash
cd tests/render
docker compose -f docker-compose.render.yml build
RENDER_MODE=subtitles docker compose -f docker-compose.render.yml run --rm render
```

Verificar fonte no container:

```bash
docker compose -f docker-compose.render.yml run --rm --entrypoint fc-match render "Montserrat:style=Bold"
```

### Modos (`RENDER_MODE`)

| Modo | v2 long | Nota |
|------|---------|------|
| `silence` | ✅ passo 1 | + uselessParts (futuro worker) |
| `hook` | ✅ passo 2 | re-hook imperceptível |
| `edl` | 🔜 spec only — **não implementado** no wrapper ainda |
| `subtitles` | ✅ passo 4 | |
| `music` | ✅ passo 5 | |
| `outro` | ✅ passo 6 | long only |
| `reframing` | ⏸ adiado | vertical depois |

## Checklist

[`CHECKLIST-RENDER.md`](CHECKLIST-RENDER.md) · hooks: [`HOOKS-REHOOKS-TRANSITIONS.md`](HOOKS-REHOOKS-TRANSITIONS.md)
