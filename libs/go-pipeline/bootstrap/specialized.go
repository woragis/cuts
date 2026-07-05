package bootstrap

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/blob"
	"github.com/woragis/cuts-go-pipeline/config"
	"github.com/woragis/cuts-go-pipeline/consumer"
	"github.com/woragis/cuts-go-pipeline/jobqueue"
	"github.com/woragis/cuts-go-pipeline/metrics"
	"github.com/woragis/cuts-go-pipeline/pydelegate"
	"github.com/woragis/cuts-go-pipeline/runtime"
	"github.com/woragis/cuts-go-pipeline/specialized"
)

// RunSpecialized starts a Go worker for analyze, publish, or thumbnail stages.
// Jobs run via Python delegate until native Go HTTP handlers are ported.
func RunSpecialized(serviceName string) {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})))

	cfg, err := config.Load()
	if err != nil {
		slog.Error("config", "err", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		slog.Error("postgres connect", "err", err)
		os.Exit(1)
	}
	defer pool.Close()

	opt, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		slog.Error("redis parse url", "err", err)
		os.Exit(1)
	}
	rdb := redis.NewClient(opt)
	defer rdb.Close()

	store, err := blob.New(cfg)
	if err != nil {
		slog.Error("blob store", "err", err)
		os.Exit(1)
	}

	python := pydelegate.Runner{Cfg: cfg}
	disp := specialized.Service{
		Cfg: cfg, Pool: pool, RDB: rdb, Store: store, Python: python,
	}
	met := metrics.New(cfg, rdb)
	limiter := runtime.NewLimiter(rdb, cfg.WorkerStage, cfg.Concurrency)
	queueKeys := cfg.ConsumeQueueKeys()

	slog.Info(serviceName+" started",
		"stage", cfg.WorkerStage,
		"queues", queueKeys,
		"fallback_concurrency", cfg.Concurrency,
		"runtime_limits", "redis:"+runtime.RedisKeyLimits,
		"python_delegate", python.Available(),
	)

	svc := consumer.Service{
		Cfg: cfg, Dispatch: disp, Metrics: met, Limiter: limiter, RDB: rdb,
		Pop: func(popCtx context.Context) (*jobqueue.PoppedJob, error) {
			return jobqueue.Pop(popCtx, rdb, queueKeys, cfg.BrpopTimeoutS)
		},
	}

	for {
		if err := svc.Run(ctx); err != nil {
			if specialized.IsConnError(err) {
				slog.Warn("connection error — retrying")
				continue
			}
			slog.Error("consumer stopped", "err", err)
			os.Exit(1)
		}
		return
	}
}
