package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

var validStages = map[string]struct{}{
	"general": {}, "analyze": {}, "transcribe": {}, "render": {},
	"thumbnail": {}, "publish": {},
}

type Config struct {
	DatabaseURL       string
	RedisURL          string
	DataDir           string
	WorkerStage       string
	Concurrency       int
	BrpopTimeoutS     int
	JobLeaseSeconds   int
	JobMaxAttempts    int
	MetricsTTLSeconds int
	InstanceID        string
	YTDlpBin          string
	WhisperBin        string
	FFmpegBin         string
	PythonBin         string
	PythonWorkerRoot  string
	QueueGeneral      string
	QueueTranscribe   string
	QueueAnalyze      string
	QueueRender       string
	QueueThumbnail    string
	QueuePublish      string
	S3Endpoint        string
	S3AccessKey       string
	S3SecretKey       string
	S3Bucket          string
	S3UseSSL          bool
	S3Region          string
	YTDlpCookiesFile  string
}

func Load() (Config, error) {
	cfg := Config{
		DatabaseURL:      strings.TrimSpace(os.Getenv("DATABASE_URL")),
		RedisURL:         strings.TrimSpace(os.Getenv("REDIS_URL")),
		DataDir:          envOr("DATA_DIR", "/data"),
		WorkerStage:      strings.ToLower(envOr("WORKER_STAGE", "general")),
		InstanceID:       strings.TrimSpace(os.Getenv("WORKER_INSTANCE_ID")),
		YTDlpBin:         envOr("YT_DLP_BIN", "yt-dlp"),
		WhisperBin:       envOr("WHISPER_BIN", "whisper"),
		FFmpegBin:        envOr("FFMPEG_BIN", "ffmpeg"),
		PythonBin:        envOr("PYTHON_BIN", "python"),
		PythonWorkerRoot: strings.TrimSpace(os.Getenv("PYTHON_WORKER_ROOT")),
		QueueGeneral:     envOr("REDIS_QUEUE_GENERAL", "cuts:jobs"),
		QueueTranscribe:  envOr("REDIS_QUEUE_TRANSCRIBE", "cuts:jobs:transcribe"),
		QueueAnalyze:     envOr("REDIS_QUEUE_ANALYZE", "cuts:jobs:analyze"),
		QueueRender:      envOr("REDIS_QUEUE_RENDER", "cuts:jobs:render"),
		QueueThumbnail:   envOr("REDIS_QUEUE_THUMBNAIL", "cuts:jobs:thumbnail"),
		QueuePublish:     envOr("REDIS_QUEUE_PUBLISH", "cuts:jobs:publish"),
		S3Endpoint:       strings.TrimSpace(os.Getenv("S3_ENDPOINT")),
		S3AccessKey:      strings.TrimSpace(os.Getenv("S3_ACCESS_KEY")),
		S3SecretKey:      strings.TrimSpace(os.Getenv("S3_SECRET_KEY")),
		S3Bucket:         envOr("S3_BUCKET", "cuts"),
		S3Region:         envOr("S3_REGION", "us-east-1"),
		YTDlpCookiesFile: strings.TrimSpace(os.Getenv("YT_DLP_COOKIES_FILE")),
	}
	cfg.Concurrency = envInt("WORKER_CONCURRENCY", cfg.defaultConcurrency())
	cfg.BrpopTimeoutS = envInt("WORKER_BRPOP_TIMEOUT_S", 5)
	cfg.JobLeaseSeconds = envInt("JOB_LEASE_SECONDS", 900)
	cfg.JobMaxAttempts = envInt("JOB_MAX_ATTEMPTS", 3)
	cfg.MetricsTTLSeconds = envInt("WORKER_METRICS_TTL_S", 90)
	cfg.S3UseSSL = envBool("S3_USE_SSL")

	if cfg.DatabaseURL == "" {
		return cfg, fmt.Errorf("DATABASE_URL is required")
	}
	if cfg.RedisURL == "" {
		return cfg, fmt.Errorf("REDIS_URL is required")
	}
	if _, ok := validStages[cfg.WorkerStage]; !ok {
		return cfg, fmt.Errorf("WORKER_STAGE must be one of general, analyze, transcribe, render, thumbnail, publish (got %q)", cfg.WorkerStage)
	}
	return cfg, nil
}

func (c Config) defaultConcurrency() int {
	switch c.WorkerStage {
	case "analyze":
		return 16
	case "publish":
		return 8
	case "thumbnail":
		return 8
	case "general":
		return 8
	default:
		return 2
	}
}

func (c Config) ConsumeQueueKeys() []string {
	switch c.WorkerStage {
	case "analyze":
		return []string{c.QueueAnalyze}
	case "transcribe":
		return []string{c.QueueTranscribe}
	case "render":
		return []string{c.QueueRender}
	case "thumbnail":
		return []string{c.QueueThumbnail}
	case "publish":
		return []string{c.QueuePublish}
	default:
		return []string{c.QueueGeneral}
	}
}

func envOr(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return fallback
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return n
}

func envBool(key string) bool {
	switch strings.ToLower(strings.TrimSpace(os.Getenv(key))) {
	case "1", "true", "yes":
		return true
	default:
		return false
	}
}
