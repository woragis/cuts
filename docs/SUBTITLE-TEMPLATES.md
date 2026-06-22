# Templates de legenda (subtitle burn-in)

Biblioteca de estilos para legendas queimadas em **shorts** (9:16). Validados no prototipo `woragis/canal/legendas-mvp`.

---

## Comportamento aprovado

| Aspecto | Decisao |
|---------|---------|
| Animacao | `\k` ASS — troca **instantanea** de cor na palavra ativa |
| Palavra ja falada | permanece na cor "spoken" |
| Palavra pendente | cor "unspoken" (cinza) |
| Timing | word timestamps do Whisper (nao estimativa) |
| Chunks | 3 palavras por bloco na tela |
| Posicao | centro (`alignment: 5`) |
| Sem | sweep `\kf`, scale/pop, cores por canal |

---

## Templates seed (dia 0)

| ID | Slug | Spoken | Unspoken | Uso |
|----|------|--------|----------|-----|
| `b2222222-2222-2222-2222-222222222201` | `default` | `#FFFFFF` | `#707070` | Todos os canais |
| `b2222222-2222-2222-2222-222222222202` | `mission` | `#FFD700` | `#909090` | MBL / missao politica |

Arquivos fonte: `backend/seeds/subtitle-templates/*.json`  
Migration: `backend/migrations/004_subtitle_templates.sql`

---

## Modelo de dados

### Tabela `subtitle_templates`

```sql
id UUID PK
name TEXT
slug TEXT UNIQUE
description TEXT
config JSONB   -- colors, font, layout, animation
deleted_at, created_at, updated_at
```

### `config.json` (por template)

```json
{
  "colors": {
    "spoken": "#FFFFFF",
    "unspoken": "#707070",
    "outline": "#000000"
  },
  "font": {
    "family": "Arial Black",
    "size": 72,
    "outlineWidth": 5
  },
  "layout": {
    "alignment": 5,
    "marginV": 0,
    "maxWordsPerChunk": 3
  },
  "animation": {
    "mode": "instant_karaoke",
    "tag": "k",
    "fadeMs": 80
  }
}
```

### ASS gerado

- **PrimaryColour** = `spoken` (palavra ativa + ja faladas no chunk)
- **SecondaryColour** = `unspoken` (palavras ainda nao ditas)
- Cada palavra: `{\kNN}texto` onde `NN` = duracao em centesimos (Whisper `end - start`)

Exemplo:

```ass
Dialogue: 0,0:00:00.00,0:00:00.68,Karaoke,,0,0,0,,{\an5\fad(80,80)}{\k4}essas {\k30}duas {\k34}aqui
```

---

## API (F12 — a implementar)

```text
GET    /v1/subtitle-templates
GET    /v1/subtitle-templates/{id}
POST   /v1/subtitle-templates
DELETE /v1/subtitle-templates/{id}
```

### Uso no run

```json
{
  "youtubeUrl": "...",
  "thumbnailTemplateId": "11111111-1111-1111-1111-111111111111",
  "subtitleTemplateId": "b2222222-2222-2222-2222-222222222201",
  "options": {
    "burnSubtitles": true
  }
}
```

Default quando `burnSubtitles: true` e `subtitleTemplateId` omitido: template `default`.

---

## Pipeline (F12)

```text
transcribe.run
  → transcript.json com words[] (Whisper word timestamps)
subtitle.generate
  → shorts/{cutId}/subtitles.ass  (subtitle_engine.py + template config)
render.short
  → ffmpeg -vf subtitles=subtitles.ass
```

Worker: `backend/worker/cuts_worker/subtitle_engine.py`

---

## Prototipo visual

Demos de 30s gerados em:

```text
woragis/canal/legendas-mvp/output/default/demo.mp4
woragis/canal/legendas-mvp/output/mission/demo.mp4
```

Script: `woragis/canal/legendas-mvp/render_whisper_demo.py`

---

## Identidade por canal

Legendas **nao** variam por nicho (gameplay, podcast, etc.). Identidade visual fica em:

- thumbnail template
- titulo / descricao
- eventual `mission` para canais politicos

Todos os outros canais usam `default`.

---

## Fase de implementacao

Ver [MVP-PHASES.md](./MVP-PHASES.md) — **F12 Subtitle templates + burn-in**.

Seeds e motor ASS ja estao no repo; falta API CRUD, worker `subtitle.generate`, word timestamps no transcribe e integracao no `render.short`.
