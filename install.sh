#!/usr/bin/env bash
# ==============================================================================
#  PIHU Installer (Personalized Intelligent Human Utility)
#  Installs PIHU CLI, 5 MCP servers (53 tools), Python Agent runtime & TUI
# ==============================================================================

set -e

# ANSI styling
BOLD="\033[1m"
GREEN="\033[38;2;166;227;161m"
MAUVE="\033[38;2;203;166;247m"
SKY="\033[38;2;137;220;235m"
YELLOW="\033[38;2;249;226;175m"
RED="\033[38;2;243;139;168m"
MUTED="\033[38;2;108;112;134m"
RESET="\033[0m"

echo -e "${MAUVE}${BOLD}"
cat << "EOF"
  ██████╗ ██╗██╗  ██╗██╗   ██╗
  ██╔══██╗██║██║  ██║██║   ██║
  ██████╔╝██║███████║██║   ██║
  ██╔═══╝ ██║██╔══██║██║   ██║
  ██║     ██║██║  ██║╚██████╔╝
  ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ 
EOF
echo -e "${SKY}Personalized Intelligent Human Utility${RESET} • ${MUTED}AI Terminal IDE & MCP Agent${RESET}\n"

PIHU_HOME="${HOME}/.pihu"
BIN_DIR="${HOME}/.local/bin"
REPO_URL="https://github.com/the-mayankjha/pihu-os"
TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

# 1. System & Architecture Detection
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "${ARCH}" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *) echo -e "${RED}✗ Unsupported architecture: ${ARCH}${RESET}"; exit 1 ;;
esac

echo -e "${SKY}◈ Detected platform:${RESET} ${OS}/${ARCH}"

# 2. Prerequisites Check
echo -e "${SKY}◈ Checking dependencies...${RESET}"

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}✗ Python 3 is required. Please install Python 3.10+ and re-run.${RESET}"
    exit 1
fi

PYTHON_VER="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
echo -e "${GREEN}✓ Python ${PYTHON_VER} found${RESET}"

# 3. Create PIHU directories
echo -e "${SKY}◈ Preparing directory structure at ${PIHU_HOME}...${RESET}"
mkdir -p "${PIHU_HOME}" "${PIHU_HOME}/agent" "${PIHU_HOME}/mcp" "${BIN_DIR}"

# 4. Copy or download PIHU files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [ -d "${SCRIPT_DIR}/src-tauri/pihu_mcps" ]; then
    echo -e "${SKY}◈ Installing from local repository sources...${RESET}"
    cp -R "${SCRIPT_DIR}/src-tauri/pihu_mcps/agent" "${PIHU_HOME}/"
    cp -R "${SCRIPT_DIR}/src-tauri/pihu_mcps/mcp" "${PIHU_HOME}/"
    if [ -f "${SCRIPT_DIR}/src-tauri/pihu_mcps/pihu-cli" ]; then
        cp "${SCRIPT_DIR}/src-tauri/pihu_mcps/pihu-cli" "${BIN_DIR}/pihu"
        chmod +x "${BIN_DIR}/pihu"
    fi
elif [ -d "${SCRIPT_DIR}/agent" ] && [ -d "${SCRIPT_DIR}/mcp" ]; then
    echo -e "${SKY}◈ Installing from local package...${RESET}"
    cp -R "${SCRIPT_DIR}/agent" "${PIHU_HOME}/"
    cp -R "${SCRIPT_DIR}/mcp" "${PIHU_HOME}/"
    if [ -f "${SCRIPT_DIR}/pihu-cli" ]; then
        cp "${SCRIPT_DIR}/pihu-cli" "${BIN_DIR}/pihu"
        chmod +x "${BIN_DIR}/pihu"
    fi
else
    echo -e "${SKY}◈ Fetching latest PIHU packages from remote...${RESET}"
    git clone --depth 1 "${REPO_URL}.git" "${TMP_DIR}/pihu-repo" 2>/dev/null || {
        echo -e "${YELLOW}! Git clone failed. Downloading source archive...${RESET}"
        curl -fsSL "${REPO_URL}/archive/main.tar.gz" | tar -xz -C "${TMP_DIR}"
        mv "${TMP_DIR}"/pihu-os-* "${TMP_DIR}/pihu-repo"
    }
    cp -R "${TMP_DIR}/pihu-repo/src-tauri/pihu_mcps/agent" "${PIHU_HOME}/"
    cp -R "${TMP_DIR}/pihu-repo/src-tauri/pihu_mcps/mcp" "${PIHU_HOME}/"
