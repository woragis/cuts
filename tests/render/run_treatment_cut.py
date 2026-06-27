#!/usr/bin/env python3
"""
Tests wrapper for treatment pipeline — outputs go to tests/render/output/.

Env:
  CHANNEL_SLUG=politica-mbl
  CUT_ID=merged-short-01
  RENDER_MODE=music
  CUTS_JSON=../../tests/cuts/output/.../verdict_c_claude.json
  OUTPUT_ROOT=../../tests/render/output
  YOUTUBE_URL=...
  TRANSCRIPT_JSON=../../tests/fixtures/results/.../transcript.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
TREATMENT_DIR = TESTS_ROOT.parent / "backend" / "worker" / "scripts" / "treatment"
sys.path.insert(0, str(TREATMENT_DIR))

from treatment_lib import (  # noqa: E402
    build_treatment_brief,
    default_rehook_for_cut,
    detect_silence,
    extract_clip,
    find_cut,
    load_channel,
    probe_video,
    render_music_only,
    render_edl_only,
    render_outro_only,
    render_rehook_only,
    render_reframing_only,
    render_silence_only,
    render_subtitles_only,
    render_thumbnail,
)

DEFAULT_CUTS = TESTS_ROOT / "fixtures" / "results" / "20260624T225609Z_eKxFuD3-pos" / "cuts_merged_claude.json"
DEFAULT_TRANSCRIPT = TESTS_ROOT / "fixtures" / "results" / "20260624T225609Z_eKxFuD3-pos" / "transcript.json"
DEFAULT_URL = "https://www.youtube.com/watch?v=eKxFuD3-pos"
SKIP_EXTRACT_MODES = {"music", "hook", "edl", "reframing", "subtitles", "outro", "thumbnail"}


def _output_root() -> Path:
    raw = os.environ.get("OUTPUT_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return (TESTS_ROOT / "render" / "output").resolve()


def _load_or_build_brief(
    *,
    work_dir: Path,
    cut: dict,
    channel: dict,
    clip_path: Path,
    clip_duration: float,
    removals: list,
    youtube_url: str,
    cut_format: str,
) -> dict:
    brief_path = work_dir / "cut_treatment.json"
    if brief_path.is_file() and os.environ.get("FORCE_BRIEF") != "1":
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        fmt = channel["formatDefaults"].get(cut_format, channel["formatDefaults"]["short"])
        brief.setdefault("audio", {})
        brief["audio"].update({
            "backgroundMusicPath": channel["assets"]["backgroundMusic"],
            "voiceTargetLufs": fmt["voiceTargetLufs"],
            "musicDbDuringSpeech": channel.get("audio", {}).get("musicDbDuringSpeech", -20),
        })
        brief.setdefault("outro", {})
        brief["outro"].update({
            "imagePath": channel["assets"]["outroImage"],
            "musicPath": channel["assets"]["outroMusic"],
            "durationSec": fmt["outroDurationSec"],
            "musicStartSec": channel.get("audio", {}).get(
                "outroMusicStartSec", fmt.get("outroMusicStartSec", 8)
            ),
            "musicVolume": channel.get("audio", {}).get("outroMusicVolume", 0.28),
            "voiceFadeSec": channel.get("audio", {}).get(
                "outroTailVoiceFadeSec", fmt.get("voiceFadeSec", 1.2)
            ),
            "videoCrossfadeSec": channel.get("audio", {}).get("outroVideoCrossfadeSec", 1.0),
            "musicFadeInSec": channel.get("audio", {}).get("outroMusicFadeInSec", 1.0),
        })
        brief.setdefault("subtitles", {})
        brief["subtitles"].setdefault(
            "templatePath",
            channel.get("subtitles", {}).get("templatePath", "subtitles/templates/politica-mbl-long.json"),
        )
        if not brief.get("hook"):
            hook = default_rehook_for_cut(cut)
            if hook:
                brief["hook"] = hook
        return brief

    return build_treatment_brief(
        cut=cut,
        channel=channel,
        clip_path=clip_path,
        clip_duration=clip_duration,
        silence_removals=removals,
        youtube_url=youtube_url,
        cut_format=cut_format,
    )


def main() -> int:
    channel_slug = os.environ.get("CHANNEL_SLUG", "politica-mbl")
    cut_id = os.environ.get("CUT_ID", "long-cut-03")
    render_mode = os.environ.get("RENDER_MODE", "music").lower()
    youtube_url = os.environ.get("YOUTUBE_URL", DEFAULT_URL)
    cuts_path = Path(os.environ.get("CUTS_JSON", str(DEFAULT_CUTS)))

    channel = load_channel(channel_slug)
    cuts_data = json.loads(cuts_path.read_text(encoding="utf-8"))
    found = find_cut(cuts_data, cut_id)
    if found is None:
        print(f"Cut not found: {cut_id} in {cuts_path}", file=sys.stderr)
        return 1
    cut, cut_format = found
    cut_format = os.environ.get("CUT_FORMAT", cut_format)

    work_dir = _output_root() / f"{channel_slug}_{cut_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    print("=== Treatment test (tests/render) ===", flush=True)
    print(f"channel={channel_slug} cut={cut_id} format={cut_format} render={render_mode}")
    print(f"title={cut.get('title')}")
    print(f"cuts_json={cuts_path}")
    print(f"work_dir={work_dir}")

    brief_path = work_dir / "cut_treatment.json"
    clip_raw = work_dir / "clip_raw.mp4"
    clip_silence = work_dir / "clip_silence.mp4"

    if render_mode in SKIP_EXTRACT_MODES and clip_silence.is_file():
        print(f"\n--- Skipping extract/silence (reusing {clip_silence.name}) ---", flush=True)
        info = probe_video(clip_silence)
        removals = []
        if brief_path.is_file():
            removals = json.loads(brief_path.read_text(encoding="utf-8")).get("silence", {}).get("removals", [])
        brief = _load_or_build_brief(
            work_dir=work_dir,
            cut=cut,
            channel=channel,
            clip_path=clip_raw if clip_raw.is_file() else clip_silence,
            clip_duration=info["duration"],
            removals=removals,
            youtube_url=youtube_url,
            cut_format=cut_format,
        )
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        start = float(cut["startSec"])
        end = float(cut["endSec"])
        print(f"vod={start:.0f}s-{end:.0f}s ({end - start:.0f}s)")

        if not clip_raw.is_file() or os.environ.get("FORCE_EXTRACT") == "1":
            print("\n--- Extract clip ---", flush=True)
            extract_clip(youtube_url=youtube_url, start_sec=start, end_sec=end, output_path=clip_raw)
            print(f"  saved {clip_raw} ({clip_raw.stat().st_size / (1024 * 1024):.1f} MB)")
        else:
            print(f"\n--- Reusing {clip_raw} ---", flush=True)

        info = probe_video(clip_raw)
        print(f"  clip duration={info['duration']:.1f}s {info['width']}x{info['height']}")

        print("\n--- Silence detect ---", flush=True)
        removals = detect_silence(
            clip_raw,
            threshold_db=float(channel["silence"]["thresholdDb"]),
            min_duration_sec=float(channel["silence"]["minDurationSec"]),
        )
        removed_sec = sum(r["endSec"] - r["startSec"] for r in removals)
        print(f"  removals={len(removals)} (~{removed_sec:.1f}s total)")

        brief = build_treatment_brief(
            cut=cut,
            channel=channel,
            clip_path=clip_raw,
            clip_duration=info["duration"],
            silence_removals=removals,
            youtube_url=youtube_url,
            cut_format=cut_format,
        )
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

        if render_mode == "silence":
            final_path = render_silence_only(work_dir=work_dir, brief=brief, channel=channel)
            print(f"\n=== DONE ===\nfinal: {final_path}")
            return 0

    if render_mode == "hook":
        final_path = render_rehook_only(work_dir=work_dir, brief=brief, channel=channel)
    elif render_mode == "edl":
        transcript_path = Path(os.environ.get("TRANSCRIPT_JSON", str(DEFAULT_TRANSCRIPT)))
        final_path = render_edl_only(
            work_dir=work_dir,
            brief=brief,
            cut=cut,
            transcript_path=transcript_path if transcript_path.is_file() else None,
        )
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    elif render_mode == "reframing":
        final_path = render_reframing_only(
            work_dir=work_dir,
            channel=channel,
            force_vision=os.environ.get("FORCE_VISION") == "1",
        )
    elif render_mode == "music":
        final_path = render_music_only(work_dir=work_dir, brief=brief, channel=channel)
    elif render_mode == "subtitles":
        final_path = render_subtitles_only(
            work_dir=work_dir,
            brief=brief,
            channel=channel,
            force_whisper=os.environ.get("FORCE_WHISPER") == "1",
        )
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    elif render_mode == "outro":
        final_path = render_outro_only(work_dir=work_dir, brief=brief, channel=channel)
    elif render_mode == "thumbnail":
        transcript_path = Path(os.environ.get("TRANSCRIPT_JSON", str(DEFAULT_TRANSCRIPT)))
        frame_sec = float(os.environ["THUMBNAIL_FRAME_SEC"]) if os.environ.get("THUMBNAIL_FRAME_SEC") else None
        final_path = render_thumbnail(
            work_dir=work_dir,
            brief=brief,
            channel=channel,
            transcript_path=transcript_path if transcript_path.is_file() else None,
            frame_sec=frame_sec,
            cut_format=cut_format,
        )
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    elif render_mode == "full":
        render_silence_only(work_dir=work_dir, brief=brief, channel=channel)
        render_rehook_only(work_dir=work_dir, brief=brief, channel=channel)
        if cut_format == "long":
            transcript_path = Path(os.environ.get("TRANSCRIPT_JSON", str(DEFAULT_TRANSCRIPT)))
            render_edl_only(
                work_dir=work_dir,
                brief=brief,
                cut=cut,
                transcript_path=transcript_path if transcript_path.is_file() else None,
            )
        render_subtitles_only(work_dir=work_dir, brief=brief, channel=channel)
        render_music_only(work_dir=work_dir, brief=brief, channel=channel)
        final_path = render_outro_only(work_dir=work_dir, brief=brief, channel=channel)
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(f"Unknown RENDER_MODE: {render_mode}", file=sys.stderr)
        return 1

    if final_path.suffix == ".mp4":
        final_info = probe_video(final_path)
        print(f"\n=== DONE ===\nfinal: {final_path}\nduration: {final_info['duration']:.1f}s")
    else:
        print(f"\n=== DONE ===\nfinal: {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
