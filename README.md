# PIHU — Personalized Intelligent Human Utility

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP Compliant](https://img.shields.io/badge/MCP-Standard-green.svg)](https://modelcontextprotocol.io/)
[![Interface](https://img.shields.io/badge/TUI-Textual-purple.svg)](https://textual.textualize.io/)
[![License](https://img.shields.io/badge/license-MIT-informational.svg)](LICENSE)

**PIHU** (*Personalized Intelligent Human Utility*) is an extensible, modular personal AI agent runtime, intelligence layer, and terminal operating environment. PIHU bridges user intent with local and cloud execution environments through the **Model Context Protocol (MCP)**, local LLMs (via Ollama), and frontier cloud models (via Google Gemini).

---

## ⚡ Key Features

- 🧠 **Dual LLM Architecture**: Seamlessly switch between local private LLMs (**Ollama**) and high-speed frontier cloud models (**Google Gemini**).
- 🔌 **Model Context Protocol (MCP) First**: Native multi-server MCP client supporting tool discovery, execution, streaming, and external server orchestration.
- 🖥️ **Interactive Terminal UI (TUI)**: Beautiful, responsive Catppuccin-themed full-terminal workspace built with [Textual](https://textual.textualize.io/) featuring live token streaming, phase-based execution rendering, tool trace inspector, and model picker.
- 🛡️ **Human-in-the-Loop Security**: Granular action permission model with real-time approval gates for write, destructive, and external system operations.
- 💾 **Persistent Session & Memory Store**: SQLite-backed asynchronous storage for conversation history, task memory, and tool invocation tracking.
- 🚀 **Cross-Platform CLI & IPC**: Run standalone prompt tasks, full interactive TUI mode, or pipe events via JSON-Lines IPC for external frontend integration (e.g. Go CLI).

---

## 🏛 Monorepo Architecture

```
pihu_mcps/
├── agent/                  # Python Agent Runtime & Core Engine
│   └── pihu/
│       ├── agent/          # Orchestrator & Execution Pipeline
│       ├── config/         # Environment & Pydantic Configuration
│       ├── context/        # Context Window & History Aggregator
│       ├── events/         # Event Bus & Streaming Telemetry
│       ├── intent/         # User Intent Classifier
│       ├── llm/            # LLM Provider Adapters (Ollama, Gemini, Router)
│       ├── mcp/            # MCP Client Manager & Tool Dispatcher
│       ├── memory/         # Async SQLite Session & Memory DB
│       ├── security/       # Permission & Approval Gatekeeper
│       ├── ui/             # Textual TUI Application, Modals & Widgets
│       ├── cli.py          # Rich CLI Task Executor
│       └── main.py         # Entrypoint & CLI Dispatcher
├── mcp/                    # Model Context Protocol Configurations & Servers
│   ├── config.json         # MCP Server Definitions & Commands
│   └── servers/            # Builtin MCP Servers
│       ├── pihu_file_mcp.py    # Local File System MCP Server
│       ├── pihu_system_mcp.py  # Host System & Hardware Metrics MCP Server
│       └── web-search-mcp/     # Web Search MCP Server
├── cli/                    # Optional Go CLI & Bubble Tea Frontend
├── tests/                  # Pytest Unit & Integration Test Suite
└── pyproject.toml          # Project Metadata & Dependencies
```

---

## 📦 Prerequisites

- **Python**: `3.10` (recommended via `uv` or `pyenv`)
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (fast Python package manager)
- **Local LLM (Optional)**: [Ollama](https://ollama.ai/) installed and running locally
- **Cloud LLM (Optional)**: [Google Gemini API Key](https://aistudio.google.com/)

---

## 🚀 Quickstart

### 1. Clone & Set Up Virtual Environment

```bash
# Clone repository
git clone https://github.com/your-username/pihu_mcps.git
cd pihu_mcps

# Create Python 3.10 virtual environment using uv
uv venv pihu --python 3.10
source pihu/bin/activate

# Install dependencies in editable mode
uv pip install -e ".[dev]"
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# LLM Provider Settings
PIHU_DEFAULT_PROVIDER=gemini        # "gemini" or "ollama"
PIHU_GEMINI_API_KEY=your_gemini_api_key_here
PIHU_GEMINI_MODEL=gemini-2.0-flash

# Ollama Settings (when using local models)
PIHU_OLLAMA_BASE_URL=http://127.0.0.1:11434
PIHU_OLLAMA_MODEL=qwen3:4b

# Security Guardrails
PIHU_AUTO_APPROVE_READ=true
PIHU_REQUIRE_APPROVAL_WRITE=true
PIHU_REQUIRE_APPROVAL_DESTRUCTIVE=true
```

---

## 💻 Usage

### 1. Interactive Terminal UI (TUI) Mode

Launch the full interactive Textual terminal application:

```bash
python -m pihu.main
```

Or specify preferred provider and model on startup:

```bash
python -m pihu.main --provider gemini --model gemini-2.0-flash
python -m pihu.main --provider ollama --model qwen3:4b
```

#### TUI Keyboard Shortcuts

| Shortcut | Description |
|---|---|
| `Ctrl + Q` / `Esc` | Focus Input / Dismiss Modal |
| `Ctrl + C` | Cancel current task / Quit |
| `Ctrl + P` | Open Model / Provider Picker |
| `Enter` | Submit prompt / Confirm action |

---

### 2. Single-Command / CLI Mode

Execute tasks directly with Rich-formatted terminal output:

```bash
# System status query
python -m pihu.main "Give me a snapshot of current system resources and memory usage."

# File creation & analysis
python -m pihu.main "List files in the current directory and explain the project structure."

# Web query
python -m pihu.main "What are the latest updates on Python 3.13 release?"
```

---

### 3. JSON-Lines IPC Mode

For embedding PIHU into external clients (such as the Go CLI in `cli/` or Electron/web wrappers):

```bash
python -m pihu.main --json "Summarize the project README"
```

---

## 🛠️ Built-in MCP Servers

PIHU connects to MCP servers configured in `mcp/config.json`:

| Server | Tools Provided | Description |
|---|---|---|
| `pihu-file-mcp` | `read_file`, `write_file`, `list_directory`, `stat_file`, `tree` | Safe, sandboxed workspace file access & manipulation |
| `pihu-system-mcp` | `get_system_info`, `get_system_status`, `get_system_snapshot`, `get_current_time` | Real-time CPU, RAM, disk, battery, and host OS telemetry |
| `web-search` | `search`, `fetch_page` | Live internet searching and content fetching |
| `memory` | `read_graph`, `create_entities`, `search_nodes` | Persistent knowledge graph memory (npx) |

---

## 🧪 Testing

Run the automated test suite with `pytest`:

```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
