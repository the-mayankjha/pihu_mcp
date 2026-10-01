"""
Manifest data models and validation for PIHU MCP Registry packages.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from enum import Enum


class MCPRuntimeType(str, Enum):
    PYTHON = "python"
    NODE = "node"
    BINARY = "binary"
    REMOTE = "remote"


class MCPTransportType(str, Enum):
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"
    SSE = "sse"


@dataclass
class MCPRepositoryInfo:
    type: str = "git"
    url: str = ""
    branch: Optional[str] = None


@dataclass
class MCPInstallationSpec:
    method: str = "pip"  # pip, git, npm, binary, remote
    package: Optional[str] = None
    url: Optional[str] = None
    checksum_sha256: Optional[str] = None


@dataclass
class MCPEntrypoint:
    command: str = "python"
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class MCPRequirements:
    python: Optional[str] = ">=3.10"
    node: Optional[str] = ">=18"
    os: List[str] = field(default_factory=lambda: ["darwin", "linux", "windows"])


@dataclass
class MCPPermissions:
    network: bool = False
    filesystem: bool = False
    shell_execution: bool = False
    env_vars_required: List[str] = field(default_factory=list)


@dataclass
class MCPPackageManifest:
    schema_version: int = 1
    id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    category: str = "General"
    runtime: MCPRuntimeType = MCPRuntimeType.PYTHON
    transport: MCPTransportType = MCPTransportType.STDIO
    repository: Optional[MCPRepositoryInfo] = None
    installation: MCPInstallationSpec = field(default_factory=MCPInstallationSpec)
    entrypoint: MCPEntrypoint = field(default_factory=MCPEntrypoint)
    requirements: MCPRequirements = field(default_factory=MCPRequirements)
    permissions: MCPPermissions = field(default_factory=MCPPermissions)
    endpoint: Optional[str] = None
    tools_provided: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPPackageManifest":
        repo_data = data.get("repository")
        repo = MCPRepositoryInfo(**repo_data) if isinstance(repo_data, dict) else None

        inst_data = data.get("installation", {})
        inst = MCPInstallationSpec(**inst_data) if isinstance(inst_data, dict) else MCPInstallationSpec()

        ep_data = data.get("entrypoint", {})
        ep = MCPEntrypoint(**ep_data) if isinstance(ep_data, dict) else MCPEntrypoint()

        req_data = data.get("requirements", {})
        req = MCPRequirements(**req_data) if isinstance(req_data, dict) else MCPRequirements()

        perm_data = data.get("permissions", {})
        perm = MCPPermissions(**perm_data) if isinstance(perm_data, dict) else MCPPermissions()

        runtime_val = data.get("runtime", "python")
        try:
            runtime_enum = MCPRuntimeType(runtime_val)
        except ValueError:
            runtime_enum = MCPRuntimeType.PYTHON

        transport_val = data.get("transport", "stdio")
        try:
            transport_enum = MCPTransportType(transport_val)
        except ValueError:
            transport_enum = MCPTransportType.STDIO

        return cls(
            schema_version=data.get("schema_version", 1),
            id=data.get("id", data.get("name", "")),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            category=data.get("category", "General"),
            runtime=runtime_enum,
            transport=transport_enum,
            repository=repo,
            installation=inst,
            entrypoint=ep,
            requirements=req,
            permissions=perm,
            endpoint=data.get("endpoint"),
            tools_provided=data.get("tools_provided", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> List[str]:
        errors = []
        if not self.id:
            errors.append("Manifest 'id' is required.")
        if not self.version:
            errors.append("Manifest 'version' is required.")
        if self.runtime not in MCPRuntimeType.__members__.values():
            errors.append(f"Invalid runtime '{self.runtime}'.")
        if self.runtime != MCPRuntimeType.REMOTE and not self.entrypoint.command:
            errors.append("Entrypoint command is required for local runtimes.")
        return errors
