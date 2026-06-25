# Communities, editorial e catálogo de publicação

Modelo de dados para **multi-nicho**, **hub/spoke** e **catálogo + agenda** multi-plataforma.

Complementa [EDITORIAL-CHANNELS.md](./EDITORIAL-CHANNELS.md) e [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md).

---

## Hierarquia

```text
community (nicho)
  └── editorial_channel (flagship | satellite)
        └── connected_account[] (por platform + slot)
              └── publish_plan (cut × platform × horário)
```

**Exemplo — nicho política:**

```text
community: politica
  ├── flagship: brasil-em-debate
  │     └── accounts: youtube/hub-1, tiktok/hub-1, instagram/hub-1
  ├── satellite: cortes-arthur-mbl
  │     └── accounts: youtube/satellite-1.1, ...
  └── satellite: cortes-...
```

---

## 1. Communities

Agrupa identidade de negócio, regras de cadência e editoriais.

```sql
CREATE TABLE communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,          -- politica | tech | financas | games
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',

    -- Regras default para scheduling.plan (JSON)
    scheduling_rules JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- routing default hub/spoke
    routing_policy JSONB NOT NULL DEFAULT '{
      "hubTopN": 5,
      "hubTopShortsN": 2,
      "minScoreForHub": 0.75
    }'::jsonb,

    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Seeds iniciais

| slug | name | Notas |
|------|------|-------|
| `politica` | Política | 3–4 lives/dia, hub brasil-em-debate |
| `tech` | Tech | 3–5 YouTubers |
| `financas` | Finanças | 5+ canais |
| `games` | Games | ritmo alto, 8 shorts/canal/dia |

---

## 2. Editorial channels (atualizado)

Estende o modelo em [EDITORIAL-CHANNELS.md](./EDITORIAL-CHANNELS.md):

```sql
ALTER TABLE editorial_channels
    ADD COLUMN community_id UUID NOT NULL REFERENCES communities (id);

