# PIHU — Personalized Intelligent Human Utility

PIHU is a production-quality, modular personal AI agent runtime and intelligence layer that operates between the user and their digital environment.

## Monorepo Architecture

- `agent/`: Python Agent Runtime & Core Engine
- `cli/`: Go CLI & Terminal User Interface (Bubble Tea)
- `mcp/`: Model Context Protocol server configurations & integrations
- `docs/`: Architecture specifications and developer guides
- `tests/`: Automated unit and integration test suite

## Requirements

- Python 3.10
- Go 1.22+
- `uv` package manager

## Quickstart

```bash
# Create virtual environment with Python 3.10
uv venv pihu --python 3.10

# Install Python runtime package in editable mode
uv pip install -e ".[dev]" --python pihu/bin/python

# Run standalone runtime
pihu/bin/python -m pihu.main "What time is it?"
```
