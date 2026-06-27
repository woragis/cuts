# Checklist de render — inspeção manual

Copie este bloco para `tests/render/output/{channel}_{cut_id}/CHECKLIST-notes.md` após revisar os MP4s.

---

## Metadados

- **Cut ID:** 
- **Formato:** short / long
- **Veredito fonte:** C-Claude / C-OpenAI / A / B
- **RENDER_MODE testado:** 
- **Data:** 

---

## 1. Silêncio (`clip_silence.mp4`)

- [ ] Pausas longas removidas sem cortar frases no meio
- [ ] Ritmo natural — não ficou “apressado demais”
- [ ] uselessParts marcados como `trim` foram respeitados (se aplicável)
- Notas:

## 2. Hook / Re-hook (`clip_hooked.mp4`)

- [ ] Estrutura faz sentido para o **tópico completo** (não só choque)
- [ ] Re-hook: peak teaser → context → buildup → finale coerente
- [ ] Sem jump cuts abruptos entre segmentos do re-hook
- [ ] Short: hook opcional — corte informativo OK sem re-hook
- Notas:

## 3. Reframing / Zoom (`clip_framed.mp4`)

- [ ] Crop 9:16 centrado no falante
- [ ] Zoom suave durante explicação (se houver)
- [ ] Corte seco com zoom reset para default quando muda assunto
- [ ] Sem “pulo” de enquadramento entre blocos
- Notas:

## 4. Música (`clip_music.mp4`)

### Short
- [ ] Voz audível (LUFS alvo do canal)
- [ ] Música ducking durante fala — não compete
- [ ] Nível agradável em fone e celular

### Long
- [ ] Mesmos critérios + música não cansa em 6–10 min
- Notas:

## 5. Legendas (`clip_subs.mp4`)

- [ ] Fonte correta (Montserrat Bold / config canal)
- [ ] Quebra de linha legível, sem overflow
- [ ] Sincronia com áudio pós-remoção de silêncio
- [ ] Contraste e posição (safe area shorts)
- Notas:

## 6. Outro — **somente long** (`clip_outro.mp4`)

- [ ] Transição visual suave (fade / dissolve)
- [ ] Transição auditiva — música outro entra no momento certo
- [ ] Sem corte seco entre conteúdo e card outro
- [ ] Duração outro proporcional (~3–5s)
- Notas:

## 7. Thumbnail

- [ ] Frame representa o tópico (não só rosto genérico)
- [ ] Re-hook peak usado quando aplicável
- Notas:

## 8. Retenção geral

- [ ] Assunto ficou **completo e informativo**
- [ ] Profissionalismo: áudio + visual + ritmo
- [ ] Aprovar para produção: sim / não / revisar hook / revisar música

---

## Referência LUFS (politica-mbl)

Ver `backend/worker/scripts/treatment/channels/politica-mbl.json` → `formatDefaults.short.voiceTargetLufs` / `long`.
