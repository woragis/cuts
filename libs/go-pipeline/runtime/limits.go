package runtime

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	redisKeyLimits = "cuts:runtime:limits"
	RedisKeyLimits = redisKeyLimits
	redisChannel   = "cuts:runtime:rev"
	refreshEvery   = 30 * time.Second
)

type StageLimits struct {
	MaxConcurrency int            `json:"max_concurrency"`
	MaxIngest      int            `json:"max_ingest,omitempty"`
	MaxPlan        int            `json:"max_plan,omitempty"`
	MaxLight       int            `json:"max_light,omitempty"`
	MaxPerPlatform map[string]int `json:"max_per_platform,omitempty"`
}

type ClusterLimits struct {
	MaxIngest int `json:"max_ingest"`
	MaxRender int `json:"max_render"`
}

type Limits struct {
	Rev        int64         `json:"rev"`
	General    StageLimits   `json:"general"`
	Analyze    StageLimits   `json:"analyze"`
	Transcribe StageLimits   `json:"transcribe"`
	Render     StageLimits   `json:"render"`
	Thumbnail  StageLimits   `json:"thumbnail"`
	Publish    StageLimits   `json:"publish"`
	Cluster    ClusterLimits `json:"cluster"`
}

func defaultLimits() Limits {
	return Limits{
		Rev: 1,
		General: StageLimits{
			MaxConcurrency: 8, MaxIngest: 4, MaxPlan: 8, MaxLight: 8,
		},
		Analyze:    StageLimits{MaxConcurrency: 4},
		Transcribe: StageLimits{MaxConcurrency: 1},
		Render:     StageLimits{MaxConcurrency: 1},
		Thumbnail:  StageLimits{MaxConcurrency: 2},
		Publish: StageLimits{
			MaxConcurrency: 6,
			MaxPerPlatform: map[string]int{"youtube": 2, "tiktok": 2, "instagram": 2},
		},
		Cluster: ClusterLimits{MaxIngest: 12, MaxRender: 8},
	}
}

func normalize(l *Limits) {
	def := defaultLimits()
	if l.General.MaxConcurrency <= 0 {
		l.General = def.General
	}
	if l.Analyze.MaxConcurrency <= 0 {
		l.Analyze = def.Analyze
	}
	if l.Transcribe.MaxConcurrency <= 0 {
		l.Transcribe = def.Transcribe
	}
	if l.Render.MaxConcurrency <= 0 {
		l.Render = def.Render
	}
	if l.Thumbnail.MaxConcurrency <= 0 {
		l.Thumbnail = def.Thumbnail
	}
	if l.Publish.MaxConcurrency <= 0 {
		l.Publish = def.Publish
	}
	if l.Cluster.MaxIngest <= 0 {
		l.Cluster = def.Cluster
	}
}

func concurrencyForJob(l Limits, stage, jobType string) int {
	switch stage {
	case "general":
		switch jobType {
		case "ingest.youtube.download":
			if l.General.MaxIngest > 0 {
				return min(l.General.MaxConcurrency, l.General.MaxIngest)
			}
		case "analyze.plan", "analyze.gemini.merge", "run.continue", "run.restart":
			if l.General.MaxPlan > 0 {
				return min(l.General.MaxConcurrency, l.General.MaxPlan)
			}
		case "scheduling.plan":
			if l.General.MaxLight > 0 {
				return min(l.General.MaxConcurrency, l.General.MaxLight)
			}
		}
		return l.General.MaxConcurrency
	case "analyze":
		return l.Analyze.MaxConcurrency
	case "transcribe":
		return l.Transcribe.MaxConcurrency
	case "render":
		return l.Render.MaxConcurrency
	case "thumbnail":
		return l.Thumbnail.MaxConcurrency
	case "publish":
		return l.Publish.MaxConcurrency
	default:
		return 1
	}
}

func globalSemKey(jobType string) string {
	switch jobType {
	case "ingest.youtube.download":
		return "cuts:sem:ingest"
	case "render.short", "render.long", "outro.append":
		return "cuts:sem:render"
	default:
		return ""
	}
}

func globalSemMax(l Limits, jobType string) int {
	switch jobType {
	case "ingest.youtube.download":
		return l.Cluster.MaxIngest
	case "render.short", "render.long", "outro.append":
		return l.Cluster.MaxRender
	default:
		return 0
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

type Limiter struct {
	rdb       *redis.Client
	stage     string
	fallback  int
	mu        sync.RWMutex
	limits    Limits
	fetchedAt time.Time
	local     localPool
}

func NewLimiter(rdb *redis.Client, stage string, fallbackConcurrency int) *Limiter {
	l := &Limiter{
		rdb: rdb, stage: stage, fallback: fallbackConcurrency,
		limits: defaultLimits(),
	}
	l.local = localPool{parent: l}
	return l
}

func (l *Limiter) Refresh(ctx context.Context) {
	l.mu.RLock()
	stale := time.Since(l.fetchedAt) > refreshEvery
	l.mu.RUnlock()
	if !stale {
		return
	}
	raw, err := l.rdb.Get(ctx, redisKeyLimits).Result()
	if err != nil {
		return
	}
	var parsed Limits
	if json.Unmarshal([]byte(raw), &parsed) != nil {
		return
	}
	normalize(&parsed)
	l.mu.Lock()
	l.limits = parsed
	l.fetchedAt = time.Now()
	l.mu.Unlock()
}

func (l *Limiter) limitsSnapshot() Limits {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.limits
}

func (l *Limiter) maxLocal(jobType string) int {
	lim := l.limitsSnapshot()
	n := concurrencyForJob(lim, l.stage, jobType)
	if n <= 0 {
		n = l.fallback
	}
	if n <= 0 {
		n = 1
	}
	return n
}

func (l *Limiter) AcquireLocal(ctx context.Context, jobType string) error {
	return l.local.acquire(ctx, jobType)
}

func (l *Limiter) ReleaseLocal() {
	l.local.release()
}

func (l *Limiter) AcquireGlobal(ctx context.Context, jobType string) (func(), error) {
	lim := l.limitsSnapshot()
	key := globalSemKey(jobType)
	max := globalSemMax(lim, jobType)
	if key == "" || max <= 0 {
		return func() {}, nil
	}
	for {
		ok, err := tryIncrSem(ctx, l.rdb, key, max)
		if err != nil {
			return func() {}, err
		}
		if ok {
			return func() { _ = l.rdb.Decr(context.Background(), key).Err() }, nil
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(400 * time.Millisecond):
		}
	}
}

type localPool struct {
	parent *Limiter
	mu     sync.Mutex
	active int
}

func (p *localPool) acquire(ctx context.Context, jobType string) error {
	for {
		p.mu.Lock()
		max := p.parent.maxLocal(jobType)
		if p.active < max {
			p.active++
			p.mu.Unlock()
			return nil
		}
		p.mu.Unlock()
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(50 * time.Millisecond):
		}
	}
}

func (p *localPool) release() {
	p.mu.Lock()
	if p.active > 0 {
		p.active--
	}
	p.mu.Unlock()
}

var incrSemScript = redis.NewScript(`
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
if n > tonumber(ARGV[1]) then
  redis.call('DECR', KEYS[1])
  return 0
end
return 1
`)

func tryIncrSem(ctx context.Context, rdb *redis.Client, key string, max int) (bool, error) {
	n, err := incrSemScript.Run(ctx, rdb, []string{key}, max, 3600).Int()
	if err != nil {
		return false, err
	}
	return n == 1, nil
}
