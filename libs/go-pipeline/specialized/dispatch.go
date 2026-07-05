package specialized

import (
	"context"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/blob"
	"github.com/woragis/cuts-go-pipeline/config"
	"github.com/woragis/cuts-go-pipeline/jobqueue"
	"github.com/woragis/cuts-go-pipeline/pydelegate"
	"github.com/woragis/cuts-go-pipeline/queue"
)

// Service runs jobs for a single worker stage (analyze, publish, thumbnail).
// Handlers execute in Python via pydelegate until ported to native Go HTTP.
type Service struct {
	Cfg    config.Config
	Pool   *pgxpool.Pool
	RDB    *redis.Client
	Store  *blob.Store
	Python pydelegate.Runner
}

func (s Service) Run(ctx context.Context, job *jobqueue.PoppedJob) error {
	jobType := job.Envelope.Type
	if !queue.JobAllowedForStage(jobType, s.Cfg.WorkerStage) {
		target := queue.QueueForJobType(s.Cfg, jobType)
		if job.QueueKey != target {
			return jobqueue.RequeueWrongStage(ctx, s.RDB, job.ProcessingKey, target, job.Raw)
		}
	}
	if !s.Python.Available() {
		return pydelegate.ErrNotConfigured(jobType)
	}
	return s.runPythonDelegate(ctx, job)
}

func (s Service) runPythonDelegate(ctx context.Context, job *jobqueue.PoppedJob) error {
	env := job.Envelope
	runID := queue.StrPayload(env.Payload, "run_id")
	if runID != "" && s.Store.UsesRemote() {
		if err := s.Store.MaterializePrefix(ctx, blob.RunPrefix(runID)); err != nil {
			return err
		}
	}
	if err := s.Python.Run(ctx, env, job.QueueKey, job.ProcessingKey, job.Raw); err != nil {
		return err
	}
	if runID != "" && s.Store.UsesRemote() {
		return s.Store.SyncPrefixUp(ctx, blob.RunPrefix(runID))
	}
	return nil
}

func IsConnError(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	for _, part := range []string{"connection", "conn refused", "eof", "broken pipe", "closed network", "unable to connect"} {
		if strings.Contains(msg, part) {
			return true
		}
	}
	return false
}
