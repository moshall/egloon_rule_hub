"""Tests for the upstream README fetch helpers."""

from unittest import TestCase
from urllib.error import HTTPError, URLError

from egloon_rule_hub.upstream_docs.fetch import derive_readme_url, fetch_readme


class TestFetchReadme(TestCase):
    RULE_URL = (
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/"
        "rule/Clash/OpenAI/OpenAI.yaml"
    )
    README_URL = (
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/"
        "rule/Clash/OpenAI/README.md"
    )
    DIRECTORY_RULE_URL = (
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/"
        "rule/Clash/OpenAI/"
    )
    DIRECTORY_README_URL = (
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/"
        "rule/Clash/OpenAI/README.md"
    )

    def test_derive_readme_url_replaces_filename(self):
        readme_url = derive_readme_url(self.RULE_URL)
        self.assertEqual(readme_url, self.README_URL)

    def test_derive_readme_url_handles_directory_path(self):
        readme_url = derive_readme_url(self.DIRECTORY_RULE_URL)
        self.assertEqual(readme_url, self.DIRECTORY_README_URL)

    def test_fetch_readme_missing_status_on_404(self):
        error = HTTPError(self.README_URL, 404, "Not Found", hdrs=None, fp=None)

        called = []

        def fetcher(url: str) -> bytes:
            called.append(url)
            raise error

        result = fetch_readme(self.RULE_URL, fetcher=fetcher)

        self.assertEqual(result.status, "missing")
        self.assertIs(result.error, error)
        self.assertEqual(result.readme_url, self.README_URL)
        self.assertIsNone(result.content)
        self.assertEqual(called, [self.README_URL])

    def test_fetch_readme_fetch_error_on_urlerror(self):
        error = URLError("temporary failure")

        called = []

        def fetcher(url: str) -> bytes:
            called.append(url)
            raise error

        result = fetch_readme(self.RULE_URL, fetcher=fetcher)

        self.assertEqual(result.status, "fetch_error")
        self.assertIs(result.error, error)
        self.assertEqual(result.readme_url, self.README_URL)
        self.assertIsNone(result.content)
        self.assertEqual(called, [self.README_URL])

    def test_fetch_readme_fetch_error_on_non_404_http_error(self):
        error = HTTPError(self.README_URL, 500, "Server Error", hdrs=None, fp=None)

        called = []

        def fetcher(url: str) -> bytes:
            called.append(url)
            raise error

        result = fetch_readme(self.RULE_URL, fetcher=fetcher)

        self.assertEqual(result.status, "fetch_error")
        self.assertIs(result.error, error)
        self.assertEqual(result.readme_url, self.README_URL)
        self.assertIsNone(result.content)
        self.assertEqual(called, [self.README_URL])

    def test_fetch_readme_success_status(self):
        called = []

        def fetcher(url: str) -> bytes:
            called.append(url)
            return b"ok"

        result = fetch_readme(self.RULE_URL, fetcher=fetcher)

        self.assertEqual(result.status, "ok")
        self.assertIsNone(result.error)
        self.assertEqual(result.readme_url, self.README_URL)
        self.assertEqual(result.content, b"ok")
        self.assertEqual(called, [self.README_URL])
