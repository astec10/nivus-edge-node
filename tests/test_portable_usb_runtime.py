from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy.portable_usb.configure_runtime import (  # noqa: E402
    DATA_MOUNT,
    LINKS,
    MountRecord,
    BlockRecord,
    RuntimeSetupError,
    UNIT_FILES,
    configure_persistent_paths,
    validate_storage_layout,
)


def valid_records():
    root = MountRecord("/dev/sdb3", "ext4", "/", "rw,relatime")
    data = MountRecord("/dev/sdb4", "ext4", DATA_MOUNT, "rw,relatime")
    fstab = [MountRecord("/dev/sdb4", "ext4", DATA_MOUNT)]
    root_block = BlockRecord("part", "sdb", "usb")
    data_block = BlockRecord("part", "sdb", "usb")
    return root, data, fstab, root_block, data_block


class PortableUsbRuntimeTests(unittest.TestCase):
    def test_accepts_installed_ubuntu_and_data_partitions_on_same_usb(self) -> None:
        validate_storage_layout(*valid_records(), "NIVUS_DATA", ["/dev/sdb4"])

    def test_rejects_data_partition_on_internal_or_different_disk(self) -> None:
        root, data, fstab, root_block, _ = valid_records()
        for invalid in (
            BlockRecord("part", "sda", "sata"),
            BlockRecord("part", "sdc", "usb"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(RuntimeSetupError):
                    validate_storage_layout(
                        root, data, fstab, root_block, invalid, "NIVUS_DATA", ["/dev/sdb4"]
                    )

    def test_rejects_read_only_mount_wrong_label_duplicate_label_and_nonpersistent_fstab(self) -> None:
        root, data, fstab, root_block, data_block = valid_records()
        invalid_cases = (
            (root, MountRecord(data.source, "ext4", DATA_MOUNT, "ro,relatime"), fstab, "NIVUS_DATA", [data.source]),
            (root, data, fstab, "OTHER", [data.source]),
            (root, data, fstab, "NIVUS_DATA", [data.source, "/dev/sdc4"]),
            (root, data, [], "NIVUS_DATA", [data.source]),
        )
        for root_record, data_record, fstab_records, label, label_sources in invalid_cases:
            with self.subTest(label=label, fstab=fstab_records):
                with self.assertRaises(RuntimeSetupError):
                    validate_storage_layout(
                        root_record, data_record, fstab_records,
                        root_block, data_block, label, label_sources
                    )

    def _source_tree(self, repository: Path) -> None:
        for relative, _destination, _mode in UNIT_FILES:
            source = repository / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"fixture: {relative}\n", encoding="utf-8")

    def test_configures_persistent_layout_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            repository = Path(temp) / "repo"
            data_root = root / "var/lib/nivus"
            data_root.mkdir(parents=True)
            (data_root / "lost+found").mkdir()
            self._source_tree(repository)

            configure_persistent_paths(repository, root)
            configure_persistent_paths(repository, root)

            self.assertEqual(
                (data_root / ".nivus-data-volume").read_text(encoding="utf-8").strip(),
                "nivus-data-volume-v1",
            )
            for name in ("compose", "config", "releases", "docker"):
                self.assertTrue((data_root / name).is_dir())
            for link, target in LINKS.items():
                self.assertTrue((root / link.lstrip("/")).is_symlink())
                self.assertEqual((root / link.lstrip("/")).readlink().as_posix(), target)
            self.assertTrue((root / "usr/local/libexec/nivus-data-volume-guard").stat().st_mode & 0o111)
            self.assertTrue((root / "etc/systemd/system/var-lib-nivus.mount").is_file())

    def test_refuses_unmarked_nonempty_data_without_creating_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            repository = Path(temp) / "repo"
            data_root = root / "var/lib/nivus"
            data_root.mkdir(parents=True)
            (data_root / "existing.db").write_text("keep", encoding="utf-8")
            self._source_tree(repository)

            with self.assertRaisesRegex(RuntimeSetupError, "volume não vazio"):
                configure_persistent_paths(repository, root)

            self.assertEqual((data_root / "existing.db").read_text(encoding="utf-8"), "keep")
            self.assertFalse((root / "var/lib/nivus-compose").exists())
            self.assertFalse((data_root / ".nivus-data-volume").exists())

    def test_refuses_conflicting_populated_destination_before_mutating_volume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            repository = Path(temp) / "repo"
            data_root = root / "var/lib/nivus"
            data_root.mkdir(parents=True)
            (data_root / "lost+found").mkdir()
            conflicting = root / "opt/nivus-compose"
            conflicting.mkdir(parents=True)
            (conflicting / "keep").write_text("preserve", encoding="utf-8")
            self._source_tree(repository)

            with self.assertRaisesRegex(RuntimeSetupError, "não está vazio"):
                configure_persistent_paths(repository, root)

            self.assertTrue((conflicting / "keep").is_file())
            self.assertFalse((data_root / ".nivus-data-volume").exists())


if __name__ == "__main__":
    unittest.main()
