# Publicação no YouTube

OAuth multi-conta, upload e **agendamento nativo** via YouTube Data API (`publishAt`).

**Sem scheduler próprio na v1** — o YouTube publica no horário agendado.

---

## Contas conectadas

```sql
CREATE TABLE connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL DEFAULT 'youtube',
    external_channel_id TEXT,
    display_name TEXT,
    email TEXT,

    refresh_token_encrypted BYTEA NOT NULL,
    access_token_encrypted BYTEA,
    token_expires_at TIMESTAMPTZ,
    scopes JSONB,

    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- **Um `connected_account` por satélite** (e um por flagship)
- `editorial_channel.publish_account_id` → FK
- App OAuth: só `GOOGLE_OAUTH_CLIENT_ID` + `CLIENT_SECRET` no env (não refresh token por canal)

### Fluxo UI

```text
Configurações → Editorial channel → "Conectar conta Google"
  → OAuth → salva tokens criptografados → lista channel id + nome
```

Repetível: 5 satélites = 5 syncs.

---

## Upload

Worker `publish_cut_to_youtube` evolui para:

```python
publish_cut_to_youtube(
    output_dir=...,
    account_id=...,       # carrega tokens do DB
    privacy="private",    # ou public | unlisted
    publish_at=None,      # RFC3339 UTC — agendamento YouTube
)
```

### Body YouTube (`videos.insert`)

```json
{
  "snippet": { "title": "...", "description": "...", "categoryId": "22" },
  "status": {
    "privacyStatus": "private",
    "publishAt": "2026-06-26T15:00:00.000Z",
    "selfDeclaredMadeForKids": false
  }
}
```

Regras API:

- `publishAt` só com `privacyStatus: private` no upload
- Mínimo ~15 min no futuro (buffer recomendado: 30 min)
- Timezone: sempre UTC na API; UI converte America/Sao_Paulo

Thumbnail: `thumbnails.set` após upload (já implementado).

---

## “Agenda” sem cron nosso

```text
1. Cortes completed + routing definido
2. UI "Gerar proposta de horários" (regras simples: 3–4 slots/dia/canal)
3. Usuário confirma tabela cut → publishAt
4. Worker faz upload IMEDIATO com publishAt em cada vídeo
5. YouTube publica sozinho — zero job nosso à meia-noite
```

Tabela opcional `publish_plans` (auditoria):

```sql
CREATE TABLE publish_plans (
    id UUID PRIMARY KEY,
    cut_id UUID REFERENCES cuts (id),
    editorial_channel_id UUID,
    connected_account_id UUID,
    publish_at TIMESTAMPTZ NOT NULL,
    youtube_video_id TEXT,
    status TEXT  -- scheduled | published | failed
);
```

Retry: se upload falha, re-enfileira; se já no YouTube com `publishAt`, só atualizar metadata.

---

## Job payload

```json
{
  "type": "publish.youtube",
  "payload": {
    "run_id": "...",
    "cut_id": "...",
    "account_id": "...",
    "privacy": "private",
    "publish_at": "2026-06-26T18:00:00Z"
  }
}
```

`account_id` resolvido de `cut.target_editorial_channel.publish_account_id`.

---

## Shorts no YouTube

- Vídeo 9:16 vertical; opcional `#Shorts` na descrição
- Mesmo endpoint `videos.insert`
- `publishAt` idêntico

TikTok / Instagram: documentar depois; mesma tabela `connected_accounts` com `platform` diferente.

---

## Implementação atual

| Item | Status |
|------|--------|
| `publish.youtube` job | ✅ |
| Botão UI publicar | ✅ private imediato |
| OAuth multi-conta | ❌ |
| `publishAt` | ❌ |
| Conta por editorial | ❌ |
| Env `YOUTUBE_REFRESH_TOKEN` | ⚠️ legado — remover após OAuth |

Ref: `worker/cuts_worker/publish.py`

**Dev local:** `worker/scripts/post/youtube/oauth_local/` — OAuth + upload de teste sem deploy.
