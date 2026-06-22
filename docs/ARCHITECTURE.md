# Arquitetura — Máquina de Cortes

Documento de referência baseado no padrão [Lingo / Minecraft](../../minecraft/ARCHITECTURE.md): **Go API + PostgreSQL + Redis + Python workers**.

---

## Índice

1. [Visão do produto](#1-visão-do-produto)
2. [Runtimes](#2-runtimes)
3. [Camadas Go](#3-camadas-go)
4. [Workers Python](#4-workers-python)
5. [Layout de pastas](#5-layout-de-pastas)
6. [Job types (Redis)](#6-job-types-redis)
7. [HTTP e contratos](#7-http-e-contratos)
8. [Storage](#8-storage)
9. [O que não fazer](#9-o-que-não-fazer)

---

## 1. Visão do produto

**MVP:** colar **URL do YouTube** → escolher **template de thumbnail** → informar **o que procurar no vídeo** (`cutBrief`) → receber **Shorts**, **cortes longos** e/ou **só análise** (JSON), com título, descrição e thumbnail por corte.

Funciona para **canais de terceiros** (curadoria, highlights, react) e, em fase posterior, para vídeos locais do canal Woragis.

---

## 2. Runtimes

```text
Frontend / CLI
       │
       ▼
  Go API (server/)          ← REST /v1, runs, templates, status
       │
       ├─ PostgreSQL        ← fonte da verdade
       └─ Redis             ← fila de jobs
              │
              ▼
       Python workers/      ← yt-dlp, Whisper, Gemini, FFmpeg, thumbs
```

**Princípio:** Go é o **dono do estado**. Após `POST /v1/runs`, o run existe no DB com status rastreável. Workers processam jobs e atualizam via API interna ou escrita de artefatos + callback.

| Camada | Linguagem | Papel |
|--------|-----------|-------|
| API, domínio, filas | **Go** | handler → service → repository |
| Download, transcrição, IA, render | **Python** | workers especializados |
| UI (opcional MVP) | **Next.js** | upload URL, templates, revisar cortes |

FFmpeg/Whisper/Gemini são **sempre** jobs assíncronos — nunca bloqueiam a API por minutos.

---

## 3. Camadas Go

```text
handler  →  service  →  repository
```

| Camada | Responsabilidade | Proibido |
|--------|------------------|----------|
| **Handler** | Parse HTTP, auth, JSON | GORM, regras de negócio, FFmpeg |
| **Service** | Validações, transações, enqueue Redis | `http.Request` |
| **Repository** | Queries Postgres | Redis, HTTP |

### Módulos de domínio

| Módulo | Responsabilidade |
|--------|------------------|
| `source` | URL YouTube, metadados, path do download |
| `run` | Pipeline run (1 URL → N outputs) |
| `cut` | Cada corte (short / long): timestamps, metadata, status |
| `template` | Biblioteca de estilos de thumbnail |
| `job` | Enqueue Redis, dedupe, DLQ |

---

## 4. Workers Python

Workers ficam em **pastas separadas** sob `backend/`, cada um com consumer + handlers (padrão Lingo `lingo_worker/`).

| Worker | Jobs | Ferramentas |
|--------|------|-------------|
| `worker-ingest` | `ingest.youtube.download` | yt-dlp |
| `worker-transcribe` | `transcribe.run` | legendas YT ou Whisper |
| `worker-analyze` | `analyze.gemini` | Gemini API + cutBrief |
| `worker-metadata` | `metadata.generate` | Gemini (título, desc, tags) |
| `worker-thumbnail` | `thumbnail.generate` | template + gpt-image / composição |
| `worker-render` | `render.short`, `render.long`, `outro.append` | FFmpeg |

**Fase 1:** um único `worker/` monolítico com dispatch por `job.type`. Separar em pastas quando escalar.

---

## 5. Layout de pastas

```text
maquina-de-cortes/
├── docs/                        # documentação (este diretório)
├── README.md
├── backend/                     # submodule Go + workers
│   ├── docs/
│   ├── migrations/
│   ├── server/                  # Go API
│   │   ├── cmd/server/main.go
│   │   └── internal/
│   │       ├── httpserver/
│   │       ├── source/
│   │       ├── run/
│   │       ├── cut/
│   │       ├── template/
│   │       └── job/
│   ├── worker-ingest/
│   ├── worker-transcribe/
│   ├── worker-analyze/
│   ├── worker-metadata/
│   ├── worker-thumbnail/
│   ├── worker-render/
│   └── docker-compose.yml
└── frontend/                    # submodule (fase posterior)
```

---

## 6. Job types (Redis)

Envelope (padrão Lingo):

```json
{
  "schema_version": 1,
  "type": "analyze.gemini",
  "payload": { "runId": "...", "cutBrief": "..." }
}
```

| Job type | Worker | Descrição |
|----------|--------|-----------|
| `ingest.youtube.download` | ingest | Baixa vídeo/áudio da URL |
| `transcribe.run` | transcribe | Gera transcript.json |
| `analyze.gemini` | analyze | cutBrief → cuts.json draft |
| `metadata.generate` | metadata | título/desc/tags por cut |
| `thumbnail.generate` | thumbnail | PNG por cut + template |
| `render.short` | render | 9:16 + legenda opcional |
| `render.long` | render | 16:9 extract |
| `outro.append` | render | outro 12s (fase posterior) |

---

## 7. HTTP e contratos

| Item | Convenção |
|------|-----------|
| Prefixo | `/v1` |
| IDs | UUID |
| JSON | camelCase |
| Erros | `{ "code": "...", "message": "..." }` |
| Health | `GET /health`, `GET /ready` |

Ver [INPUT-OUTPUT.md](./INPUT-OUTPUT.md) para schemas completos.

---

## 8. Storage

```text
/data/runs/{runId}/
├── source/           # vídeo baixado
├── transcript.json
├── cuts.json         # draft → approved
├── manifest.json
├── long/{cutId}/
└── shorts/{cutId}/
```

Templates persistidos no DB + filesystem/S3:

```text
/data/templates/{templateId}/
├── pattern.png
├── character.png   # opcional
└── config.json
```

---

## 9. O que não fazer

| Evitar | Motivo |
|--------|--------|
| FFmpeg no handler Go | Bloqueia API por minutos |
| Lógica de corte no handler | Dificulta testes |
| Dois donos de migração | Só Go aplica SQL |
| Microserviço por worker | Overhead no MVP |
| Render antes de approve (default) | Shorts ruins publicados automaticamente |

---

## Referências

- [minecraft/ARCHITECTURE.md](../../minecraft/ARCHITECTURE.md)
- [Lingo worker pipeline](../../Lokra/lingo/backend/worker/lingo_worker/pipeline.py)
- [PIPELINES.md](./PIPELINES.md)
- [MVP-PHASES.md](./MVP-PHASES.md)
