import pytest

from web_search_mcp.security import UnsafeURL, validate_url


def test_only_http_https():
    validate_url("https://example.com")
    validate_url("http://example.com")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/a",
        "javascript:alert(1)",
        "https://user:pass@example.com/",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURL):
        validate_url(url)
