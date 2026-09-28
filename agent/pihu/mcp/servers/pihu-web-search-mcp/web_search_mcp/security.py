from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    pass


def validate_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("Only http:// and https:// URLs are allowed.")

    if not parsed.hostname:
        raise UnsafeURL("URL has no hostname.")

    if parsed.username or parsed.password:
        raise UnsafeURL("URLs containing credentials are not allowed.")


async def assert_public_host(hostname: str) -> None:
    try:
        ip = ipaddress.ip_address(hostname)
        _assert_public_ip(ip)
        return
    except ValueError:
        pass

    try:
        infos = await asyncio.get_running_loop().run_in_executor(
            None, lambda: socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        )
    except socket.gaierror as exc:
        raise UnsafeURL(f"Unable to resolve host: {hostname}") from exc

    addresses = {item[4][0] for item in infos}
    if not addresses:
        raise UnsafeURL(f"Unable to resolve host: {hostname}")

    for address in addresses:
        _assert_public_ip(ipaddress.ip_address(address))


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if not ip.is_global:
        raise UnsafeURL(f"Host resolves to a non-public address: {ip}")


async def validate_and_resolve(url: str) -> str:
    validate_url(url)
    host = urlparse(url).hostname
    assert host is not None
    await assert_public_host(host)
    return url
