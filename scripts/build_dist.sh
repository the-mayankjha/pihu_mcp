#!/usr/bin/env bash
# ==============================================================================
#  PIHU Build & Release Packaging Script
#  Compiles cross-platform binaries and bundles MCP servers for distribution
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"

echo "==> Preparing build output directory at ${DIST_DIR}..."
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

PLATFORMS=(
    "darwin/arm64"
    "darwin/amd64"
    "linux/amd64"
    "linux/arm64"
)

cd "${SCRIPT_DIR}/cli"

for PLATFORM in "${PLATFORMS[@]}"; do
    OS="${PLATFORM%/*}"
    ARCH="${PLATFORM#*/}"
    OUTPUT_NAME="pihu-${OS}-${ARCH}"

    echo "==> Building ${OUTPUT_NAME}..."
    GOOS="${OS}" GOARCH="${ARCH}" go build -ldflags="-s -w" -o "${DIST_DIR}/${OUTPUT_NAME}" ./cmd/pihu

    # Create tarball bundle with agent & mcp servers
    TAR_NAME="pihu-${OS}-${ARCH}.tar.gz"
    echo "==> Packaging ${TAR_NAME}..."
    (
        TMP_PKG="$(mktemp -d)"
        mkdir -p "${TMP_PKG}/pihu"
        cp "${DIST_DIR}/${OUTPUT_NAME}" "${TMP_PKG}/pihu/pihu"
        cp -R "${SCRIPT_DIR}/agent" "${TMP_PKG}/pihu/"
        cp -R "${SCRIPT_DIR}/mcp" "${TMP_PKG}/pihu/"
        cp "${SCRIPT_DIR}/install.sh" "${TMP_PKG}/pihu/"
        tar -czf "${DIST_DIR}/${TAR_NAME}" -C "${TMP_PKG}" pihu
        rm -rf "${TMP_PKG}"
    )
done

# Build local current platform binary
echo "==> Building local native binary..."
go build -o "${SCRIPT_DIR}/pihu-cli" ./cmd/pihu

echo "==> Distribution packaging complete in ${DIST_DIR}:"
ls -lh "${DIST_DIR}"