-- publish_account_id vira conjunto por plataforma (ver connected_accounts)
```

Cada `editorial_channel` pertence a **uma** `community`.

Contas de publicação: **N por plataforma** via `connected_accounts.editorial_channel_id`.

---

## 3. Connected accounts (multi-plataforma)

```sql
CREATE TABLE connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    community_id UUID NOT NULL REFERENCES communities (id),
    editorial_channel_id UUID REFERENCES editorial_channels (id),

    platform TEXT NOT NULL,             -- youtube | tiktok | instagram | twitter | ...
    slot_id TEXT NOT NULL,              -- hub-1, satellite-1.1, ... (legado dev-servers)

    external_id TEXT,                   -- channel_id | open_id | ig_user_id
    display_name TEXT,
    username TEXT,

    -- tokens criptografados (AES-GCM ou vault)
    credentials_encrypted BYTEA NOT NULL,
    token_expires_at TIMESTAMPTZ,
    scopes JSONB,

    status TEXT NOT NULL DEFAULT 'active',  -- active | expired | revoked
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (platform, slot_id),
    UNIQUE (editorial_channel_id, platform)  -- 1 conta YT por editorial
);
```

### Import do dev-server

```text
POST /v1/connected-accounts/import
{
  "platform": "instagram",
  "slotId": "satellite-1.1",
  "editorialChannelId": "uuid",
  "accountJson": { ... }   // JSON baixado do meta-dev-server
}
```

App OAuth (`client_id` / `client_secret`) permanece em **env**; tokens por conta no DB.

---

## 4. Source profiles

Perfil por live/pessoa dentro de um nicho ([SOURCE-PROFILES.md](./SOURCE-PROFILES.md)).

```sql
CREATE TABLE source_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL REFERENCES communities (id),
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    default_satellite_editorial_id UUID REFERENCES editorial_channels (id),
    reframing_preset JSONB DEFAULT '{}'::jsonb,
    UNIQUE (community_id, slug)
);
```

Usado no run:

```json
{
  "communityId": "uuid-politica",
  "sourceProfileId": "uuid-mbl-arthur-live"
}
```

---

## 5. Runs e cuts (campos novos)

### Run

```json
{
  "communityId": "uuid",
  "sourceProfileId": "uuid",
  "editorialChannelId": "uuid-flagship-default",
  "options": { "routingMode": "hub_and_spoke" }
}
```

### Cut (após routing)

```json
{
  "targetEditorialChannelId": "uuid",
  "routingReason": "hub_top_score",
  "routingRank": 1,
  "renderStatus": "completed",
  "catalogStatus": "ready"
}
```

---

## 6. Publish catalog

Catálogo de cortes **renderizados**, prontos para distribuição.

```sql
CREATE TABLE publish_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cut_id UUID NOT NULL REFERENCES cuts (id),
    run_id UUID NOT NULL REFERENCES runs (id),
    community_id UUID NOT NULL REFERENCES communities (id),
    editorial_channel_id UUID NOT NULL REFERENCES editorial_channels (id),

    cut_type TEXT NOT NULL,             -- short | long
    render_path TEXT NOT NULL,
    thumbnail_path TEXT,

    title TEXT,
    description TEXT,
    captions JSONB DEFAULT '{}'::jsonb,  -- por plataforma: { "tiktok": "...", "instagram": "..." }

    status TEXT NOT NULL DEFAULT 'ready',
    -- ready | scheduled | publishing | published | failed | skipped

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (cut_id, editorial_channel_id)
);
```

**Transição:** quando render completa → insert `publish_catalog` com `status = ready`.

---

## 7. Publish plans

Agenda de **quando** e **onde** publicar.

```sql
CREATE TABLE publish_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    catalog_id UUID NOT NULL REFERENCES publish_catalog (id),
    platform TEXT NOT NULL,
    connected_account_id UUID NOT NULL REFERENCES connected_accounts (id),

    scheduled_at TIMESTAMPTZ NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',

    privacy TEXT DEFAULT 'private',     -- youtube: private + publishAt
    platform_options JSONB DEFAULT '{}'::jsonb,

    status TEXT NOT NULL DEFAULT 'pending',
    -- pending | approved | enqueued | publishing | done | failed | cancelled

    external_post_id TEXT,
    external_url TEXT,
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,

    created_by TEXT DEFAULT 'scheduling.plan',  -- agent | manual
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_publish_plans_due ON publish_plans (status, scheduled_at)
    WHERE status IN ('pending', 'approved');
```

### Fluxo de status

```text
scheduling.plan → pending
humano aprova   → approved   (fase 1)
scheduler       → enqueued → publishing → done | failed
```

Fase 2: `pending` → `approved` automático se regras OK.

---

## 8. API (proposto)

```text
GET    /v1/communities
POST   /v1/communities
GET    /v1/communities/{id}/editorial-channels

GET    /v1/publish-catalog?communityId=&status=ready
GET    /v1/publish-plans?date=2026-06-26&communityId=
POST   /v1/publish-plans/{id}/approve
PATCH  /v1/publish-plans/{id}              -- mover horário manual
POST   /v1/runs/{id}/schedule             -- dispara scheduling.plan

POST   /v1/connected-accounts/import
GET    /v1/connected-accounts?communityId=
```

---

## 9. Relação com slots dev-server

Slots compartilhados entre plataformas ([post/ROADMAP.md](../backend/worker/scripts/post/ROADMAP.md)):

| slot_id | Uso típico |
|---------|------------|
| `hub-1` | flagship do nicho |
| `satellite-1.1` | satélite 1 |
| `satellite-1.2` | satélite 2 |

`connected_accounts.slot_id` liga ao JSON exportado pelos OAuth servers (Railway).

---

## 10. Implementação atual

| Entidade | Status |
|----------|--------|
| `communities` | ❌ spec |
| `editorial_channels` + `community_id` | ❌ spec parcial em EDITORIAL-CHANNELS |
| `connected_accounts` | ❌ spec em PUBLISH-YOUTUBE |
| `publish_catalog` | ❌ spec |
| `publish_plans` | ❌ spec |
| `source_profiles` (DB) | ❌ JSON files hoje |

Próxima migration sugerida: **008_communities_and_publish.sql**.
