package pydelegate

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/woragis/cuts-go-pipeline/config"
	"github.com/woragis/cuts-go-pipeline/queue"
)

type Runner struct {
	Cfg config.Config
}

func (r Runner) Available() bool {
	if r.Cfg.PythonWorkerRoot == "" {
		return false
	}
	script := filepath.Join(r.Cfg.PythonWorkerRoot, "cuts_worker", "single_job.py")
	if st, err := os.Stat(script); err != nil || st.IsDir() {
		return false
	}
	return true
}

func (r Runner) Run(
	ctx context.Context,
	env queue.Envelope,
	queueKey, processingKey string,
	raw []byte,
) error {
	if !r.Available() {
		return fmt.Errorf("python worker not configured (set PYTHON_WORKER_ROOT to backend/worker)")
	}
	tmp, err := os.CreateTemp("", "cuts-job-*.json")
	if err != nil {
		return err
	}
	path := tmp.Name()
	defer os.Remove(path)

	if _, err := tmp.Write(raw); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}

	cmd := exec.CommandContext(ctx, r.Cfg.PythonBin, "-m", "cuts_worker.single_job")
	cmd.Dir = r.Cfg.PythonWorkerRoot
	cmd.Env = append(os.Environ(),
		"JOB_ENVELOPE_FILE="+path,
		"JOB_QUEUE_KEY="+queueKey,
		"JOB_PROCESSING_KEY="+processingKey,
		"DATABASE_URL="+r.Cfg.DatabaseURL,
		"REDIS_URL="+r.Cfg.RedisURL,
		"DATA_DIR="+r.Cfg.DataDir,
		"YT_DLP_BIN="+r.Cfg.YTDlpBin,
		"WHISPER_BIN="+r.Cfg.WhisperBin,
		"FFMPEG_BIN="+r.Cfg.FFmpegBin,
		"WORKER_STAGE="+r.Cfg.WorkerStage,
		"PYTHONUNBUFFERED=1",
	)
	if r.Cfg.S3Endpoint != "" {
		cmd.Env = append(cmd.Env,
			"S3_ENDPOINT="+r.Cfg.S3Endpoint,
			"S3_ACCESS_KEY="+r.Cfg.S3AccessKey,
			"S3_SECRET_KEY="+r.Cfg.S3SecretKey,
			"S3_BUCKET="+r.Cfg.S3Bucket,
			"S3_REGION="+r.Cfg.S3Region,
		)
		if r.Cfg.S3UseSSL {
			cmd.Env = append(cmd.Env, "S3_USE_SSL=true")
		}
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("python delegate job_type=%s: %w", env.Type, err)
	}
	return nil
}
