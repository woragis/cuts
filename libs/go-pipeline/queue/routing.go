package queue

import (
	"strings"

	"github.com/woragis/cuts-go-pipeline/config"
)

var renderJobs = map[string]struct{}{
	JobMetadataGenerate: {}, JobSubtitleGenerate: {},
	JobRenderShort: {}, JobRenderLong: {}, JobOutroAppend: {},
}

var thumbnailJobs = map[string]struct{}{
	JobThumbnailGenerate: {}, JobThumbnailPlan: {},
}

var publishJobs = map[string]struct{}{
	JobPublishYouTube: {}, JobPublishInstagram: {}, JobPublishTikTok: {},
}

var transcribeJobs = map[string]struct{}{
	JobTranscribeRun: {}, JobTranscribePlan: {}, JobTranscribeChunk: {}, JobTranscribeMerge: {},
}

var analyzeJobs = map[string]struct{}{
	JobAnalyzeGeminiChunk: {}, JobAnalyzeTranscriptChunk: {},
	JobAnalyzeURL: {}, JobAnalyzeMerge: {}, JobAnalyzeTranscript: {},
}

var generalJobs = map[string]struct{}{
	JobIngestYouTube: {}, JobAnalyzePlan: {},
	JobAnalyzeGeminiMerge: {}, JobSchedulingPlan: {}, JobRunContinue: {}, JobRunRestart: {},
}

func QueueForJobType(cfg config.Config, jobType string) string {
	if _, ok := thumbnailJobs[jobType]; ok {
		return cfg.QueueThumbnail
	}
	if _, ok := renderJobs[jobType]; ok {
		return cfg.QueueRender
	}
	if _, ok := publishJobs[jobType]; ok {
		return cfg.QueuePublish
	}
	if _, ok := transcribeJobs[jobType]; ok {
		return cfg.QueueTranscribe
	}
	if _, ok := analyzeJobs[jobType]; ok {
		return cfg.QueueAnalyze
	}
	return cfg.QueueGeneral
}

func StageForJobType(jobType string) string {
	if _, ok := thumbnailJobs[jobType]; ok {
		return "thumbnail"
	}
	if _, ok := renderJobs[jobType]; ok {
		return "render"
	}
	if _, ok := publishJobs[jobType]; ok {
		return "publish"
	}
	if _, ok := transcribeJobs[jobType]; ok {
		return "transcribe"
	}
	if _, ok := analyzeJobs[jobType]; ok {
		return "analyze"
	}
	return "general"
}

func JobAllowedForStage(jobType, stage string) bool {
	stage = strings.ToLower(strings.TrimSpace(stage))
	if stage == "" || stage == "all" {
		return true
	}
	return StageForJobType(jobType) == stage
}

func IsGeneralJob(jobType string) bool {
	_, ok := generalJobs[jobType]
	return ok
}

func ProcessingKey(mainQueue string) string {
	return mainQueue + ":processing"
}
