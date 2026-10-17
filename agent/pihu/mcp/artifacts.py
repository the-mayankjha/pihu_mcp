"""Download one immutable, compatible MCP artifact and verify it before extraction."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import urllib.parse
import urllib.request
import zipfile

MAX_DOWNLOAD = 1024 * 1024 * 1024
MAX_EXPANDED = 3 * MAX_DOWNLOAD

def host_target():
    system = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system(), platform.system().lower())
    architecture = {"x86_64": "x64", "AMD64": "x64", "aarch64": "arm64"}.get(platform.machine(), platform.machine().lower())
    return system, architecture

def select_artifact(manifest):
    system, architecture = host_target()
    systems = manifest.compatibility.get("operating_systems", [])
    architectures = manifest.compatibility.get("architectures", [])
    if systems and system not in systems: raise ValueError(f"{manifest.id} does not support {system}")
    if architectures and architecture not in architectures: raise ValueError(f"{manifest.id} does not support {architecture}")
    aliases = {"darwin": "macos", "win32": "windows", "x86_64": "x64", "amd64": "x64", "aarch64": "arm64"}
    matches = []
    for artifact in manifest.artifacts:
        os_name = aliases.get(artifact.get("platform"), artifact.get("platform"))
        cpu = aliases.get(artifact.get("architecture"), artifact.get("architecture"))
        if os_name in (system, "any", "all") and cpu in (architecture, "any", "all"):
            matches.append((int(os_name == system) + int(cpu == architecture), artifact))
    if not matches: raise ValueError(f"No downloadable artifact for {system}/{architecture}")
    return max(matches, key=lambda item: item[0])[1]

def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Package downloads must use HTTPS without embedded credentials")
    if parsed.hostname in ("localhost", "localhost.localdomain"):
        raise ValueError("Local package download hosts are not allowed")
    import ipaddress
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return url
    if not address.is_global: raise ValueError("Package download addresses must be public")
    return url

class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        validate_url(new_url)
        return super().redirect_request(request, fp, code, message, headers, new_url)

def download_and_extract(manifest, target: Path, progress=None):
    artifact = select_artifact(manifest)
    checksum = artifact.get("sha256", "")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", checksum): raise ValueError("Artifact SHA-256 is required")
    expected = artifact.get("size_bytes")
    if expected is not None and (not isinstance(expected, int) or expected <= 0 or expected > MAX_DOWNLOAD): raise ValueError("Invalid artifact size")
    archive = target / ".download"
    digest = hashlib.sha256()
    count = 0
    request = urllib.request.Request(validate_url(artifact["url"]), headers={"User-Agent": "PIHU-Market/3"})
    opener = urllib.request.build_opener(Redirects())
    try:
        with opener.open(request, timeout=60) as response, archive.open("wb") as output:
            while chunk := response.read(256 * 1024):
                count += len(chunk)
                if count > MAX_DOWNLOAD or (expected and count > expected): raise ValueError("Package exceeds its download size limit")
                digest.update(chunk)
                output.write(chunk)
                if progress: progress(count, expected)
        if expected is not None and count != expected: raise ValueError("Incomplete package download")
        if digest.hexdigest() != checksum.lower(): raise ValueError("Package checksum mismatch; no code was installed")
        if artifact.get("format", "zip") == "binary":
            destination = target / "server"
            archive.rename(destination)
            destination.chmod(0o755)
            return artifact
        with zipfile.ZipFile(archive) as payload:
            entries = payload.infolist()
            if len(entries) > 30000 or sum(entry.file_size for entry in entries) > MAX_EXPANDED: raise ValueError("Package exceeds extraction limits")
            seen = set()
            for entry in entries:
                path = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in entry.filename or ":" in entry.filename or stat.S_ISLNK(mode) or path.parts[0] in (".download", ".venv")):
                    raise ValueError("Unsafe path or symlink in package")
                key = entry.filename.rstrip("/").casefold()
                if key in seen: raise ValueError("Duplicate package path")
                seen.add(key)
                if entry.is_dir(): continue
                destination = target.joinpath(*path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with payload.open(entry) as source, destination.open("wb") as output:
                    import shutil
                    shutil.copyfileobj(source, output)
                destination.chmod(0o755 if mode & 0o111 else 0o644)
        embedded = json.loads((target / "manifest.json").read_text())
        if embedded.get("id") != manifest.id or embedded.get("version") != manifest.version:
            raise ValueError("Package identity does not match the registry")
        return artifact
    finally:
        archive.unlink(missing_ok=True)
