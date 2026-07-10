# Cuts

Pipeline para transformar **vídeos do YouTube** (próprios ou de terceiros) em **Shorts**, **cortes longos** e **metadados** — com templates de thumbnail e `cutBrief` para guiar a IA.

Projeto do ecossistema **Woragis / LitCode**, evoluindo do trabalho em [`canal/`](../canal/) (outro, thumbnails LeetCode).

---

## MVP

**Input:** URL do YouTube + template de thumbnail + o que procurar no vídeo (`cutBrief`).

**Output:** Shorts 9:16, cortes 5–15 min, títulos, descrições, thumbnails — ou só `cuts.json` para validação barata.

### Pipelines no MVP

| # | Pipeline | Descrição |
|---|----------|-----------|
| 1 | URL → Shorts | Clips 15–60s virais |
| 2 | URL → Cortes longos | Blocos 5–15 min |
| 3 | URL → Shorts + Longos | Repurpose completo |
| 4 | URL → Só análise | `cuts.json` sem render |
| 5 | URL + timestamps manuais | Pula IA; render direto |

Pipelines 6–8 (arquivo local, metadados-only, outro) ficam para fases posteriores.

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Go API + Redis + Python workers |
| [docs/PIPELINES.md](./docs/PIPELINES.md) | Catálogo completo de pipelines |
| [docs/MVP-PHASES.md](./docs/MVP-PHASES.md) | Fases F0–F11 com commits |
| [docs/INPUT-OUTPUT.md](./docs/INPUT-OUTPUT.md) | Contratos API, cuts.json, manifest |
| [docs/TEMPLATES.md](./docs/TEMPLATES.md) | Biblioteca de thumbnails |
| [docs/SUBTITLE-TEMPLATES.md](./docs/SUBTITLE-TEMPLATES.md) | Biblioteca de legendas (burn-in shorts) |
| [docs/CUT-BRIEF.md](./docs/CUT-BRIEF.md) | Presets e exemplos para Gemini |

---

## Arquitetura (resumo)

```text
Frontend / CLI
       │
       ▼
  Go API (backend/server/)     ← runs, templates, status
       │
       ├─ PostgreSQL
       └─ Redis
              │
              ▼
       Python workers/          ← yt-dlp, Whisper, Gemini, FFmpeg
```

- **Go** — estado, CRUD, filas
- **Python** — download, transcrição, análise, render, thumbnails
- **FFmpeg** — encode (sempre assíncrono; gargalo de performance)

Ver [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) para detalhes.

---

## Repositório

```text
maquina-de-cortes/
├── docs/           # documentação
├── backend/        # submodule — Go API + workers
└── frontend/       # submodule — UI (fase posterior)
```

---

## O que já existe no canal Woragis

| Path | Descrição |
|------|-----------|
| [`canal/end-screen/`](../canal/end-screen/) | Outro 12s, música, fades (FFmpeg) |
| [`canal/generate-thumbnails.py`](../canal/generate-thumbnails.py) | Thumbnails LeetCode DSA Quest |
| [`canal/character/clean.png`](../canal/character/clean.png) | Personagem aprovado |

Lições técnicas preservadas: **yuv420p**, evitar dessincronia A/V no concat, música do outro a partir de 52s.

---

## Próximo passo

**F1 — Scaffold backend:** Go server, docker-compose (Postgres + Redis), `GET /health`.

Ver [docs/MVP-PHASES.md](./docs/MVP-PHASES.md) para o plano completo.
