#!/usr/bin/env python3
"""
ABC pipeline v2 — 4 vereditos (A Gemini, B OpenAI, C Claude, C OpenAI).

Usage:
  cd backend/worker
  python ../../tests/cuts/run_abc_pipeline.py --fixture ../../tests/fixtures/default-run.json

Env: ANTHROPIC_API_KEY, OPENAI_API_KEY, WHISPER_REUSE=1, SKIP_PHASE_A/B, SKIP_PHASE_C_CLAUDE=1, SKIP_TRANSCRIPT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from abc_lib import (  # noqa: E402
    load_fixture,
    load_phase_a,
    resolve_transcript,
    run_phase_b,
    run_phase_c,
    write_validation_md,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ABC cuts pipeline v2")
    parser.add_argument(
        "--fixture",
        default=str(TESTS_ROOT / "fixtures" / "default-run.json"),
        help="Path to run fixture JSON",
    )
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    fixture = load_fixture(fixture_path)
    run_id = fixture.get("runId", "test-run")
    out_dir = Path(os.environ.get("OUTPUT_DIR", str(TESTS_ROOT / "cuts" / "output" / run_id)))
    out_dir.mkdir(parents=True, exist_ok=True)

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    youtube_url = fixture.get("youtubeUrl", "")

    print(f"run_id={run_id}")
    print(f"output={out_dir}")

    print("\n=== Phase A · Gemini (reuse baseline) ===")
    verdict_a = load_phase_a(fixture=fixture, out_dir=out_dir)

    transcript_reuse = None
    reuse_rel = fixture.get("transcript", {}).get("reusePath")
    if reuse_rel:
        candidate = TESTS_ROOT / reuse_rel
        if candidate.is_file():
            transcript_reuse = candidate

    print("\n=== Transcript ===")
    if not openai_key and not transcript_reuse and not (out_dir / "transcript.json").is_file():
        print("WARN: OPENAI_API_KEY missing — will try baseline transcript only", file=sys.stderr)

    try:
        transcript = resolve_transcript(
            youtube_url=youtube_url,
            language=fixture.get("language", "pt"),
            out_dir=out_dir,
            openai_key=openai_key,
            reuse_path=transcript_reuse,
        )
        print(f"  segments={len(transcript.get('segments', []))} source={transcript.get('source')}")
    except Exception as e:
        print(f"  transcript failed: {e}", file=sys.stderr)
        (out_dir / "transcript_error.txt").write_text(str(e), encoding="utf-8")
        transcript = {"segments": [], "durationSec": fixture.get("durationSec", 0), "source": "missing"}

    if not openai_key:
        print("Set OPENAI_API_KEY for phase B", file=sys.stderr)
        return 1

    print("\n=== Phase B · OpenAI transcript ===")
    verdict_b = run_phase_b(fixture=fixture, out_dir=out_dir, transcript=transcript, openai_key=openai_key)

    if not anthropic_key and os.environ.get("SKIP_PHASE_C_CLAUDE", "").strip() not in ("1", "true"):
        print("Set ANTHROPIC_API_KEY for phase C-Claude, or SKIP_PHASE_C_CLAUDE=1", file=sys.stderr)
        return 1

    print("\n=== Phase C · Merge ===")
    verdict_c_claude, verdict_c_openai = run_phase_c(
        fixture=fixture,
        out_dir=out_dir,
        verdict_a=verdict_a,
        verdict_b=verdict_b,
        transcript=transcript,
        anthropic_key=anthropic_key,
        openai_key=openai_key,
    )

    validation_path = out_dir / "validation.md"
    write_validation_md(
        path=validation_path,
        youtube_url=youtube_url,
        verdict_a=verdict_a,
        verdict_b=verdict_b,
        verdict_c_claude=verdict_c_claude,
        verdict_c_openai=verdict_c_openai,
        transcript_source=str(transcript.get("source") or ""),
    )

    summary = {
        "runId": run_id,
        "outputDir": str(out_dir),
        "counts": {
            "a_shorts": len(verdict_a.get("shorts") or []),
            "b_shorts": len(verdict_b.get("shorts") or []),
            "c_claude_shorts": len(verdict_c_claude.get("shorts") or []),
            "c_openai_shorts": len(verdict_c_openai.get("shorts") or []),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== DONE ===")
    print(f"validation.md -> {validation_path}")
    print(f"C-Claude shorts: {len(verdict_c_claude.get('shorts') or [])}")
    print(f"C-OpenAI shorts: {len(verdict_c_openai.get('shorts') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
