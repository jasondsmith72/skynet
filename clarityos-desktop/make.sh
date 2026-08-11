#!/bin/bash
# Build a ClarityOS Desktop image.
#
#   ./make.sh            build stage m0
#   ./make.sh m1         build stage m1 (llama-server + model)
#   EXPORT_RAW=1 ./make.sh m1    also emit the raw image for writing to USB
#
# build.sh is bind-mounted over the copy baked into the builder image, so edits to it take
# effect immediately. Without this it is far too easy to edit build.sh, rerun, and silently
# get the stale version that was COPYed in at docker-build time.
set -euo pipefail

cd "$(dirname "$0")"
STAGE="${1:-m0}"
IMAGE="${IMAGE:-clarityos-builder:m1}"
HERE="$(pwd -W 2>/dev/null || pwd)"

mkdir -p out cache

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Builder image $IMAGE missing; building it (this compiles llama.cpp, ~5 min)..."
  docker build -t "$IMAGE" ./build
fi

echo "Building stage $STAGE ..."
exec docker run --rm \
  -e STAGE="$STAGE" \
  -e EXPORT_RAW="${EXPORT_RAW:-0}" \
  ${MODEL_URL:+-e MODEL_URL="$MODEL_URL"} \
  -v "$HERE/out:/out" \
  -v "$HERE/cache:/cache" \
  -v "$HERE/build/build.sh:/usr/local/bin/build.sh:ro" \
  "$IMAGE"
