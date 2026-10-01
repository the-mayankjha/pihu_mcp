"""
Package ID & Version Resolver for PIHU MCP Subsystem.
"""

from typing import Tuple, Optional


class MCPResolver:
    """Parses package specifications like 'google-workspace' or 'google-workspace@1.2.0'."""

    @staticmethod
    def parse_spec(spec: str) -> Tuple[str, str]:
        """Parses target string into (package_id, version)."""
        spec = spec.strip()
        if "@" in spec and not spec.startswith("@"):
            parts = spec.split("@", 1)
            return parts[0].strip(), parts[1].strip()
        elif spec.startswith("@") and spec.count("@") > 1:
            idx = spec.rfind("@")
            return spec[:idx].strip(), spec[idx+1:].strip()
        return spec, "latest"
