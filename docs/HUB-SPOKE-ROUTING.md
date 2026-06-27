# Hub/spoke routing

Distribui cortes aprovados entre **flagship** (hub) e **satélites** (spoke), sem duplicar vídeo no YouTube.

---

## Regra de negócio

Entrada: batch de cortes de uma ou mais lives (ex.: 15 cortes de 3 lives).

```text
1. Agrupar por source_profile (live/pessoa)
2. Em cada grupo + global: ordenar por score (e bônus polêmica/contexto)
3. Top N global → editorial flagship (brasil-em-debate)
4. Restante → editorial satélite da source_profile
5. Nenhum cut_id publicado em dois editoriais
```

Parâmetros default (configurável no flagship ou global):

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `hubTopN` | 5 | Longos que vão ao flagship por batch |
| `hubTopShortsN` | 2 | Shorts top ao flagship (opcional) |
| `minScoreForHub` | 0.75 | Piso para entrar no hub mesmo no top N |

---

## Campos no cut (proposto)

```json
{
  "id": "merged-short-01",
  "score": 0.91,
  "sourceProfileId": "mbl-arthur-live",
  "targetEditorialChannelId": "uuid-brasil-em-debate",
  "routingReason": "hub_top_score",
  "routingRank": 1
}
```

```json
{
  "id": "merged-short-04",
  "score": 0.72,
  "targetEditorialChannelId": "uuid-cortes-arthur-mbl",
  "routingReason": "satellite_overflow"
}
```

`routingReason` enum: `hub_top_score` | `satellite_overflow` | `manual_override`

---

## Fluxo no pipeline

```text
analyze → cuts proposed
    ↓
approve (humano ou batch)
    ↓
routing.assign  (novo step lógico na API ou no approve handler)
    ↓
metadata / treatment / thumbnail  (usa targetEditorialChannelId)
    ↓
publish  (usa publish_account do editorial)
```

Treatment deve carregar **música, outro, templates** do editorial de destino, não do run pai.

---

## Cadência esperada

| Canal | Longos/dia | Shorts/dia |
|-------|------------|------------|
| Flagship | 3–5 | 2–3 |
| Satélite | 3–4 | 5–8 |

Agendamento via `publishAt` no YouTube (ver [PUBLISH-YOUTUBE.md](./PUBLISH-YOUTUBE.md)) — slots calculados na confirmação da agenda, não cron interno.

---

## UI

1. Após approve: painel **“Roteamento”** com tabela cut → editorial (editável)
2. Bulk: “mover para satélite X” / “promover ao hub”
3. Filtro por `sourceProfile` na revisão

---

## Implementação atual

- ❌ Routing não implementado
- ❌ `targetEditorialChannelId` não existe no schema
- ✅ Discussão e regras documentadas aqui
