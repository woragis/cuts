package queue

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
)

func BuildEnvelope(jobType string, payload map[string]any) Envelope {
	return Envelope{
		SchemaVersion: SchemaVersion,
		Type:          jobType,
		Payload:       payload,
		EnqueuedAt:    time.Now().UTC().Format(time.RFC3339),
	}
}

func MarshalEnvelope(env Envelope) (string, error) {
	b, err := json.Marshal(env)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func ParseEnvelope(raw []byte) (*Envelope, error) {
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		return nil, err
	}
	if env.Type == "" || env.Payload == nil {
		return nil, fmt.Errorf("invalid envelope")
	}
	return &env, nil
}

func MakeIdempotencyKey(jobType string, payload map[string]any) string {
	planID := StrPayload(payload, "plan_id")
	cutID := StrPayload(payload, "cut_id")
	runID := StrPayload(payload, "run_id")
	communityID := StrPayload(payload, "community_id")
	scheduleDate := StrPayload(payload, "schedule_date")

	if chunk, ok := payload["chunk_index"]; ok && runID != "" {
		return fmt.Sprintf("%s:%s:chunk:%v", jobType, runID, chunk)
	}
	if planID != "" {
		return fmt.Sprintf("%s:plan:%s", jobType, planID)
	}
	if cutID != "" && runID != "" {
		if truthy(payload["force"]) || truthy(payload["regenerate"]) {
			jobID := StrPayload(payload, "job_id")
			if jobID == "" {
				jobID = uuid.NewString()
			}
			return fmt.Sprintf("%s:%s:%s:force:%s", jobType, runID, cutID, jobID)
		}
		fromStep := StrPayload(payload, "from_step")
		if fromStep == "" {
			fromStep = StrPayload(payload, "fromStep")
		}
		if fromStep != "" {
			jobID := StrPayload(payload, "job_id")
			if jobID == "" {
				jobID = uuid.NewString()
			}
			cont := payload["continue_pipeline"]
			if cont == nil {
				cont = payload["continuePipeline"]
			}
			if cont == nil {
				cont = true
			}
			return fmt.Sprintf("%s:%s:%s:step:%s:cont:%v:job:%s", jobType, runID, cutID, fromStep, cont, jobID)
		}
		return fmt.Sprintf("%s:%s:%s", jobType, runID, cutID)
	}
	if communityID != "" && scheduleDate != "" {
		return fmt.Sprintf("%s:%s:%s", jobType, communityID, scheduleDate)
	}
	if runID != "" {
		if jobType == "thumbnail.plan" && truthy(payload["force"]) {
			jobID := StrPayload(payload, "job_id")
			if jobID == "" {
				jobID = uuid.NewString()
			}
			return fmt.Sprintf("%s:%s:force:%s", jobType, runID, jobID)
		}
		return fmt.Sprintf("%s:%s", jobType, runID)
	}
	jobID := StrPayload(payload, "job_id")
	if jobID == "" {
		jobID = uuid.NewString()
	}
	return fmt.Sprintf("%s:job:%s", jobType, jobID)
}

func StrPayload(payload map[string]any, key string) string {
	raw, ok := payload[key]
	if !ok || raw == nil {
		return ""
	}
	return strings.TrimSpace(fmt.Sprint(raw))
}

func truthy(v any) bool {
	switch t := v.(type) {
	case bool:
		return t
	case string:
		return strings.EqualFold(t, "true")
	default:
		return false
	}
}
