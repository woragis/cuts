# Deploy em escala — Railway e alternativas

Como hospedar a arquitetura de [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md) no **Railway** hoje, e quando migrar para **AWS/Kubernetes**.

---

## Railway consegue lidar com essa arquitetura?

**Sim, em parte** — com ressalvas importantes.

Railway **não é Kubernetes**. Não existem “pods” nativos; existem **services** (containers) com **réplicas** configuráveis. Para o nosso caso, o modelo mental correto é:

```text
Railway Project "maquina-de-cortes"
├── service: api-go              (réplicas 1–3)
├── service: scheduler-go        (réplicas 1 — singleton)
├── service: worker-render       (réplicas 4–16 manual)
├── service: worker-publish      (réplicas 2–8 manual)
├── service: worker-ingest       (réplicas 2)
├── plugin: postgres
├── plugin: redis
├── volume: /data (compartilhado ou por worker — ver limitações)
└── services externos:
    ├── cuts-tiktok-dev-server
    └── cuts-meta-dev-server
```

---

## O que Railway oferece

| Recurso | Suporte | Notas |
|---------|---------|-------|
| Múltiplos serviços no mesmo project | ✅ | API, scheduler, workers separados |
| **Réplicas horizontais** | ✅ manual | Settings → Regions → replica count |
| **Vertical autoscaling** | ✅ automático | Escala até limite do plano (vCPU/RAM) |
| **Autoscaling horizontal automático** (CPU/fila) | ❌ nativo | Ajuste manual ou script/API |
| Postgres / Redis managed | ✅ | Plugins |
| Volumes persistentes | ✅ | Limitados; custo por GB |
| Deploy via GitHub | ✅ | Já usado nos dev-servers |
| Multi-region replicas | ✅ | Tráfego HTTP roteado |

