from __future__ import annotations

import unittest

from egloon_rule_hub.model.catalog import SourceDef, SourceRef
from egloon_rule_hub.sources.registry import resolve_source_ref


class SourceRegistryTests(unittest.TestCase):
    def test_resolve_known_source_kind(self) -> None:
        source_def = SourceDef(
            name="acl4ssr",
            kind="acl4ssr_repo",
            repo="ACL4SSR/ACL4SSR",
            branch="master",
            base_raw_url="https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master",
        )
        source_ref = SourceRef(
            source="acl4ssr",
            path="Clash/Ruleset/OpenAi.list",
            format="clash_list",
            priority=80,
        )

        resolved = resolve_source_ref(source_def, source_ref)
        self.assertEqual(
            resolved.url,
            "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/OpenAi.list",
        )
        self.assertEqual(resolved.format, "clash_list")

    def test_unknown_source_kind_raises(self) -> None:
        source_def = SourceDef(name="bad", kind="unknown_kind")
        source_ref = SourceRef(source="bad", url="https://example.com/rules.list")

        with self.assertRaises(ValueError):
            resolve_source_ref(source_def, source_ref)


if __name__ == "__main__":
    unittest.main()

