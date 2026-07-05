package queue

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/redis/go-redis/v9"
	"github.com/woragis/cuts-go-pipeline/config"
)

type Enqueuer struct {
	Cfg config.Config
}

func (e Enqueuer) Enqueue(ctx context.Context, conn pgx.Tx, rdb *redis.Client, jobType string, payload map[string]any, queueKey string) (string, error) {
	target := queueKey
	if target == "" {
		target = QueueForJobType(e.Cfg, jobType)
	}
	jobID := StrPayload(payload, "job_id")
	if jobID == "" {
		jobID = uuid.NewString()
	}
	payload = copyPayload(payload)
	payload["job_id"] = jobID

	idem := MakeIdempotencyKey(jobType, payload)
	runID := StrPayload(payload, "run_id")

	inserted, finalJobID, err := insertJobLog(ctx, conn, insertJobLogInput{
		JobType: jobType, JobID: jobID, Payload: payload, RunID: runID,
		QueueKey: target, IdempotencyKey: idem, MaxAttempts: e.Cfg.JobMaxAttempts,
	})
	if err != nil {
		return "", err
	}
	if !inserted {
		return finalJobID, nil
	}

	env := BuildEnvelope(jobType, payload)
	raw, err := MarshalEnvelope(env)
	if err != nil {
		return "", err
	}
	if err := rdb.LPush(ctx, target, raw).Err(); err != nil {
		return "", err
	}
	return finalJobID, nil
}

type insertJobLogInput struct {
	JobType, JobID, RunID, QueueKey, IdempotencyKey string
	Payload                                         map[string]any
	MaxAttempts                                     int
}

func insertJobLog(ctx context.Context, conn pgx.Tx, in insertJobLogInput) (bool, string, error) {
	payloadJSON, err := json.Marshal(in.Payload)
	if err != nil {
		return false, "", err
	}
	maxAttempts := in.MaxAttempts
	if maxAttempts <= 0 {
		maxAttempts = 3
	}

	var existingJobID, status string
	var leaseExpires *string
	err = conn.QueryRow(ctx, `
		SELECT job_id, status, lease_expires_at::text FROM jobs_log WHERE idempotency_key = $1
	`, in.IdempotencyKey).Scan(&existingJobID, &status, &leaseExpires)
	if err != nil && !errors.Is(err, pgx.ErrNoRows) {
		return false, "", err
	}
	if err == nil {
		if shouldSkipEnqueue(status, leaseExpires) {
			return false, existingJobID, nil
		}
		_, err = conn.Exec(ctx, `
			UPDATE jobs_log SET status = 'enqueued', job_id = $1, payload = $2::jsonb, queue_key = $3,
				error_message = NULL, error_context = NULL, claimed_at = NULL, claimed_by = NULL,
				lease_expires_at = NULL, updated_at = now() WHERE idempotency_key = $4
		`, in.JobID, payloadJSON, in.QueueKey, in.IdempotencyKey)
		return true, in.JobID, err
	}

	var runID any
	if in.RunID != "" {
		runID = in.RunID
	}
	_, err = conn.Exec(ctx, `
		INSERT INTO jobs_log (run_id, job_type, job_id, status, payload, idempotency_key, queue_key, attempt, max_attempts)
		VALUES ($1::uuid, $2, $3, 'enqueued', $4::jsonb, $5, $6, 0, $7)
	`, runID, in.JobType, in.JobID, payloadJSON, in.IdempotencyKey, in.QueueKey, maxAttempts)
	return true, in.JobID, err
}

func shouldSkipEnqueue(status string, leaseExpires *string) bool {
	switch status {
	case "completed", "dead":
		return true
	case "enqueued", "claimed", "processing":
		if leaseExpires == nil || *leaseExpires == "" {
			return true
		}
		if t, err := time.Parse(time.RFC3339Nano, *leaseExpires); err == nil {
			return t.After(time.Now().UTC())
		}
		return true
	default:
		return false
	}
}

func copyPayload(src map[string]any) map[string]any {
	out := make(map[string]any, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}
