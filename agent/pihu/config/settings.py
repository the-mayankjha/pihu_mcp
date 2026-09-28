from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import os

def _find_env_file() -> Optional[str]:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
        Path.home() / ".pihu" / ".env",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None

class Settings(BaseSettings):
    """PIHU Agent Settings & Configuration"""
    model_config = SettingsConfigDict(
        env_prefix="PIHU_",
        env_file=_find_env_file(),
        extra="ignore"
    )

    # General
    app_name: str = "PIHU"
    debug: bool = False
    project_root: Path = Field(default_factory=lambda: Path.cwd())

    # LLM Settings
    default_provider: str = "gemini"  # "gemini" or "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # MCP Settings
    mcp_config_path: Path = Field(default_factory=lambda: Path.cwd() / "mcp" / "config.json")
    mcp_tool_timeout: float = 30.0

    # Security Settings
    auto_approve_read: bool = True
    require_approval_write: bool = True
    require_approval_external: bool = True
    require_approval_destructive: bool = True

    # Storage & Session Settings
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".pihu")
    db_filename: str = "pihu.db"

    @property
    def db_path(self) -> Path:
        p = self.data_dir / self.db_filename
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.data_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return p
        except Exception:
            fallback_dir = self.project_root / ".pihu"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / self.db_filename

settings = Settings()
