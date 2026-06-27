#!/usr/bin/env bash
# Batch render: silence → hook → reframing → music → subtitles (+ outro for long)
# Usage: ./run_render_batch.sh merged-short-01 [long-cut-03 ...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_ROOT="$(dirname "$SCRIPT_DIR")"
WORKER_DIR="$TESTS_ROOT/../backend/worker"

CHANNEL_SLUG="${CHANNEL_SLUG:-politica-mbl}"
VERDICT="${CUTS_JSON:-$TESTS_ROOT/cuts/output/20260624T225609Z_eKxFuD3-pos/verdict_c_claude.json}"
MODES="${RENDER_MODES:-silence hook reframing music subtitles}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 CUT_ID [CUT_ID...]" >&2
  exit 1
fi

cd "$WORKER_DIR"

for CUT in "$@"; do
  echo "========== $CUT =========="
  for MODE in $MODES; do
    echo "--- $CUT / $MODE ---"
    CHANNEL_SLUG="$CHANNEL_SLUG" \
    CUT_ID="$CUT" \
    RENDER_MODE="$MODE" \
    CUTS_JSON="$VERDICT" \
    OUTPUT_ROOT="$TESTS_ROOT/render/output" \
      python "$SCRIPT_DIR/run_treatment_cut.py"
  done
  if [[ "$CUT" == long-* ]]; then
    echo "--- $CUT / outro ---"
    CHANNEL_SLUG="$CHANNEL_SLUG" \
    CUT_ID="$CUT" \
    RENDER_MODE=outro \
    CUTS_JSON="$VERDICT" \
    OUTPUT_ROOT="$TESTS_ROOT/render/output" \
      python "$SCRIPT_DIR/run_treatment_cut.py"
  fi
done

echo "Done. Outputs: $TESTS_ROOT/render/output/"
