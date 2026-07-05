package metrics

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/config"
)

const metricsPrefix = "cuts:metrics:worker:"

type Service struct {
	Cfg  config.Config
	RDB  *redis.Client
	inst string
	host string

	jobsOK            int
	jobsFail          int
	lastJobDurationS  float64
	status            string
	currentJobType    string
	currentRunID      string
}

func New(cfg config.Config, rdb *redis.Client) *Service {
	inst := cfg.InstanceID
	if inst == "" {
		hostname, _ := os.Hostname()
		inst = fmt.Sprintf("%s-%d", hostname, os.Getpid())
	}
	host, _ := os.Hostname()
	return &Service{Cfg: cfg, RDB: rdb, inst: inst, host: host, status: "idle"}
}

func (s *Service) JobStarted(jobType, runID string) {
	s.status = "busy"
	s.currentJobType = jobType
	s.currentRunID = runID
}

func (s *Service) JobFinished(ok bool, durationS float64) {
	if ok {
		s.jobsOK++
	} else {
		s.jobsFail++
	}
	s.lastJobDurationS = durationS
	s.status = "idle"
	s.currentJobType = ""
	s.currentRunID = ""
}

func (s *Service) Push(ctx context.Context) error {
	var mem runtime.MemStats
	runtime.ReadMemStats(&mem)
	payload := map[string]any{
		"instance":           s.inst,
		"hostname":           s.host,
		"stage":              s.Cfg.WorkerStage,
		"status":             s.status,
		"currentJobType":     s.currentJobType,
		"currentRunId":       s.currentRunID,
		"jobsOk":             s.jobsOK,
		"jobsFail":           s.jobsFail,
		"lastJobDurationSec": s.lastJobDurationS,
		"memoryMb":           float64(mem.Alloc) / (1024 * 1024),
		"updatedAt":          time.Now().UTC().Format(time.RFC3339),
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	key := metricsPrefix + s.inst
	pipe := s.RDB.Pipeline()
	pipe.Set(ctx, key, raw, time.Duration(s.Cfg.MetricsTTLSeconds)*time.Second)
	pipe.SAdd(ctx, "cuts:metrics:workers", s.inst)
	pipe.Expire(ctx, "cuts:metrics:workers", time.Duration(s.Cfg.MetricsTTLSeconds)*time.Second)
	_, err = pipe.Exec(ctx)
	return err
}
