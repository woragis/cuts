package queue

const SchemaVersion = 1

const (
	JobIngestYouTube        = "ingest.youtube.download"
	JobAnalyzeURL           = "analyze.gemini.url"
	JobAnalyzePlan          = "analyze.plan"
	JobAnalyzeGeminiMerge   = "analyze.gemini.merge"
	JobAnalyzeMerge         = "analyze.merge"
	JobTranscribeRun        = "transcribe.run"
	JobTranscribePlan       = "transcribe.plan"
	JobTranscribeChunk      = "transcribe.chunk"
	JobTranscribeMerge      = "transcribe.merge"
	JobAnalyzeTranscript    = "analyze.transcript"
	JobSchedulingPlan       = "scheduling.plan"
	JobRunContinue          = "run.continue"
	JobRunRestart           = "run.restart"
	JobAnalyzeGeminiChunk   = "analyze.gemini.chunk"
	JobAnalyzeTranscriptChunk = "analyze.transcript.chunk"
	JobMetadataGenerate     = "metadata.generate"
	JobThumbnailGenerate    = "thumbnail.generate"
	JobThumbnailPlan        = "thumbnail.plan"
	JobSubtitleGenerate     = "subtitle.generate"
	JobRenderShort          = "render.short"
	JobRenderLong           = "render.long"
	JobOutroAppend          = "outro.append"
	JobPublishYouTube       = "publish.youtube"
	JobPublishInstagram     = "publish.instagram"
	JobPublishTikTok        = "publish.tiktok"
)

type Envelope struct {
	SchemaVersion int            `json:"schema_version"`
	Type          string         `json:"type"`
	Payload       map[string]any `json:"payload"`
	EnqueuedAt    string         `json:"enqueued_at"`
}
