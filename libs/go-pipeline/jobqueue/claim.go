package jobqueue

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
)

func ClaimJob(ctx context.Context, conn pgx.Tx, jobID, workerID string, leaseSeconds int) (bool, error) {
	if jobID == "" {
		return false, nil
	}
	if workerID == "" {
		workerID = "go-worker"
	}
	if leaseSeconds <= 0 {
		leaseSeconds = 900
	}
	lease := time.Now().UTC().Add(time.Duration(leaseSeconds) * time.Second)
	tag, err := conn.Exec(ctx, `
		UPDATE jobs_log SET status = 'processing', claimed_at = now(),
			first_claimed_at = COALESCE(first_claimed_at, now()), claimed_by = $1,
			lease_expires_at = $2, attempt = attempt + 1, updated_at = now()
		WHERE job_id = $3 AND status IN ('enqueued', 'claimed', 'processing')
	`, workerID, lease, jobID)
	if err != nil {
		return false, err
	}
	return tag.RowsAffected() > 0, nil
}

func CompleteJob(ctx context.Context, conn pgx.Tx, jobID string) error {
	if jobID == "" {
		return nil
	}
	_, err := conn.Exec(ctx, fmt.Sprintf(`
		UPDATE jobs_log SET status = 'completed', lease_expires_at = NULL,
			total_duration_ms = COALESCE(total_duration_ms, 0) + CASE
				WHEN claimed_at IS NOT NULL THEN GREATEST(0, (EXTRACT(EPOCH FROM (now() - claimed_at)) * 1000)::bigint)
				ELSE 0 END,
			updated_at = now()
		WHERE job_id = $1 AND status = 'processing'
	`), jobID)
	return err
}

func SkipJob(ctx context.Context, conn pgx.Tx, jobID, reason string) error {
	if jobID == "" {
		return nil
	}
	_, err := conn.Exec(ctx, fmt.Sprintf(`
		UPDATE jobs_log SET status = 'skipped', lease_expires_at = NULL, error_message = $2, updated_at = now(),
			total_duration_ms = COALESCE(total_duration_ms, 0) + CASE
				WHEN claimed_at IS NOT NULL THEN GREATEST(0, (EXTRACT(EPOCH FROM (now() - claimed_at)) * 1000)::bigint)
				ELSE 0 END
		WHERE job_id = $1 AND status = 'processing'
	`), jobID, truncate(reason, 4000))
	return err
}

func IsRunCancelled(ctx context.Context, conn pgx.Tx, runID string) (bool, error) {
	if runID == "" {
		return false, nil
	}
	var cancelled bool
	err := conn.QueryRow(ctx, `SELECT COALESCE(cancelled, false) FROM runs WHERE id = $1::uuid`, runID).Scan(&cancelled)
	return cancelled, err
}
