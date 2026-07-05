package consumer

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/config"
	"github.com/woragis/cuts-go-pipeline/jobqueue"
	"github.com/woragis/cuts-go-pipeline/metrics"
	"github.com/woragis/cuts-go-pipeline/queue"
	"github.com/woragis/cuts-go-pipeline/runtime"
	"github.com/woragis/cuts-go-pipeline/specialized"
)

type Dispatcher interface {
	Run(ctx context.Context, job *jobqueue.PoppedJob) error
}

type Service struct {
	Cfg      config.Config
	Dispatch Dispatcher
	Metrics  *metrics.Service
	Pop      func(ctx context.Context) (*jobqueue.PoppedJob, error)
	Limiter  *runtime.Limiter
	RDB      *redis.Client
}

func (s Service) Run(ctx context.Context) error {
	var wg sync.WaitGroup

	for {
		select {
		case <-ctx.Done():
			wg.Wait()
			return nil
		default:
		}

		if s.Limiter != nil {
			s.Limiter.Refresh(ctx)
		}

		_ = s.Metrics.Push(ctx)
		job, err := s.Pop(ctx)
		if err != nil {
			if specialized.IsConnError(err) {
				return err
			}
			slog.Error("pop failed", "err", err)
			time.Sleep(time.Second)
			continue
		}
		if job == nil {
			continue
		}

		wg.Add(1)
		go func(j *jobqueue.PoppedJob) {
			defer wg.Done()
			s.processOne(ctx, j)
		}(job)
	}
}

func (s Service) processOne(ctx context.Context, job *jobqueue.PoppedJob) {
	env := job.Envelope
	jobType := env.Type
	runID := queue.StrPayload(env.Payload, "run_id")

	if !queue.JobAllowedForStage(jobType, s.Cfg.WorkerStage) {
		target := queue.QueueForJobType(s.Cfg, jobType)
		slog.Warn("wrong stage — requeue", "type", jobType, "target", target)
		_ = jobqueue.RequeueWrongStage(ctx, s.RDB, job.ProcessingKey, target, job.Raw)
		return
	}

	if s.Limiter != nil {
		releaseGlobal, err := s.Limiter.AcquireGlobal(ctx, jobType)
		if err != nil {
			slog.Warn("global limit wait cancelled", "type", jobType, "err", err)
			return
		}
		defer releaseGlobal()
		if err := s.Limiter.AcquireLocal(ctx, jobType); err != nil {
			slog.Warn("local limit wait cancelled", "type", jobType, "err", err)
			return
		}
		defer s.Limiter.ReleaseLocal()
	}

	s.Metrics.JobStarted(jobType, runID)
	started := time.Now()
	err := s.Dispatch.Run(ctx, job)
	ok := err == nil
	if ok {
		if ackErr := jobqueue.Ack(ctx, s.RDB, job.ProcessingKey, job.Raw); ackErr != nil {
			slog.Error("ack failed", "type", jobType, "err", ackErr)
		}
	} else if specialized.IsConnError(err) {
		slog.Warn("postgres/redis error during job", "type", jobType, "run_id", runID)
	}
	s.Metrics.JobFinished(ok, time.Since(started).Seconds())
	_ = s.Metrics.Push(ctx)
}
