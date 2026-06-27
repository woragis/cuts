"""Shared ABC pipeline v2: OpenAI phase B, dual merge C, validation writer."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TESTS_ROOT = Path(__file__).resolve().parents[1]
CUTS_DIR = Path(__file__).resolve().parent
WORKER_ROOT = TESTS_ROOT.parent / "backend" / "worker"
SCRIPTS_ROOT = WORKER_ROOT / "scripts"
PROMPTS_DIR = CUTS_DIR / "prompts"

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
TRANSCRIPT_CHUNK_SEC = 900
CHUNK_PAUSE_SEC = 65


def _ensure_worker_path() -> None:
    root = str(WORKER_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prompt(name: str, **kwargs: Any) -> str:
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    for key, value in kwargs.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _fmt_ts(sec: float) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def parse_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, count=1)
        cleaned = re.sub(r"\s*```$", "", cleaned, count=1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def tag_cuts(cuts: list[dict], *, source: str, prefix: str) -> list[dict]:
    out: list[dict] = []
    for i, c in enumerate(cuts, start=1):
        item = dict(c)
        item["source"] = source
        item["id"] = item.get("id") or f"{prefix}-{i:02d}"
        item.setdefault("startSec", float(c.get("startSec", 0)))
        item.setdefault("endSec", float(c.get("endSec", 0)))
        item.setdefault("uselessParts", c.get("uselessParts") or [])
        out.append(item)
    return out


def transcript_slice(transcript: dict[str, Any], start: float, end: float) -> list[dict]:
    rows: list[dict] = []
    for seg in transcript.get("segments", []):
        s = float(seg.get("startSec", 0))
        e = float(seg.get("endSec", 0))
        if e < start or s > end:
            continue
        rows.append({"startSec": s, "endSec": e, "text": seg.get("text", "")})
    return rows


def cluster_by_time(cuts: list[dict], *, gap_sec: float = 150.0) -> list[list[dict]]:
    if not cuts:
        return []
    sorted_cuts = sorted(cuts, key=lambda c: float(c.get("startSec", 0)))
    clusters: list[list[dict]] = [[sorted_cuts[0]]]
    for cut in sorted_cuts[1:]:
        prev = clusters[-1][-1]
        if float(cut.get("startSec", 0)) - float(prev.get("endSec", 0)) <= gap_sec:
            clusters[-1].append(cut)
        else:
            clusters.append([cut])
    return clusters


def openai_chat_json(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 8192,
    max_retries: int = 8,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
    }
    last_error: Exception | None = None
    for attempt in range(max_retries):
        req = urllib.request.Request(
            OPENAI_CHAT_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            return parse_json_from_text(text)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"OpenAI HTTP {e.code}: {detail[:800]}")
            if e.code == 429 and attempt < max_retries - 1:
                wait = min(45 * (attempt + 1), 180)
                print(f"  OpenAI rate limit, waiting {wait}s ({attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            raise last_error from e
    raise last_error or RuntimeError("OpenAI request failed")


def claude_messages_json(
    *,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 12000,
    max_retries: int = 12,
) -> dict[str, Any]:
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    last_error: Exception | None = None
    for attempt in range(max_retries):
        req = urllib.request.Request(
            ANTHROPIC_API,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            blocks = payload.get("content") or []
            texts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
            return parse_json_from_text("\n".join(texts).strip())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Claude HTTP {e.code}: {detail[:800]}")
            if e.code in (429, 529) and attempt < max_retries - 1:
                retry_after = e.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else min(45 * (attempt + 1), 180)
                print(f"  Claude rate limit ({e.code}), waiting {wait}s")
                time.sleep(wait)
                continue
            raise last_error from e
    raise last_error or RuntimeError("Claude request failed")


def resolve_transcript(
    *,
    youtube_url: str,
    language: str,
    out_dir: Path,
    openai_key: str,
    reuse_path: Path | None = None,
) -> dict[str, Any]:
    transcript_path = out_dir / "transcript.json"
    if os.environ.get("WHISPER_REUSE", "1").strip() in ("1", "true") and transcript_path.is_file():
        print(f"  reusing {transcript_path}")
        return json.loads(transcript_path.read_text(encoding="utf-8"))

    if reuse_path and reuse_path.is_file():
        print(f"  copying baseline transcript {reuse_path}")
        data = json.loads(reuse_path.read_text(encoding="utf-8"))
        transcript_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    if os.environ.get("SKIP_TRANSCRIPT", "").strip() in ("1", "true"):
        raise RuntimeError("SKIP_TRANSCRIPT=1 but transcript.json missing")

    _ensure_worker_path()
    sys.path.insert(0, str(SCRIPTS_ROOT))
    from test_dual_merge_claude import resolve_transcript as _resolve  # noqa: WPS433

    data = _resolve(
        youtube_url=youtube_url,
        language=language,
        out_dir=out_dir,
        openai_key=openai_key,
    )
    transcript_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_phase_a(*, fixture: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    verdict_path = out_dir / "verdict_a.json"
    if verdict_path.is_file() and os.environ.get("SKIP_PHASE_A", "").strip() in ("1", "true"):
        print(f"  reusing {verdict_path}")
        return json.loads(verdict_path.read_text(encoding="utf-8"))

    baseline = fixture.get("baselineResults", "")
    video_cuts_env = os.environ.get("VIDEO_CUTS_JSON", "").strip()
    if video_cuts_env:
        source_path = Path(video_cuts_env)
    elif baseline:
        source_path = TESTS_ROOT / baseline / "cuts_merged.json"
    else:
        source_path = SCRIPTS_ROOT / "results" / "20260624T225609Z_eKxFuD3-pos" / "cuts_merged.json"

    if not source_path.is_file():
        raise FileNotFoundError(f"Phase A cuts not found: {source_path}")

    raw = json.loads(source_path.read_text(encoding="utf-8"))
    envelope = {
        "schemaVersion": 2,
        "phase": "a",
        "runId": fixture.get("runId", "test"),
        "youtubeUrl": fixture.get("youtubeUrl", ""),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": fixture.get("models", {}).get("phaseA", "gemini-2.5-pro"),
        "sourceFile": str(source_path),
        "shorts": tag_cuts(raw.get("shorts") or [], source="video", prefix="video-short"),
        "longCuts": tag_cuts(raw.get("longCuts") or [], source="video", prefix="video-long"),
    }
    verdict_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  phase A -> {verdict_path} ({len(envelope['shorts'])} shorts, {len(envelope['longCuts'])} longs)")
    return envelope


def analyze_transcript_openai(
    *,
    api_key: str,
    model: str,
    youtube_url: str,
    transcript: dict[str, Any],
    duration_sec: float,
    cut_brief: str,
) -> dict[str, Any]:
    system = (
        "Você é editor de vídeo para canal político brasileiro. "
        "Cortes COMPLETOS e INFORMATIVOS. Retorne APENAS JSON válido."
    )
    all_shorts: list[dict] = []
    all_long: list[dict] = []
    start = 0.0
    chunk_idx = 0
    pause = float(os.environ.get("CAPTION_CHUNK_PAUSE_SEC", str(CHUNK_PAUSE_SEC)))

    while start < duration_sec:
        end = min(start + TRANSCRIPT_CHUNK_SEC, duration_sec)
        chunk_idx += 1
        segments = transcript_slice(transcript, start, end)
        if not segments:
            start = end
            continue

        user = load_prompt(
            "phase_b_openai_transcript.md",
            chunk_idx=chunk_idx,
            start=int(start),
            end=int(end),
            youtube_url=youtube_url,
            cut_brief=cut_brief,
            segments_json=json.dumps(segments[:400], ensure_ascii=False),
        )
        print(f"  phase B chunk {chunk_idx} ({int(start)}–{int(end)}s) segments={len(segments)}")
        raw = openai_chat_json(api_key=api_key, model=model, system=system, user=user)
        all_shorts.extend(raw.get("shorts") or [])
        all_long.extend(raw.get("longCuts") or [])
        start = end
        if start < duration_sec:
            print(f"  pause {pause:.0f}s before next OpenAI chunk")
            time.sleep(pause)

    return {"shorts": all_shorts, "longCuts": all_long}


def run_phase_b(
    *,
    fixture: dict[str, Any],
    out_dir: Path,
    transcript: dict[str, Any],
    openai_key: str,
) -> dict[str, Any]:
    verdict_path = out_dir / "verdict_b.json"
    if verdict_path.is_file() and os.environ.get("SKIP_PHASE_B", "").strip() in ("1", "true"):
        print(f"  reusing {verdict_path}")
        return json.loads(verdict_path.read_text(encoding="utf-8"))

    model = os.environ.get("PHASE_B_MODEL", fixture.get("models", {}).get("phaseB", "gpt-4o"))
    duration = float(transcript.get("durationSec") or fixture.get("durationSec", 0))
    cap_max = float(os.environ.get("CAPTION_MAX_SEC", "0"))
    cap_duration = duration if cap_max <= 0 else min(duration, cap_max)

    raw = analyze_transcript_openai(
        api_key=openai_key,
        model=model,
        youtube_url=fixture.get("youtubeUrl", ""),
        transcript=transcript,
        duration_sec=cap_duration,
        cut_brief=fixture.get("cutBrief", ""),
    )
    envelope = {
        "schemaVersion": 2,
        "phase": "b",
        "runId": fixture.get("runId", "test"),
        "youtubeUrl": fixture.get("youtubeUrl", ""),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "transcriptSource": transcript.get("source", ""),
        "shorts": tag_cuts(raw.get("shorts") or [], source="caption", prefix="caption-short"),
        "longCuts": tag_cuts(raw.get("longCuts") or [], source="caption", prefix="caption-long"),
    }
    verdict_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  phase B -> {verdict_path} ({len(envelope['shorts'])} shorts, {len(envelope['longCuts'])} longs)")
    return envelope


def _merge_config(fixture: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "transcriptPadBeforeSec": 240,
        "transcriptPadAfterSec": 120,
        "transcriptMaxSegmentsBefore": 120,
        "transcriptMaxSegmentsInCluster": 200,
        "transcriptMaxSegmentsAfter": 60,
        "longClusterMinDurationSec": 180,
        "longClusterPadBeforeSec": 360,
        "longClusterPadAfterSec": 180,
        "longClusterMaxSegmentsInCluster": 350,
        "extendForMissingContext": True,
    }
    cfg = dict(defaults)
    cfg.update(fixture.get("merge") or {})
    return cfg


def _is_long_cluster(cluster: list[dict], *, min_duration_sec: float) -> bool:
    starts = [float(c.get("startSec", 0)) for c in cluster]
    ends = [float(c.get("endSec", 0)) for c in cluster]
    span = max(ends) - min(starts)
    if span >= min_duration_sec:
        return True
    for c in cluster:
        cid = str(c.get("id", "")).lower()
        if "long" in cid:
            return True
        if float(c.get("endSec", 0)) - float(c.get("startSec", 0)) >= min_duration_sec:
            return True
    return False


def _build_merge_clusters(
    video_cuts: list[dict],
    caption_cuts: list[dict],
    transcript: dict[str, Any],
    *,
    merge_cfg: dict[str, Any],
) -> list[dict]:
    combined = video_cuts + caption_cuts
    clusters = cluster_by_time(combined)
    default_pad_before = float(merge_cfg.get("transcriptPadBeforeSec", 240))
    default_pad_after = float(merge_cfg.get("transcriptPadAfterSec", 120))
    long_pad_before = float(merge_cfg.get("longClusterPadBeforeSec", 360))
    long_pad_after = float(merge_cfg.get("longClusterPadAfterSec", 180))
    long_min_span = float(merge_cfg.get("longClusterMinDurationSec", 180))
    max_before = int(merge_cfg.get("transcriptMaxSegmentsBefore", 120))
    max_in_default = int(merge_cfg.get("transcriptMaxSegmentsInCluster", 200))
    max_in_long = int(merge_cfg.get("longClusterMaxSegmentsInCluster", 350))
    max_after = int(merge_cfg.get("transcriptMaxSegmentsAfter", 60))

    payloads: list[dict] = []
    for i, cluster in enumerate(clusters, start=1):
        starts = [float(c.get("startSec", 0)) for c in cluster]
        ends = [float(c.get("endSec", 0)) for c in cluster]
        cluster_start = min(starts)
        cluster_end = max(ends)
        is_long = _is_long_cluster(cluster, min_duration_sec=long_min_span)
        pad_before = long_pad_before if is_long else default_pad_before
        pad_after = long_pad_after if is_long else default_pad_after
        max_in = max_in_long if is_long else max_in_default
        window_start = max(0, cluster_start - pad_before)
        window_end = cluster_end + pad_after

        transcript_before = transcript_slice(transcript, window_start, cluster_start)[:max_before]
        transcript_in = transcript_slice(transcript, cluster_start, cluster_end)[:max_in]
        transcript_after = transcript_slice(transcript, cluster_end, window_end)[:max_after]

        merge_hint = (
            "Leia transcriptBefore: se candidatos começam no meio da discussão, "
            "use action=extend e recue startSec até o setup mínimo."
        )
        if is_long:
            merge_hint += (
                " Cluster long: pode estender até cobrir arco completo do tópico; "
                "não force encurtar se a explicação exige mais tempo."
            )

        payloads.append({
            "clusterId": i,
            "clusterType": "long" if is_long else "short",
            "clusterWindowSec": {"start": cluster_start, "end": cluster_end},
            "transcriptWindowSec": {"start": window_start, "end": window_end},
            "candidates": cluster,
            "transcriptBefore": transcript_before,
            "transcriptInCluster": transcript_in,
            "transcriptAfter": transcript_after,
            "transcriptExcerpt": transcript_before + transcript_in + transcript_after,
            "mergeHint": merge_hint,
        })
    return payloads


def merge_verdicts(
    *,
    provider: str,
    api_key: str,
    model: str,
    youtube_url: str,
    cut_brief: str,
    video_cuts: list[dict],
    caption_cuts: list[dict],
    transcript: dict[str, Any],
    short_count: int,
    long_count: int,
    short_min_sec: int,
    short_ideal_sec: int,
    short_max_sec: int,
    long_min_sec: int,
    long_ideal_sec: int,
    long_max_sec: int,
    merge_cfg: dict[str, Any],
) -> dict[str, Any]:
    cluster_payloads = _build_merge_clusters(
        video_cuts, caption_cuts, transcript, merge_cfg=merge_cfg
    )
    system = (
        "Você consolida candidatos de cortes para live política em PT-BR. "
        "Completude informativa > hook no início. "
        "Use transcriptBefore para estender startSec quando faltar contexto. "
        "Short ideal ~{s_ideal}s, até {s_max}s se necessário. "
        "Long ideal ~{l_ideal}s, até {l_max}s quando explicação completa exigir — "
        "longs podem ficar abaixo do ideal se o tópico for focado. "
        "Consolide uselessParts. Retorne APENAS JSON válido."
    ).format(
        s_ideal=short_ideal_sec,
        s_max=short_max_sec,
        l_ideal=long_ideal_sec,
        l_max=long_max_sec,
    )
    user = load_prompt(
        "phase_c_merge.md",
        youtube_url=youtube_url,
        cut_brief=cut_brief,
        short_count=short_count,
        long_count=long_count,
        short_min_sec=short_min_sec,
        short_ideal_sec=short_ideal_sec,
        short_max_sec=short_max_sec,
        long_min_sec=long_min_sec,
        long_ideal_sec=long_ideal_sec,
        long_max_sec=long_max_sec,
        long_min_min=max(1, long_min_sec // 60),
        long_ideal_min=max(1, long_ideal_sec // 60),
        long_max_min=max(1, round(long_max_sec / 60)),
        clusters_json=json.dumps(cluster_payloads, ensure_ascii=False)[:180000],
    )
    seg_total = sum(
        len(c.get("transcriptBefore") or [])
        + len(c.get("transcriptInCluster") or [])
        + len(c.get("transcriptAfter") or [])
        for c in cluster_payloads
    )
    print(
        f"  merge ({provider}): {len(cluster_payloads)} clusters, "
        f"{len(video_cuts) + len(caption_cuts)} candidates, transcript_segs={seg_total}"
    )
    if provider == "openai":
        return openai_chat_json(api_key=api_key, model=model, system=system, user=user, max_tokens=12000)
    return claude_messages_json(api_key=api_key, model=model, system=system, user=user, max_tokens=12000)


def run_phase_c(
    *,
    fixture: dict[str, Any],
    out_dir: Path,
    verdict_a: dict[str, Any],
    verdict_b: dict[str, Any],
    transcript: dict[str, Any],
    anthropic_key: str,
    openai_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    targets = fixture.get("targets", {})
    shorts_cfg = targets.get("shorts", {})
    longs_cfg = targets.get("longCuts", {})
    short_count = shorts_cfg.get("count", 12)
    short_min_sec = int(shorts_cfg.get("minSec", 45))
    short_ideal_sec = int(shorts_cfg.get("idealSec", 70))
    short_max_sec = int(shorts_cfg.get("maxSec", 130))
    long_count = longs_cfg.get("count", 4)
    long_min_sec = int(longs_cfg.get("minSec", 240))
    long_ideal_sec = int(longs_cfg.get("idealSec", 480))
    long_max_sec = int(longs_cfg.get("maxSec", 900))
    merge_cfg = _merge_config(fixture)
    youtube_url = fixture.get("youtubeUrl", "")
    cut_brief = fixture.get("cutBrief", "")

    video_all = (verdict_a.get("shorts") or []) + (verdict_a.get("longCuts") or [])
    caption_all = (verdict_b.get("shorts") or []) + (verdict_b.get("longCuts") or [])

    claude_model = os.environ.get(
        "PHASE_C_CLAUDE_MODEL",
        fixture.get("models", {}).get("phaseCClaude", "claude-sonnet-4-6"),
    )
    openai_model = os.environ.get(
        "PHASE_C_OPENAI_MODEL",
        fixture.get("models", {}).get("phaseCOpenAI", "gpt-4o"),
    )

    skip_claude = os.environ.get("SKIP_PHASE_C_CLAUDE", "").strip() in ("1", "true")
    claude_path = out_dir / "verdict_c_claude.json"

    if skip_claude and claude_path.is_file() and os.environ.get("FORCE_PHASE_C_CLAUDE") != "1":
        print("\n=== Phase C · Claude merge (skipped, reusing) ===")
        verdict_c_claude = json.loads(claude_path.read_text(encoding="utf-8"))
    elif skip_claude:
        print("\n=== Phase C · Claude merge (SKIP_PHASE_C_CLAUDE=1) ===")
        verdict_c_claude = {
            "schemaVersion": 2,
            "phase": "c_claude",
            "runId": fixture.get("runId", "test"),
            "youtubeUrl": youtube_url,
            "skipped": True,
            "note": "SKIP_PHASE_C_CLAUDE=1 — use verdict_c_openai.json",
            "shorts": [],
            "longCuts": [],
            "decisions": [],
        }
        claude_path.write_text(json.dumps(verdict_c_claude, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print("\n=== Phase C · Claude merge ===")
        merged_claude = merge_verdicts(
            provider="claude",
            api_key=anthropic_key,
            model=claude_model,
            youtube_url=youtube_url,
            cut_brief=cut_brief,
            video_cuts=video_all,
            caption_cuts=caption_all,
            transcript=transcript,
            short_count=short_count,
            long_count=long_count,
            short_min_sec=short_min_sec,
            short_ideal_sec=short_ideal_sec,
            short_max_sec=short_max_sec,
            long_min_sec=long_min_sec,
            long_ideal_sec=long_ideal_sec,
            long_max_sec=long_max_sec,
            merge_cfg=merge_cfg,
        )
        verdict_c_claude = {
            "schemaVersion": 2,
            "phase": "c_claude",
            "runId": fixture.get("runId", "test"),
            "youtubeUrl": youtube_url,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "model": claude_model,
            "shorts": merged_claude.get("shorts") or [],
            "longCuts": merged_claude.get("longCuts") or [],
            "decisions": merged_claude.get("decisions") or [],
        }
        claude_path.write_text(json.dumps(verdict_c_claude, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Phase C · OpenAI merge ===")
    merged_openai = merge_verdicts(
        provider="openai",
        api_key=openai_key,
        model=openai_model,
        youtube_url=youtube_url,
        cut_brief=cut_brief,
        video_cuts=video_all,
        caption_cuts=caption_all,
        transcript=transcript,
        short_count=short_count,
        long_count=long_count,
        short_min_sec=short_min_sec,
        short_ideal_sec=short_ideal_sec,
        short_max_sec=short_max_sec,
        long_min_sec=long_min_sec,
        long_ideal_sec=long_ideal_sec,
        long_max_sec=long_max_sec,
        merge_cfg=merge_cfg,
    )
    verdict_c_openai = {
        "schemaVersion": 2,
        "phase": "c_openai",
        "runId": fixture.get("runId", "test"),
        "youtubeUrl": youtube_url,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "model": openai_model,
        "shorts": merged_openai.get("shorts") or [],
        "longCuts": merged_openai.get("longCuts") or [],
        "decisions": merged_openai.get("decisions") or [],
    }
    openai_path = out_dir / "verdict_c_openai.json"
    openai_path.write_text(json.dumps(verdict_c_openai, ensure_ascii=False, indent=2), encoding="utf-8")

    return verdict_c_claude, verdict_c_openai


def _useless_summary(parts: list[dict]) -> str:
    if not parts:
        return "—"
    bits = []
    for p in parts[:5]:
        bits.append(f"{_fmt_ts(float(p.get('startSec', 0)))}–{_fmt_ts(float(p.get('endSec', 0)))} ({p.get('severity', '?')})")
    return "; ".join(bits)


def _append_cut_section(
    lines: list[str],
    base: str,
    cuts: list[dict],
    *,
    heading_level: int = 3,
    phase_label: str = "",
) -> None:
    h = "#" * heading_level
    for i, cut in enumerate(sorted(cuts, key=lambda c: float(c.get("startSec", 0))), start=1):
        start = float(cut.get("startSec", 0))
        end = float(cut.get("endSec", start))
        duration = end - start
        link = f"{base}&t={int(start)}s"
        useless = cut.get("uselessParts") or []
        lines.extend([
            f"{h} {i}. {cut.get('title', '(sem título)')}",
            f"- **Timeline:** {_fmt_ts(start)} – {_fmt_ts(end)} (`{int(start)}s` – `{int(end)}s`, ~{duration:.0f}s)",
            f"- **Fase:** {phase_label or cut.get('source', '?')}",
            f"- **Topic:** {cut.get('topic', '—')}",
            f"- **Completeness:** {cut.get('completeness', '—')}",
            f"- **Score:** {cut.get('score', '?')}",
            f"- **Motivo:** {cut.get('reason', cut.get('description', ''))}",
        ])
        if cut.get("extendedBecause"):
            lines.append(f"- **Extend:** {cut.get('extendedBecause')}")
        if cut.get("action"):
            lines.append(f"- **Ação merge:** {cut.get('action')}")
        lines.append(f"- **uselessParts:** {_useless_summary(useless)}")
        if useless:
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(useless, ensure_ascii=False, indent=2))
            lines.append("```")
        if cut.get("mergedFrom"):
            lines.append(f"- **mergedFrom:** {cut.get('mergedFrom')}")
        lines.append(f"- **YouTube:** [{link}]({link})")
        lines.append("- [ ] Aprovado para render")
        lines.append("")


def write_validation_md(
    *,
    path: Path,
    youtube_url: str,
    verdict_a: dict[str, Any],
    verdict_b: dict[str, Any],
    verdict_c_claude: dict[str, Any],
    verdict_c_openai: dict[str, Any],
    transcript_source: str = "",
) -> None:
    base = youtube_url.split("&")[0]
    lines = [
        "# Validação manual — Pipeline ABC v2 (4 vereditos)",
        "",
        f"Vídeo: {base}",
        f"Gerado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Checklist rápido",
        "",
        "- [ ] Fase A: tópicos completos?",
        "- [ ] Fase B: alinhado com transcript?",
        "- [ ] C-Claude vs C-OpenAI: qual merge ficou melhor?",
        "- [ ] uselessParts fazem sentido?",
        "- [ ] Veredito escolhido para render: _______________",
        "",
    ]
    if transcript_source:
        lines.extend([f"> Transcript: `{transcript_source}`", ""])

    lines.extend(["---", "", f"## A · Gemini vídeo ({verdict_a.get('model', '?')})", ""])
    _append_cut_section(lines, base, (verdict_a.get("shorts") or []) + (verdict_a.get("longCuts") or []), phase_label="A")

    lines.extend(["---", "", f"## B · OpenAI transcript ({verdict_b.get('model', '?')})", ""])
    _append_cut_section(lines, base, (verdict_b.get("shorts") or []) + (verdict_b.get("longCuts") or []), phase_label="B")

    lines.extend(["---", "", f"## C-Claude · Merge ({verdict_c_claude.get('model', '?')})", ""])
    if verdict_c_claude.get("decisions"):
        lines.extend(["### Decisões", "", "```json", json.dumps(verdict_c_claude["decisions"], ensure_ascii=False, indent=2), "```", ""])
    _append_cut_section(lines, base, (verdict_c_claude.get("shorts") or []) + (verdict_c_claude.get("longCuts") or []), phase_label="C-Claude")

    lines.extend(["---", "", f"## C-OpenAI · Merge ({verdict_c_openai.get('model', '?')})", ""])
    if verdict_c_openai.get("decisions"):
        lines.extend(["### Decisões", "", "```json", json.dumps(verdict_c_openai["decisions"], ensure_ascii=False, indent=2), "```", ""])
    _append_cut_section(lines, base, (verdict_c_openai.get("shorts") or []) + (verdict_c_openai.get("longCuts") or []), phase_label="C-OpenAI")

    path.write_text("\n".join(lines), encoding="utf-8")
