from __future__ import annotations

import hashlib
import os
import re
import time
import urllib.parse
import httpx

from web_search_mcp.models import FileDownloadResponse


class FileDownloader:
    """Asynchronous file downloader for web-search MCP server."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def download(
        self,
        url: str,
        save_path: str | None = None,
        max_bytes: int = 50_000_000,
    ) -> FileDownloadResponse:
        started = time.perf_counter()

        # Determine filename and target path
        parsed = urllib.parse.urlparse(url)
        raw_filename = os.path.basename(parsed.path) or "downloaded_file"
        raw_filename = re.sub(r'[^\w\.\-]', '_', raw_filename)
        if not raw_filename or raw_filename == "_":
            raw_filename = "downloaded_file"

        if not save_path:
            target_dir = os.path.abspath("downloads")
            os.makedirs(target_dir, exist_ok=True)
            target_file = os.path.join(target_dir, raw_filename)
        else:
            target_file = os.path.abspath(save_path)
            os.makedirs(os.path.dirname(target_file) or ".", exist_ok=True)

        try:
            resp = await self.client.get(url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()

            # Refine filename from Content-Disposition header if present
            cd = resp.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                fname_match = re.search(r'filename=["\']?([^"\';]+)["\']?', cd)
                if fname_match:
                    clean_fname = re.sub(r'[^\w\.\-]', '_', fname_match.group(1))
                    if clean_fname:
                        if not save_path:
                            target_file = os.path.join(os.path.dirname(target_file), clean_fname)

            content = resp.content
            if len(content) > max_bytes:
                content = content[:max_bytes]

            with open(target_file, "wb") as f:
                f.write(content)

            size_bytes = len(content)
            size_human = (
                f"{round(size_bytes / 1024 / 1024, 2)} MB"
                if size_bytes > 1024 * 1024
                else f"{round(size_bytes / 1024, 1)} KB"
            )
            sha256 = hashlib.sha256(content).hexdigest()
            content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0]

            return FileDownloadResponse(
                url=str(resp.url),
                save_path=target_file,
                filename=os.path.basename(target_file),
                size_bytes=size_bytes,
                size_human=size_human,
                content_type=content_type,
                sha256_hash=sha256,
                status="success",
                took_ms=round((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            return FileDownloadResponse(
                url=url,
                save_path=target_file,
                filename=raw_filename,
                size_bytes=0,
                size_human="0 KB",
                content_type="unknown",
                sha256_hash="",
                status="error",
                message=str(exc),
                took_ms=round((time.perf_counter() - started) * 1000),
            )
