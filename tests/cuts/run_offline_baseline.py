#!/usr/bin/env python3
"""
Gera validation.md a partir do baseline copiado (sem API keys).

Útil para revisar cortes históricos antes de rodar o pipeline v2 completo.
Fase B aqui ainda é Claude (run antigo) — rotule como baseline.

Usage:
  python tests/cuts/run_offline_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from abc_lib import load_fixture, tag_cuts, write_validation_md  # noqa: E402

BASELINE = TESTS_ROOT / "fixtures" / "results" / "20260624T225609Z_eKxFuD3-pos"
OUT = TESTS_ROOT / "cuts" / "output" / "20260624T225609Z_eKxFuD3-pos"


def main() -> int:
    fixture = load_fixture(TESTS_ROOT / "fixtures" / "default-run.json")
    OUT.mkdir(parents=True, exist_ok=True)

    video_raw = json.loads((BASELINE / "cuts_merged.json").read_text(encoding="utf-8"))
    caption_raw = json.loads((BASELINE / "cuts_caption.json").read_text(encoding="utf-8"))
    merged_claude = json.loads((BASELINE / "cuts_merged_claude.json").read_text(encoding="utf-8"))

    verdict_a = {
        "model": "gemini-2.5-pro (baseline)",
        "shorts": tag_cuts(video_raw.get("shorts") or [], source="video", prefix="video-short"),
        "longCuts": tag_cuts(video_raw.get("longCuts") or [], source="video", prefix="video-long"),
    }
    verdict_b = {
        "model": "claude-sonnet (baseline B — substituir por OpenAI v2)",
        "shorts": tag_cuts(caption_raw.get("shorts") or [], source="caption", prefix="caption-short"),
        "longCuts": tag_cuts(caption_raw.get("longCuts") or [], source="caption", prefix="caption-long"),
    }
    verdict_c_claude = {
        "model": "claude-sonnet (baseline C)",
        "shorts": merged_claude.get("shorts") or [],
        "longCuts": merged_claude.get("longCuts") or [],
        "decisions": merged_claude.get("decisions") or [],
    }
    verdict_c_openai = {
        "model": "(pendente — rodar run_abc_pipeline.py)",
        "shorts": [],
        "longCuts": [],
        "decisions": [],
    }

    transcript_path = BASELINE / "transcript.json"
    transcript_source = ""
    if transcript_path.is_file():
        transcript_source = json.loads(transcript_path.read_text(encoding="utf-8")).get("source", "")

    validation_path = OUT / "validation_baseline.md"
    write_validation_md(
        path=validation_path,
        youtube_url=fixture.get("youtubeUrl", ""),
        verdict_a=verdict_a,
        verdict_b=verdict_b,
        verdict_c_claude=verdict_c_claude,
        verdict_c_openai=verdict_c_openai,
        transcript_source=transcript_source,
    )

    # prepend warning
    text = validation_path.read_text(encoding="utf-8")
    warning = (
        "> **Baseline histórico** — Fase B era Claude. Para 4 vereditos v2 (B=OpenAI, C-OpenAI), "
        "rode `run_abc_pipeline.py` com API keys.\n\n"
    )
    validation_path.write_text(warning + text, encoding="utf-8")

    print(f"validation_baseline.md -> {validation_path}")
    print(f"A shorts: {len(verdict_a['shorts'])}")
    print(f"B shorts: {len(verdict_b['shorts'])}")
    print(f"C-Claude shorts: {len(verdict_c_claude['shorts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