Fonte: [Railway Scaling docs](https://docs.railway.com/deployments/scaling).

### Réplicas ≠ pods Kubernetes

| Kubernetes | Railway |
|------------|---------|
| Pod | Container instance (réplica) |
| Deployment com HPA | Service com N réplicas **fixas** (você altera) |
| KEDA (scale por fila Redis) | Não nativo — custom script |
| Node pool GPU | Não |

Funcionalmente, **3 réplicas de `worker-render` no Railway ≈ 3 pods** consumindo a mesma fila Redis — padrão correto para nosso worker.

---

## Limitações críticas para Máquina de Cortes

### 1. Timeout HTTP de 5 minutos

Requests HTTP morrem após ~5 min.

**Impacto:** nenhum se workers consomem **Redis** (background), não HTTP long-polling.

**Não fazer:** endpoint `POST /upload` síncrono com FFmpeg.

### 2. Sem autoscaling horizontal nativo

Railway **não** cria réplicas sozinho quando CPU > 60% ou fila Redis cresce.

**Opções:**

| Opção | Esforço | Custo |
|-------|---------|-------|
| Ajuste manual de réplicas | Baixo | Previsível |
| Script cron + [Railway GraphQL API](https://docs.railway.com) | Médio | Baixo |
| [Judoscale](https://judoscale.com/railway) (terceiro) | Baixo | ~$50+/mês |
| Migrar workers para AWS/K8s + KEDA | Alto | Variável |

**Recomendação fase 1:** monitorar lag da fila `cuts:jobs:render` no Grafana/metrics; aumentar réplicas manualmente nos horários de pico (tarde/noite após lives).

### 3. Storage de vídeo (GB/TB)

Cada render gera arquivos grandes. Railway volumes:

- Funcionam para **prototipagem** e nicho único
- Ficam **caros** com centenas de GB
- Compartilhar volume entre N réplicas de render exige cuidado (NFS-like não existe — preferir **S3-compatible** externo)

**Recomendação escala:**

```text
Fase 1: Railway volume /data
Fase 2: Cloudflare R2 ou AWS S3 (mesmo código, path s3://)
```

Workers baixam source uma vez, upload publica de URL ou arquivo local.

### 4. CPU para FFmpeg

Plano Pro: até **24 vCPU / 24 GB por réplica**. Com 4 réplicas render = até 96 vCPU teóricos (custo linear).

Render é **CPU-bound** — Railway funciona, mas **custo sobe rápido** com 8–16 réplicas 24/7.

---

## Mapeamento serviço → Railway

| Componente | Dockerfile | Réplicas | Notas |
|------------|------------|----------|-------|
| `server` | `backend/Dockerfile` | 1–2 | API stateless |
| `scheduler` | novo `Dockerfile.scheduler` | **1** | singleton |
| `worker-render` | `backend/Dockerfile.worker` | **4–16** | `WORKER_STAGE=render` |
| `worker-publish` | mesmo | **2–8** | `WORKER_STAGE=publish` |
| `worker-ingest` | mesmo | 2 | I/O |
| `postgres` | plugin | 1 | |
| `redis` | plugin | 1 | filas |

Mesma imagem worker, **env diferente** por service Railway — padrão comum, não precisa 5 Dockerfiles.

---

## Estratégia de escala por fase

### Fase A — Só política (3–4 lives/dia)

**Railway é suficiente.**

- 1 API + 1 scheduler + 2 render + 1 publish
- Postgres + Redis plugins
- Volume 50–100 GB ou R2
- OAuth dev-servers já no Railway

Custo estimado: dezenas a low hundreds USD/mês (depende de réplicas e volume).

### Fase B — 3 nichos, centenas de renders/dia

**Railway possível, monitorar custo.**

- 6–12 réplicas render (manual nos horários de batch)
- Script simples: se `LLEN cuts:jobs:render` > 50 → alerta Discord + aumentar réplicas via API
- S3 para storage

### Fase C — Operação contínua multi-nicho pleno

**Considerar híbrido ou AWS:**

| Componente | Onde |
|------------|------|
| API + scheduler + frontend | Railway (simples) |
| worker-render | **AWS Batch / ECS / K8s + KEDA** |
| worker-publish | Railway ou AWS (leve) |
| Storage | S3 |
| Redis | Upstash / ElastiCache |

Motivo: **KEDA** escala workers por tamanho da fila Redis automaticamente — exatamente o que precisamos para render.

---

## AWS / Kubernetes — quando faz sentido

Não é “só AWS tem escala”. Railway escala **manualmente**. AWS/K8s escala **automaticamente** com mais configuração.

| Recurso AWS/K8s | Benefício |
|-----------------|-----------|
| **KEDA** + Redis scaler | Réplicas render ∝ `LLEN queue` |
| **S3** | Storage barato para vídeo |
| **Spot instances** | Render FFmpeg 70% mais barato |
| **GPU** (fase futura) | Whisper local, etc. |

**Sinais para migrar render:**

- Custo Railway render > ~$300–500/mês
- Fila render com lag > 2h recorrente
- >10 réplicas render fixas desperdiçando CPU de madrugada

---

## Autoscaling “caseiro” no Railway (intermediário)

Script externo (cron no GitHub Actions ou mini service):

```text
1. LLEN cuts:jobs:render (Redis)
2. Se > threshold_high → Railway API: worker-render replicas = N+1
3. Se < threshold_low por 30min → replicas = N-1 (mínimo 2)
```

Railway expõe API GraphQL para alterar replica count — mesma ideia de HPA simplificado.

---

## Checklist deploy Railway (escala)

- [ ] Filas Redis separadas (`cuts:jobs:render`, etc.)
- [ ] `WORKER_STAGE` env por service
- [ ] Scheduler como service separado (1 réplica)
- [ ] Volume ou S3 para `/data`
- [ ] Healthcheck workers: heartbeat Redis, não HTTP longo
- [ ] Métricas: lag fila, tempo médio render
- [ ] Alertas: publish_plans atrasados > 15 min
- [ ] OAuth servers separados (já feito)

---

## Resposta direta

| Pergunta | Resposta |
|----------|----------|
| Railway aguenta a arquitetura? | **Sim** — múltiplos services + réplicas + Redis + Postgres |
| Tem pods? | **Não** — tem **réplicas** (equivalente prático) |
| Escala automática sobe/desce? | **Vertical sim; horizontal não** (manual ou script) |
| Só AWS faz isso? | **Não** — AWS/K8s faz **automático** com mais setup; Railway faz **manual** mais simples |
| Começar onde? | Railway com 2–4 réplicas render; migrar render pesado quando custo/lag doer |

---

## Referências

- [Railway — Scaling](https://docs.railway.com/deployments/scaling)
- [Railway — Optimize Performance](https://docs.railway.com/deployments/optimize-performance)
- [ARCHITECTURE-SCALE.md](./ARCHITECTURE-SCALE.md)
- [KEDA Redis scaler](https://keda.sh/docs/latest/scalers/redis-lists/) (futuro AWS/K8s)
