# Testes e validação — até publicar no YouTube

Plano para validar cada camada antes de OAuth em produção e upload agendado.

---

## Fases de validação

```text
T0  Local scripts (já feito)
T1  Worker E2E um corte (treatment)
T2  Hub/spoke + editorial (staging)
T3  Thumbnail sempre gpt-image-2 + frame Gemini
T4  OAuth sandbox + upload private
T5  publishAt em canal de teste
T6  Piloto Brasil em Debate + 1 satélite
```

---

## T0 — Scripts locais ✅

| Check | Como |
|-------|------|
| Reframing 9:16 | `run_reframing_test.py` + aprovação visual |
| Legendas | `run_short_finish_test.py` |
| Thumb | output `thumbnail_short.png` |

VOD referência: `eKxFuD3-pos`, cuts em `scripts/results/.../cuts_merged_claude.json`.

---

## T1 — Worker E2E (um short)

**Setup:** run com `burnSubtitles: true`, `treatmentChannel: politica-mbl`.

| # | Critério | Pass |
|---|----------|------|
| 1 | `clip_raw` → `clip_silence` → `clip_framed` → `clip_subtitled` → `video.mp4` | arquivos existem |
| 2 | Legendas: phrase chunks, posYFrac ~0.64, enterMs 120 | ASS + visual |
| 3 | Reframing: Arthur topo em news_reaction | spot-check 3 cortes |
| 4 | `thumbnail.png` 9:16 | existe |
| 5 | `manifest.json` status completed | API |

**Falha comum:** Gemini key, Whisper key, ffmpeg path.

---

## T2 — Editorial + routing (após F25–F27)

| # | Teste |
|---|-------|
| 1 | Seed flagship + 2 satélites com músicas/outros diferentes |
| 2 | Batch 15 cortes → top 5 hub, 10 satélite |
| 3 | Render satélite A ≠ satélite B (hash áudio ou duração outro) |
| 4 | Nenhum `cut_id` em dois editoriais |

---

## T3 — Thumbnail + modelos (após F29–F30)

| # | Teste | Modelo |
|---|-------|--------|
| 1 | `pattern_frame` + frame auto | gemini-2.5-pro |
| 2 | Mesmo cut, frame auto | gemini-3.5-flash (comparar) |
| 3 | `pattern_character` com upload | gpt-image-2 |
| 4 | Confirmar **sem** fallback PIL (`THUMBNAIL_BACKEND` removido) |
| 5 | Falha API → job `failed` com mensagem clara | — |

**Aceite visual:** thumb legível em mobile, rosto hero, 2 linhas título.

---

## T4 — OAuth + upload private

**Canal:** conta Google de teste ou satélite novo (0 inscritos ok).

| # | Passo |
|---|-------|
| 1 | Conectar conta via UI |
| 2 | Publicar 1 short `privacy=private` sem `publishAt` |
| 3 | Verificar `youtube_video_id` no cut / publish_plan |
| 4 | Thumb aparece no Studio |
| 5 | Desconectar / token refresh automático |

---

## T5 — publishAt (agendamento YouTube)

| # | Passo |
|---|-------|
| 1 | Propor 3 horários (UI ou JSON manual) |
| 2 | Upload 3 cortes com `publishAt` + private |
| 3 | YouTube Studio → agendados (não publicados) |
| 4 | Após 1 horário passar → vídeo público/privado conforme configurado |
| 5 | Cancelar/reagendar via API (opcional fase 2) |

**Não** rodar cron interno; validar que zero jobs nossos disparam na hora H.

---

## T6 — Piloto produção

| Canal | Volume teste | Duração |
|-------|--------------|---------|
| Satélite novo | 3 longos + 5 shorts, agendados 2 dias | 1 semana observação |
| Brasil em Debate | top 2 do batch | após satélite ok |

Métricas: CTR thumb, retenção 30s, strikes/copyright (Content ID).

---

## Checklist pré-upload (por corte)

```markdown
- [ ] video.mp4 9:16 ou 16:9 conforme tipo
- [ ] thumbnail.png gerada por gpt-image-2
- [ ] title.txt ≤ 100 chars
- [ ] description.txt ok
- [ ] target_editorial_channel definido
- [ ] publish_account conectada
- [ ] publish_at UTC válido (≥30 min futuro)
- [ ] vídeo não duplicado em outro editorial
```

---

## Ambiente

| Variável | Uso |
|----------|-----|
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | OAuth |
| `TOKEN_ENCRYPTION_KEY` | tokens no DB |
| `OPENAI_API_KEY` | gpt-image-2 + Whisper |
| `GEMINI_API_KEY` | analyze, reframing, frame |

Staging: `DATA_DIR` isolado, canal YouTube descartável.

---

## Regressão automatizada

Manter:

```bash
cd backend/worker && python -m pytest -q
```

Adicionar (futuro):

- `test_routing_hub_spoke.py`
- `test_publish_at_payload.py`
- `test_thumbnail_requires_gpt_image.py`

---

## Documentos relacionados

- [ROADMAP-POS-TREATMENT.md](./ROADMAP-POS-TREATMENT.md)
- [PUBLISH-YOUTUBE.md](./PUBLISH-YOUTUBE.md)
- [THUMBNAIL-MODES.md](./THUMBNAIL-MODES.md)
- [HUB-SPOKE-ROUTING.md](./HUB-SPOKE-ROUTING.md)
