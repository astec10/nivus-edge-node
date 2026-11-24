"""Synthetic tests for the Nivus package builder and manifest verifier."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from deploy.portable_usb.create_bundle import BundleError, build_bundle, verify_bundle


REQUIRED_FILES = (
    "docker-compose.yml",
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "deploy/install.sh",
    "deploy/nivus-node-agent.service.example",
    "deploy/portable_usb/configure_runtime.py",
    "deploy/portable_usb/platform_support.py",
    "deploy/portable_usb/install_nivus.sh",
    "deploy/portable_usb/bundle_manifest.schema.json",
    "deploy/live-usb/nivus-data-volume-guard",
    "node_agent/agent.py",
)


def create_clean_source(root: Path) -> None:
    for relative in REQUIRED_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"synthetic {relative}\n", encoding="utf-8")
    (root / ".env.example").write_text("PUBLIC_EXAMPLE=1\n", encoding="utf-8")
    (root / "README.md").write_text("synthetic top-level readme\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "bundle-tests@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Bundle Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "synthetic installer source"], cwd=root, check=True)


class BundleBuilderTests(unittest.TestCase):
    def test_builds_verifiable_package_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            create_clean_source(source)
            output = root / "artifacts"

            bundle, archive, checksum = build_bundle(source, output, "0.1.0-test")

            self.assertEqual(verify_bundle(bundle), len(json.loads((bundle / "bundle_manifest.json").read_text())["files"]))
            self.assertTrue(archive.is_file())
            self.assertRegex(checksum.read_text(encoding="ascii"), r"^[a-f0-9]{64}  .+\.tar\.gz\n$")
            expected_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(checksum.read_text(encoding="ascii").split()[0], expected_hash)
            with tarfile.open(archive, mode="r:gz") as packaged:
                self.assertTrue(
                    all(
                        not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
                        for member in packaged
                    )
                )
            self.assertFalse((bundle / "payload/.env.example").exists())

    def test_detects_modified_and_unlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            create_clean_source(source)
            bundle, _archive, _checksum = build_bundle(source, root / "artifacts", "0.1.0")
            tracked = bundle / "payload/node_agent/agent.py"
            tracked.write_text("modified\n", encoding="utf-8")
            with self.assertRaisesRegex(BundleError, "integridade não confere"):
                verify_bundle(bundle)

            tracked.write_text("synthetic node_agent/agent.py\n", encoding="utf-8")
            (bundle / "unexpected.txt").write_text("not listed\n", encoding="utf-8")
            with self.assertRaisesRegex(BundleError, "diverge do manifesto"):
                verify_bundle(bundle)

    def test_refuses_dirty_source_and_sensitive_tracked_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            create_clean_source(source)
            (source / "README.md").write_text("uncommitted\n", encoding="utf-8")
            with self.assertRaisesRegex(BundleError, "precisa estar limpa"):
                build_bundle(source, root / "dirty-output", "0.1.0")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            create_clean_source(source)
            (source / "private.key").write_text("synthetic key\n", encoding="utf-8")
            subprocess.run(["git", "add", "private.key"], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "synthetic key fixture"], cwd=source, check=True)
            with self.assertRaisesRegex(BundleError, "arquivo sensível versionado"):
                build_bundle(source, root / "sensitive-output", "0.1.0")

    def test_rejects_output_inside_source_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            create_clean_source(source)
            with self.assertRaisesRegex(BundleError, "fora do repositório"):
                build_bundle(source, source / "dist", "0.1.0")
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(BundleError, "já existe"):
                build_bundle(source, existing, "0.1.0")


if __name__ == "__main__":
    unittest.main()
