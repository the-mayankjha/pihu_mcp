"""Shared local package inventory used by PIHU's CLI and desktop clients."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from pihu.config.settings import settings


class PackageStore:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.data_dir
        self.packages_dir = self.data_dir / "packages"
        self.mcps_dir = self.packages_dir / "mcps"
        self.spirits_dir = self.packages_dir / "spirits"
        self.state_path = self.data_dir / "installed.json"
        self.legacy_state_path = Path.home() / ".pihu" / "mcp" / "installed.json"
        self.mcps_dir.mkdir(parents=True, exist_ok=True)
        self.spirits_dir.mkdir(parents=True, exist_ok=True)

    def read(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {"schema_version": 1, "packages": {}, "servers": {}}
        for path in (self.state_path, self.legacy_state_path):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    continue
                state.update({k: v for k, v in payload.items() if k not in ("packages", "servers")})
                packages = payload.get("packages", {})
                servers = payload.get("servers", {})
                if isinstance(packages, dict):
                    state["packages"].update(
                        {key: value for key, value in packages.items() if isinstance(value, dict)}
                    )
                if isinstance(servers, dict):
                    state["servers"].update(
                        {key: value for key, value in servers.items() if isinstance(value, dict)}
                    )
            except (OSError, json.JSONDecodeError, TypeError):
                continue
        for package_id, record in state["servers"].items():
            state["packages"].setdefault(package_id, {**record, "type": "mcp"})
        state["schema_version"] = 1
        return state

    def write(self, state: Dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state["schema_version"] = 1
        if not isinstance(state.get("packages"), dict):
            state["packages"] = {}
        if not isinstance(state.get("servers"), dict):
            state["servers"] = {}
        fd, temp_name = tempfile.mkstemp(prefix="installed.", suffix=".tmp", dir=self.data_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.state_path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def record(self, record: Dict[str, Any], package_type: str) -> None:
        if package_type not in ("mcp", "spirits"):
            raise ValueError(f"Unsupported PIHU package type: {package_type}")
        state = self.read()
        package_id = str(record["id"])
        normalized = {**record, "type": package_type}
        state["packages"][package_id] = normalized
        if package_type == "mcp":
            state["servers"][package_id] = normalized
        self.write(state)

    def remove(self, package_id: str) -> Optional[Dict[str, Any]]:
        state = self.read()
        record = state["packages"].pop(package_id, None) or state["servers"].pop(package_id, None)
        state["servers"].pop(package_id, None)
        self.write(state)
        return record

    def list(self, package_type: Optional[str] = None) -> List[Dict[str, Any]]:
        records = self.read()["packages"].values()
        return [record for record in records if package_type is None or record.get("type", "mcp") == package_type]
