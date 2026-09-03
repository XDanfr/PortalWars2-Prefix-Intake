from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portalwars2_prefix_intake.core import (
    default_output_directory,
    find_portalwars2_candidates,
    public_relpath,
    resolve_prefix,
    write_intake,
)

ROOT = Path(__file__).parent / "fixtures" / "Local"


class PrefixIntakeTests(unittest.TestCase):
    def test_localappdata_discovery_ignores_unrelated_apps(self) -> None:
        candidates = find_portalwars2_candidates(ROOT)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, "PortalWars2")
        self.assertEqual(resolve_prefix(ROOT), candidates[0])

    def test_redacts_account_and_uuid_components(self) -> None:
        raw = "Saved/Cloud/Steam_12345678901234567/abcdef01-2345-6789-abcd-ef0123456789/file.sav"
        self.assertEqual(public_relpath(raw), "Saved/Cloud/Steam_<redacted>/<uuid>/file.sav")

    def test_full_hashed_intake_is_sanitised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "intake"
            summary = write_intake(resolve_prefix(ROOT), output)
            self.assertEqual(summary["files"], 6)
            self.assertEqual(summary["cache_entries"], 2)
            inventory = (output / "artifact-inventory.csv").read_text(encoding="utf-8")
            self.assertNotIn("12345678901234567", inventory)
            self.assertIn("Steam_<redacted>", inventory)
            self.assertNotIn("abcdef01-2345-6789-abcd-ef0123456789", inventory)
            with (output / "cache-manifest.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[1]["source_url"], "<redacted>")
            self.assertEqual(rows[0]["version"], "0.2.451")
            data = json.loads((output / "intake-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(data["versioned_datasets"]["playlists"], ["0.2.451"])

    def test_no_hash_leaves_hash_column_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "intake"
            write_intake(resolve_prefix(ROOT), output, calculate_hashes=False)
            with (output / "artifact-inventory.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(rows)
            self.assertTrue(all(row["sha256"] == "" for row in rows))

    def test_source_urls_can_be_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "intake"
            write_intake(resolve_prefix(ROOT), output, allow_source_urls=True)
            text = (output / "cache-manifest.csv").read_text(encoding="utf-8")
            self.assertIn("cms.example.invalid/private", text)
            self.assertNotIn("12345678901234567", text)

    def test_multiple_candidates_require_explicit_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("First", "Second"):
                target = root / name / "PortalWars2"
                target.mkdir(parents=True)
                (target / "Saved/PersistentDownloadDir").mkdir(parents=True)
                (target / "Saved/PersistentDownloadDir/CacheManifest.json").write_text('{"Entries": []}\n', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                resolve_prefix(root)

    def test_default_output_is_beside_launcher_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = default_output_directory(Path(tmp))
            self.assertEqual(output.parent, Path(tmp))
            self.assertTrue(output.name.startswith("portalwars2-intake-"))

    def test_localappdata_mode_uses_environment(self) -> None:
        from portalwars2_prefix_intake.core import main

        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "LocalAppData"
            target = local / "1047Games" / "PortalWars2"
            target.mkdir(parents=True)
            (target / "Saved/PersistentDownloadDir").mkdir(parents=True)
            (target / "Saved/PersistentDownloadDir/CacheManifest.json").write_text('{"Entries": []}\n', encoding="utf-8")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}, clear=False):
                output = Path(tmp) / "out"
                self.assertEqual(main(["--localappdata", "--output", str(output)]), 0)
                self.assertTrue((output / "intake-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
