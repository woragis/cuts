# Templates de thumbnail

Biblioteca de estilos visuais reutilizáveis. Cada **run** escolhe um template; cada **cut** herda o estilo com título/conteúdo específico.

---

## Modelo de dados

### Template (DB + filesystem)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "LeetCode DSA Quest",
  "slug": "leetcode-dsa-quest",
  "description": "Estilo escuro, laranja, personagem hooded",
  "createdAt": "2026-06-19T12:00:00Z",
  "assets": {
    "patternPath": "pattern.png",
    "characterPath": "character.png",
    "configPath": "config.json"
  }
}
```

### config.json (por template)

```json
{
  "outputSize": [1280, 720],
  "shortOutputSize": [1080, 1920],
  "colorPalette": {
    "primary": "#FF8C00",
    "secondary": "#FFD700",
    "background": "#0a0a0a"
  },
  "titleStyle": {
    "line1Color": "white",
    "line2Color": "yellow"
  },
  "imageModel": "gpt-image-2",
  "promptSnippet": "Dark hacker aesthetic, LeetCode style, orange accents..."
}
```

---

## API

```text
GET    /v1/templates              # listar
POST   /v1/templates              # criar (multipart: name + pattern.png + opcionais)
GET    /v1/templates/{id}         # detalhe
PATCH  /v1/templates/{id}         # atualizar metadados
DELETE /v1/templates/{id}         # soft delete
```

### Uso no run

```json
{
  "youtubeUrl": "...",
  "thumbnailTemplateId": "550e8400-e29b-41d4-a716-446655440000"
}
```

Worker `thumbnail.generate` recebe `{ runId, cutId, templateId, title, ... }`.

---

## Geração de thumbnail por cut

```text
template.pattern.png
+ template.character.png (opcional)
+ frame do vídeo no timestamp do cut (opcional)
+ título do cut
  → worker-thumbnail
  → shorts/{cutId}/thumbnail.png   (9:16 se short)
  → long/{cutId}/thumbnail.png     (16:9 se long)
```

Reutiliza lógica de [`generate-thumbnails.py`](../../woragis/canal/generate-thumbnails.py) do canal Woragis, parametrizada por template.

---

## Templates iniciais sugeridos (seed)

| Slug | Uso |
|------|-----|
| `generic-dark` | MVP genérico, texto grande |
| `leetcode-dsa-quest` | Canal Woragis |
| `podcast-clip` | Curadoria / react |
| `minimal-bold` | Shorts virais, fundo sólido |

---

## Storage

```text
/data/templates/{templateId}/
├── pattern.png
├── character.png
└── config.json
```

Metadados (name, slug) no Postgres; arquivos no disco ou S3.
