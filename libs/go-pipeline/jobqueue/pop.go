package jobqueue

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/config"
	"github.com/woragis/cuts-go-pipeline/queue"
)

type PoppedJob struct {
	QueueKey      string
	ProcessingKey string
	Raw           []byte
	Envelope      queue.Envelope
}

func Pop(ctx context.Context, rdb *redis.Client, queueKeys []string, timeoutS int) (*PoppedJob, error) {
	deadline := time.Now().Add(time.Duration(max(1, timeoutS)) * time.Second)
	for time.Now().Before(deadline) {
		for _, qk := range queueKeys {
			proc := queue.ProcessingKey(qk)
			remaining := time.Until(deadline)
			if remaining <= 0 {
				break
			}
			wait := min(remaining, time.Duration(timeoutS)*time.Second)
			raw, err := rdb.BRPopLPush(ctx, qk, proc, wait).Result()
			if err == redis.Nil {
				continue
			}
			if err != nil {
				return nil, err
			}
			env, err := queue.ParseEnvelope([]byte(raw))
			if err != nil {
				_ = rdb.LRem(ctx, proc, 1, raw).Err()
				continue
			}
			return &PoppedJob{
				QueueKey: qk, ProcessingKey: proc, Raw: []byte(raw), Envelope: *env,
			}, nil
		}
	}
	return nil, nil
}

func Ack(ctx context.Context, rdb *redis.Client, processingKey string, raw []byte) error {
	return rdb.LRem(ctx, processingKey, 1, raw).Err()
}

func RequeueWrongStage(ctx context.Context, rdb *redis.Client, processingKey, target string, raw []byte) error {
	pipe := rdb.Pipeline()
	pipe.LRem(ctx, processingKey, 1, raw)
	pipe.LPush(ctx, target, raw)
	_, err := pipe.Exec(ctx)
	return err
}

func FailJob(
	ctx context.Context,
	conn pgx.Tx,
	rdb *redis.Client,
	cfg config.Config,
	jobID string,
	errMsg string,
	env queue.Envelope,
	queueKey, processingKey string,
	raw []byte,
) (bool, error) {
	if jobID == "" {
		return false, nil
	}
	var attempt, maxAttempts int
	var payloadJSON []byte
	var storedQueue, jobType string
	err := conn.QueryRow(ctx, `
		SELECT attempt, max_attempts, payload, queue_key, job_type FROM jobs_log WHERE job_id = $1
	`, jobID).Scan(&attempt, &maxAttempts, &payloadJSON, &storedQueue, &jobType)
	if err != nil {
		return false, err
	}
	var payload map[string]any
	_ = json.Unmarshal(payloadJSON, &payload)
	if payload == nil {
		payload = map[string]any{}
	}

	requeue := attempt < maxAttempts
	newStatus := "dead"
	if requeue {
		newStatus = "enqueued"
	}
	_, err = conn.Exec(ctx, fmt.Sprintf(`
		UPDATE jobs_log SET status = $1, error_message = $2, lease_expires_at = NULL,
			claimed_at = NULL, claimed_by = NULL, updated_at = now(),
			total_duration_ms = COALESCE(total_duration_ms, 0) + CASE
				WHEN claimed_at IS NOT NULL THEN GREATEST(0, (EXTRACT(EPOCH FROM (now() - claimed_at)) * 1000)::bigint)
				ELSE 0 END
		WHERE job_id = $3
	`), newStatus, truncate(errMsg, 4000), jobID)
	if err != nil {
		return false, err
	}
	if !requeue {
		if processingKey != "" && raw != nil {
			_ = rdb.LRem(ctx, processingKey, 1, raw).Err()
		}
		return false, nil
	}
	target := queueKey
	if target == "" {
		target = storedQueue
	}
	if target == "" {
		target = queue.QueueForJobType(cfg, jobType)
	}
	requeueRaw, _ := queue.MarshalEnvelope(env)
	pipe := rdb.Pipeline()
	if processingKey != "" && raw != nil {
		pipe.LRem(ctx, processingKey, 1, raw)
	}
	pipe.LPush(ctx, target, requeueRaw)
	_, err = pipe.Exec(ctx)
	return true, err
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b time.Duration) time.Duration {
	if a < b {
		return a
	}
	return b
}
