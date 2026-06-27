# Editorial channels

Canal **editorial** = identidade de produção e publicação (não é a URL do YouTube; isso é `connected_account`).

Dois tipos:

| `type` | Exemplo | Função |
|--------|---------|--------|
| `flagship` | `brasil-em-debate` | Top cortes, marca agnóstica, longo prazo |
| `satellite` | `cortes-arthur-mbl` | Overflow por live/pessoa, identidade focada |

---

## Modelo de dados (proposto)

```sql
CREATE TABLE editorial_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('flagship', 'satellite')),
    niche TEXT,  -- politica | financas | games | tech

    thumbnail_template_id UUID REFERENCES templates (id),
    subtitle_template_id UUID REFERENCES subtitle_templates (id),

    -- Thumbnail (ver THUMBNAIL-MODES.md)
    thumbnail_mode TEXT NOT NULL DEFAULT 'pattern_frame',
    frame_selection TEXT NOT NULL DEFAULT 'auto',  -- auto | manual | fixed_sec
    frame_fixed_sec DOUBLE PRECISION,

    -- Áudio
    background_music_asset_id UUID,
    background_music_placement TEXT DEFAULT 'body',  -- body
    background_music_loop TEXT DEFAULT 'extended', -- extended (~1h) recomendado

    outro_image_asset_id UUID,
    outro_music_asset_id UUID,
    outro_start_sec DOUBLE PRECISION DEFAULT 8,
    outro_duration_sec DOUBLE PRECISION DEFAULT 15,  -- 0 = sem outro (shorts)

    -- Publicação (ver PUBLISH-YOUTUBE.md)
    publish_account_id UUID,  -- FK connected_accounts, nullable até OAuth

    -- Routing (só flagship costuma ter policy global; satélite herda source)
    routing_policy JSONB DEFAULT '{}'::jsonb,

    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE editorial_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    editorial_channel_id UUID NOT NULL REFERENCES editorial_channels (id),
    kind TEXT NOT NULL,  -- pattern | character | background_music | outro_image | outro_music
    filename TEXT NOT NULL,
    mime_type TEXT,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Defaults por satélite

Cada satélite carrega **identidade visual e auditiva própria**:

- `thumbnail_template` + `pattern.png` (+ `character.png` se modo character)
- `subtitle_template` (cores/fonte do canal)
- `background_music` (body, ducking, extended)
- `outro_image` + `outro_music` (ou `outro_duration_sec: 0` para shorts)
- `publish_account_id` → conta Google dedicada

O flagship (`brasil-em-debate`) usa presets “debate” genéricos; satélites usam presets alinhados à live/pessoa.

---

## API (proposto)

```text
GET    /v1/editorial-channels
POST   /v1/editorial-channels
GET    /v1/editorial-channels/{id}
PATCH  /v1/editorial-channels/{id}
DELETE /v1/editorial-channels/{id}
POST   /v1/editorial-channels/{id}/assets   # multipart: pattern, character, music, outro
```

### Uso no run

```json
{
  "youtubeUrl": "...",
  "editorialChannelId": "uuid-flagship",
  "sourceProfileId": "uuid-mbl-arthur-live",
  "options": {
    "burnSubtitles": true,
    "treatmentChannel": "politica-mbl",
    "routingMode": "hub_and_spoke"
  }
}
```

Após routing no approve, cada cut recebe `targetEditorialChannelId` (pode diferir do run default).

---

## Seeds iniciais (política)

| slug | type | Notas |
|------|------|-------|
| `brasil-em-debate` | flagship | top 5 por batch |
| `cortes-arthur-mbl` | satellite | Arthur / live principal |
| `cortes-*` | satellite | um por fonte frequente |

Migrar conteúdo de `worker/cuts_worker/channels/politica-mbl.json` para o flagship; satélites começam como cópia ajustável.

---

## Implementação atual

- ❌ Tabela e API não existem
- ⚠️ Protótipo: `worker/cuts_worker/channels/politica-mbl.json` + assets em `scripts/treatment/assets/`
- ✅ Templates thumb/legenda: CRUD separado, ainda não ligados ao editorial
