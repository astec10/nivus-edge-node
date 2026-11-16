from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy.portable_usb.select_target import (  # noqa: E402
    InspectionError,
    _write_selection,
    eligible_usb_disks,
    select_candidate,
)


GIB = 1024**3


def disk(
    name: str,
    *,
    serial: str,
    model: str = "Nivus Test USB",
    transport: str = "usb",
    size: int = 64 * GIB,
    read_only: int = 0,
    mountpoints: list[str | None] | None = None,
    child_mountpoints: list[str | None] | None = None,
) -> dict:
    return {
        "name": name,
        "path": f"/dev/{name}",
        "type": "disk",
        "size": size,
        "model": model,
        "serial": serial,
        "tran": transport,
        "ro": read_only,
        "mountpoints": mountpoints or [None],
        "children": [
            {
                "name": f"{name}1",
                "path": f"/dev/{name}1",
                "type": "part",
                "size": size - 1024 * 1024,
                "model": None,
                "serial": None,
                "tran": None,
                "ro": read_only,
                "mountpoints": child_mountpoints or [None],
            }
        ],
    }


def inventory(*devices: dict) -> dict:
    return {"blockdevices": list(devices)}


class PortableUsbTargetTests(unittest.TestCase):
    def test_lists_all_eligible_usb_disks_without_size_based_selection(self) -> None:
        small = disk("sdb", serial="USB-A", size=32 * GIB)
        large = disk("sdc", serial="USB-B", size=128 * GIB)

        found = eligible_usb_disks(inventory(large, small))

        self.assertEqual([item["serial"] for item in found], ["USB-A", "USB-B"])
        self.assertEqual(select_candidate(found, "USB-A")["path"], "/dev/sdb")
        self.assertEqual(select_candidate(found, "USB-B")["path"], "/dev/sdc")

    def test_requires_exactly_one_explicit_serial(self) -> None:
        found = eligible_usb_disks(inventory(disk("sdb", serial="USB-A")))

        with self.assertRaises(InspectionError):
            select_candidate(found, "")
        with self.assertRaises(InspectionError):
            select_candidate(found, "unknown")

    def test_excludes_non_usb_and_read_only_disks(self) -> None:
        sata = disk("sda", serial="INTERNAL", transport="sata")
        read_only = disk("sdb", serial="READONLY", read_only=1)

        self.assertEqual(eligible_usb_disks(inventory(sata, read_only)), [])

    def test_excludes_disk_with_any_mounted_partition(self) -> None:
        mounted = disk("sdb", serial="MOUNTED", child_mountpoints=["/cdrom"])

        self.assertEqual(eligible_usb_disks(inventory(mounted)), [])

    def test_excludes_disk_containing_current_root(self) -> None:
        host_usb = disk("sdb", serial="HOST-ROOT")

        self.assertEqual(
            eligible_usb_disks(inventory(host_usb), protected_paths={"/dev/sdb"}),
            [],
        )

    def test_excludes_missing_or_duplicate_serial_and_missing_model(self) -> None:
        duplicate_a = disk("sdb", serial="DUPLICATE")
        duplicate_b = disk("sdc", serial="DUPLICATE")
        no_serial = disk("sdd", serial="")
        no_model = disk("sde", serial="NO-MODEL", model="")

        self.assertEqual(
            eligible_usb_disks(inventory(duplicate_a, duplicate_b, no_serial, no_model)),
            [],
        )

    def test_selection_manifest_is_private_and_never_overwritten(self) -> None:
        target = eligible_usb_disks(inventory(disk("sdb", serial="USB-A")))[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "selection.json"
            _write_selection(output, target)
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["schema"], "nivus-portable-usb-selection-v1")
            self.assertEqual(record["device"]["serial"], "USB-A")
            self.assertIn("identity_sha256", record)
            if os.name == "posix":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)

            with self.assertRaises(InspectionError):
                _write_selection(output, target)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), record)


if __name__ == "__main__":
    unittest.main()
