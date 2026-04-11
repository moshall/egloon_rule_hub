"""Fetch helpers for upstream docs."""

from dataclasses import dataclass
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from urllib.parse import urlparse, urlunparse
import posixpath


ReadmeFetcher = Callable[[str], bytes]


@dataclass
class ReadmeFetchResult:
    rule_url: str
    readme_url: str
    status: str
    content: Optional[bytes] = None
    error: Optional[Exception] = None


def derive_readme_url(rule_url: str) -> str:
    """Derive the README.md URL from a resolved upstream rule URL."""
    parsed = urlparse(rule_url)
    path = parsed.path or "/"
    if path.endswith("/"):
        directory = path
    else:
        directory = posixpath.dirname(path)
        if not directory:
            directory = "/"
        if not directory.endswith("/"):
            directory = f"{directory}/"
    readme_path = posixpath.join(directory, "README.md")
    if not readme_path.startswith("/"):
        readme_path = f"/{readme_path}"
    return urlunparse(parsed._replace(path=readme_path))


def _default_fetcher(url: str) -> bytes:
    with urlopen(url, timeout=10) as response:
        return response.read()


def fetch_readme(
    rule_url: str, fetcher: Optional[ReadmeFetcher] = None
) -> ReadmeFetchResult:
    """Fetch README for a resolved upstream rule URL."""
    readme_url = derive_readme_url(rule_url)
    fetcher = fetcher or _default_fetcher
    try:
        content = fetcher(readme_url)
    except HTTPError as exc:
        status = "missing" if exc.code == 404 else "fetch_error"
        return ReadmeFetchResult(
            rule_url=rule_url,
            readme_url=readme_url,
            status=status,
            error=exc,
        )
    except URLError as exc:
        return ReadmeFetchResult(
            rule_url=rule_url,
            readme_url=readme_url,
            status="fetch_error",
            error=exc,
        )
    except Exception as exc:
        return ReadmeFetchResult(
            rule_url=rule_url,
            readme_url=readme_url,
            status="fetch_error",
            error=exc,
        )
    return ReadmeFetchResult(
        rule_url=rule_url,
        readme_url=readme_url,
        status="ok",
        content=content,
    )
