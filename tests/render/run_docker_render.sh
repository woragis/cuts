#!/usr/bin/env bash
# Render via Docker — mesmas fontes/FFmpeg do worker Railway (fontconfig + Montserrat Bold).
#
# Exemplos:
#   ./run_docker_render.sh
#   RENDER_MODE=subtitles CUT_ID=long-cut-03 ./run_docker_render.sh
#   RENDER_MODE=outro ./run_docker_render.sh
#   RENDER_MODE=full FORCE_WHISPER=1 OPENAI_API_KEY=sk-... ./run_docker_render.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export CHANNEL_SLUG="${CHANNEL_SLUG:-politica-mbl}"
export CUT_ID="${CUT_ID:-long-cut-03}"
export CUT_FORMAT="${CUT_FORMAT:-long}"
export RENDER_MODE="${RENDER_MODE:-subtitles}"

cd "$SCRIPT_DIR"

echo "=== Docker render (Railway worker image) ==="
echo "channel=$CHANNEL_SLUG cut=$CUT_ID format=$CUT_FORMAT mode=$RENDER_MODE"

docker compose -f docker-compose.render.yml build
docker compose -f docker-compose.render.yml run --rm render

echo ""
echo "Output: $SCRIPT_DIR/output/${CHANNEL_SLUG}_${CUT_ID}/"