fi

# 5. Build CLI binary if not yet present
if [ ! -f "${BIN_DIR}/pihu" ]; then
    if command -v go >/dev/null 2>&1; then
        echo -e "${SKY}◈ Compiling native PIHU CLI binary using Go...${RESET}"
        SRC_CLI_DIR=""
        if [ -d "${SCRIPT_DIR}/src-tauri/pihu_mcps/cli" ]; then
            SRC_CLI_DIR="${SCRIPT_DIR}/src-tauri/pihu_mcps/cli"
        elif [ -d "${SCRIPT_DIR}/cli" ]; then
            SRC_CLI_DIR="${SCRIPT_DIR}/cli"
        elif [ -d "${TMP_DIR}/pihu-repo/src-tauri/pihu_mcps/cli" ]; then
            SRC_CLI_DIR="${TMP_DIR}/pihu-repo/src-tauri/pihu_mcps/cli"
        fi

        if [ -n "${SRC_CLI_DIR}" ]; then
            (cd "${SRC_CLI_DIR}" && go build -o "${BIN_DIR}/pihu" ./cmd/pihu)
            chmod +x "${BIN_DIR}/pihu"
            echo -e "${GREEN}✓ PIHU binary compiled successfully → ${BIN_DIR}/pihu${RESET}"
        fi
    fi
fi

# 6. Setup Python Virtual Environment & Dependencies
echo -e "${SKY}◈ Configuring Python MCP agent runtime...${RESET}"
VENV_DIR="${PIHU_HOME}/.venv"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi

echo -e "${SKY}◈ Installing Python dependencies (fastmcp, httpx, rich, pydantic, anyio, psutil)...${RESET}"
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet fastmcp httpx rich pydantic anyio psutil mcp python-dotenv || {
    echo -e "${YELLOW}! Installing core dependencies individually...${RESET}"
    "${VENV_DIR}/bin/pip" install --quiet httpx rich pydantic anyio psutil python-dotenv
}
echo -e "${GREEN}✓ Python runtime configured at ${VENV_DIR}${RESET}"

# 7. Create default MCP configuration & environment
if [ ! -f "${PIHU_HOME}/.env" ]; then
    cat << EOF > "${PIHU_HOME}/.env"
# PIHU Environment Configuration
# Add your Gemini API keys below (or configure via /key inside PIHU)
# GEMINI_API_KEY=your_key_here
# PIHU_GEMINI_KEY_2=your_second_key_here
EOF
    echo -e "${GREEN}✓ Created default configuration at ${PIHU_HOME}/.env${RESET}"
fi

# 8. Shell PATH Integration
SHELL_RC=""
if [ -n "${ZSH_VERSION:-}" ] || [ "${SHELL##*/}" = "zsh" ]; then
    SHELL_RC="${HOME}/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [ "${SHELL##*/}" = "bash" ]; then
    SHELL_RC="${HOME}/.bashrc"
fi

if [ -n "${SHELL_RC}" ] && [ -f "${SHELL_RC}" ]; then
    if ! grep -q "${BIN_DIR}" "${SHELL_RC}"; then
        echo -e "\n# PIHU CLI" >> "${SHELL_RC}"
        echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "${SHELL_RC}"
        echo -e "${GREEN}✓ Added ${BIN_DIR} to ${SHELL_RC}${RESET}"
    fi
fi

echo -e "\n${GREEN}${BOLD}✓ PIHU Installation Complete!${RESET}\n"
echo -e "To start using PIHU:"
echo -e "  ${MAUVE}${BOLD}export PATH=\"${BIN_DIR}:\$PATH\"${RESET}"
echo -e "  ${MAUVE}${BOLD}pihu${RESET}                  # Start interactive TUI"
echo -e "  ${MAUVE}${BOLD}pihu \"your prompt\"${RESET}  # Run autonomous task directly"
echo -e "  ${MAUVE}${BOLD}pihu tools${RESET}            # List 53 active MCP tools"
echo -e "  ${MAUVE}${BOLD}pihu mcp${RESET}              # Inspect 5 connected MCP servers\n"
