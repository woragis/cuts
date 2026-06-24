# Fase 1 — Contexto estruturado no worker + API + UI

## Entregas

1. Migration `007_error_context.sql` — colunas `error_context JSONB` em `runs` e `jobs_log`.
2. `pipeline_errors.py` — `PipelineError`, mapa job→handler/step, `normalize_job_error()`.
3. `handlers.dispatch()` — grava `error_message` + `error_context` no run e job.
4. **`subStep`** — sub-operacao dentro do handler (ex. `gemini.http_post`, `cuts.validate`).
4. Go — expõe `errorContext` em `GET /v1/runs/{id}` e `GET /v1/runs/{id}/jobs`.
5. Frontend — banner com step/handler/job; painel de jobs com contexto.
6. Testes unitários `test_pipeline_errors.py`, `test_dispatch_logging.py` atualizado.

## Fora de escopo (F2+)

- Erros tipados em cada módulo (`IngestError` → code específico).
- INSERT de `jobs_log` quando worker enfileira metadata/thumbnail/render.
- Retry baseado em `error_context.step`.
