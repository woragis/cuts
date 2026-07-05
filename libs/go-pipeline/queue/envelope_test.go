package queue

import "testing"

func TestMakeIdempotencyKeyRun(t *testing.T) {
	key := MakeIdempotencyKey(JobAnalyzePlan, map[string]any{"run_id": "abc"})
	if key != "analyze.plan:abc" {
		t.Fatalf("got %q", key)
	}
}

func TestParseEnvelope(t *testing.T) {
	raw := []byte(`{"schema_version":1,"type":"analyze.plan","payload":{"run_id":"x"},"enqueued_at":"2026-01-01T00:00:00Z"}`)
	env, err := ParseEnvelope(raw)
	if err != nil || env.Type != JobAnalyzePlan {
		t.Fatalf("parse: %v %+v", err, env)
	}
}
