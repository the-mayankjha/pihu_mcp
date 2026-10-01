"""
Abstract base class for MCP Runtime Installers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from pihu.mcp.manifest import MCPPackageManifest


class BaseMCPRuntimeHandler(ABC):
    """Abstract interface for installing and building runtime environments for MCP servers."""

    @abstractmethod
    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        """Installs dependencies into target_dir and returns server entrypoint execution parameters."""
        pass
