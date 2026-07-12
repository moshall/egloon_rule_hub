from __future__ import annotations

import unittest
from pathlib import Path

from egloon_rule_hub.build import build_target_artifact
from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
    ServiceTargetDef,
    SourceDef,
    SourceRef,
    TargetDef,
    load_catalog,
)


def _derived_target(name: str) -> TargetDef:
    try:
        return TargetDef(
            name=name,
            enabled=True,
            file_ext="list" if name == "surfboard" else "json",
            source_target="shadowrocket",
        )
    except TypeError as exc:
        raise AssertionError("TargetDef must support source_target") from exc


class DerivedTargetTests(unittest.TestCase):
    def test_reuses_source_target_selection_and_marks_conversion(self) -> None:
        source_ref = SourceRef(
            source="fixture",
            url="https://example.test/rules.list",
            format="shadowrocket_list",
        )
        service = ServiceDef(
            name="Example",
            enabled=True,
            targets=["surfboard", "singbox"],
            target_sources={
                "shadowrocket": ServiceTargetDef(
                    name="shadowrocket",
                    families={"native": [source_ref]},
                )
            },
        )
        catalog = Catalog(
            root=Path("."),
            sources={"fixture": SourceDef(name="fixture", kind="remote")},
            targets={
                "shadowrocket": TargetDef(
                    name="shadowrocket", enabled=True, file_ext="list"
                ),
                "surfboard": _derived_target("surfboard"),
                "singbox": _derived_target("singbox"),
            },
            services={"Example": service},
            bundles={},
        )

        artifact = build_target_artifact(
            catalog,
            "Example",
            "surfboard",
            fetcher=lambda _: "DOMAIN-SUFFIX,example.com\n",
        )

        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertEqual(artifact.target, "surfboard")
        self.assertEqual(artifact.selected_native_target, "shadowrocket")
        self.assertTrue(artifact.is_converted)
        self.assertEqual(artifact.conversion_path, "Shadowrocket -> Surfboard")
        self.assertEqual([rule.render() for rule in artifact.rules], ["DOMAIN-SUFFIX,example.com"])

    def test_repository_catalog_publishes_new_targets_everywhere(self) -> None:
        catalog = load_catalog(Path(__file__).resolve().parents[1])

        self.assertEqual(catalog.targets["surfboard"].source_target, "shadowrocket")
        self.assertEqual(catalog.targets["singbox"].source_target, "shadowrocket")
        for service in catalog.services.values():
            self.assertIn("surfboard", service.targets, service.name)
            self.assertIn("singbox", service.targets, service.name)
        for bundle in catalog.bundles.values():
            self.assertIn("surfboard", bundle.targets, bundle.name)
            self.assertIn("singbox", bundle.targets, bundle.name)


if __name__ == "__main__":
    unittest.main()
