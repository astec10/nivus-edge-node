from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy.portable_usb.generate_autoinstall import (  # noqa: E402
    MINIMUM_DISK_BYTES,
    GenerationError,
    build_autoinstall_user_data,
    build_seed_iso,
    early_validation_code,
    validate_account,
    validate_selection,
    write_seed,
)
from deploy.portable_usb.select_target import _identity_digest  # noqa: E402


GIB = 1024**3


def usb_disk(
    *,
    path: str = "/dev/sdb",
    name: str = "sdb",
    serial: str = "NVUSB-001",
    model: str = "Nivus Installer USB",
    size: int = 64 * GIB,
    transport: str = "usb",
    read_only: int = 0,
    mounted: str | None = None,
) -> dict:
    return {
        "path": path,
        "name": name,
        "type": "disk",
        "size": size,
        "model": model,
        "serial": serial,
        "tran": transport,
        "ro": read_only,
        "mountpoints": [mounted],
        "children": [
            {
                "path": path + "1",
                "name": name + "1",
                "type": "part",
                "size": size - 1024 * 1024,
                "model": None,
                "serial": None,
                "tran": None,
                "ro": read_only,
                "mountpoints": [None],
            }
        ],
    }


def selection_record(device: dict) -> dict:
    identity = {
        "path": device["path"],
        "name": device["name"],
        "model": device["model"],
        "serial": device["serial"],
        "size_bytes": device["size"],
        "transport": device["tran"],
    }
    return {
        "schema": "nivus-portable-usb-selection-v1",
        "device": identity,
        "identity_sha256": _identity_digest(identity),
    }


def inventory(*devices: dict) -> dict:
    return {"blockdevices": list(devices)}


class PortableUsbAutoinstallTests(unittest.TestCase):
    def test_revalidates_manifest_against_exact_live_device(self) -> None:
        disk = usb_disk(size=64 * GIB)
        record = selection_record(disk)

        selected = validate_selection(record, inventory(disk))

        self.assertEqual(selected["serial"], "NVUSB-001")
        self.assertEqual(selected["path"], "/dev/sdb")

    def test_rejects_changed_path_model_capacity_and_duplicate_serial(self) -> None:
        disk = usb_disk(size=64 * GIB)
        record = selection_record(disk)
        changed_path = usb_disk(path="/dev/sdc", name="sdc", size=64 * GIB)
        changed_model = usb_disk(model="Different USB", size=64 * GIB)
        changed_size = usb_disk(size=65 * GIB)
        duplicate_serial = usb_disk(path="/dev/sdc", name="sdc", size=64 * GIB)

        for changed in (changed_path, changed_model, changed_size):
            with self.subTest(changed=changed):
                with self.assertRaises(GenerationError):
                    validate_selection(record, inventory(changed))
        with self.assertRaises(GenerationError):
            validate_selection(record, inventory(disk, duplicate_serial))

    def test_rejects_small_read_only_or_mounted_usb(self) -> None:
        record = selection_record(usb_disk(size=64 * GIB))
        for invalid in (
            usb_disk(size=MINIMUM_DISK_BYTES - 1),
            usb_disk(read_only=1),
            usb_disk(mounted="/media/usb"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(GenerationError):
                    validate_selection(record, inventory(invalid))

    def test_rejects_modified_manifest_digest(self) -> None:
        disk = usb_disk(size=64 * GIB)
        record = selection_record(disk)
        record["device"]["serial"] = "OTHER"
        with self.assertRaises(GenerationError):
            validate_selection(record, inventory(disk))

    def test_user_data_targets_serial_and_has_persistent_data_partition(self) -> None:
        device = selection_record(usb_disk(size=64 * GIB))["device"]
        user_data = build_autoinstall_user_data(
            device, "nivus", "nivus-node", "$6$test-salt$test-hash"
        )

        self.assertTrue(user_data.startswith("#cloud-config\n"))
        body = user_data.split("\n", 2)[2]
        config = json.loads(body)["autoinstall"]
        self.assertEqual(config["interactive-sections"], ["storage"])
        self.assertEqual(config["identity"]["username"], "nivus")
        storage = config["storage"]["config"]
        target = next(item for item in storage if item.get("id") == "nivus-usb")
        self.assertEqual(target["serial"], device["serial"])
        self.assertEqual(target["model"], device["model"])
        self.assertNotIn("match", target)
        self.assertNotIn("size", target)

        data_partition = next(item for item in storage if item.get("id") == "nivus-data-partition")
        data_format = next(item for item in storage if item.get("id") == "nivus-data-format")
        data_mount = next(item for item in storage if item.get("id") == "nivus-data-mount")
        self.assertEqual(data_partition["size"], -1)
        self.assertEqual(data_format["fstype"], "ext4")
        self.assertEqual(data_format["label"], "NIVUS_DATA")
        self.assertEqual(data_mount["path"], "/var/lib/nivus")
        self.assertIn("early-commands", config)

    def test_storage_early_check_accepts_matching_usb_and_rejects_path_drift(self) -> None:
        disk = usb_disk(size=64 * GIB)
        payload = json.dumps(inventory(disk))
        result = subprocess.CompletedProcess([], 0, stdout=payload, stderr="")
        args = ["-c", disk["path"], disk["model"], disk["serial"], str(disk["size"])]

        with mock.patch("subprocess.run", return_value=result), mock.patch.object(sys, "argv", args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(early_validation_code(), "<early-check>", "exec"), {})
        self.assertIn("identity revalidated", output.getvalue())

        bad_args = ["-c", "/dev/sdc", disk["model"], disk["serial"], str(disk["size"])]
        with mock.patch("subprocess.run", return_value=result), mock.patch.object(sys, "argv", bad_args):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    exec(compile(early_validation_code(), "<early-check>", "exec"), {})
        self.assertEqual(raised.exception.code, 2)

    def test_storage_early_check_rejects_mounted_usb(self) -> None:
        disk = usb_disk(size=64 * GIB)
        disk["children"][0]["mountpoints"] = ["/cdrom"]
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps(inventory(disk)), stderr="")
        args = ["-c", disk["path"], disk["model"], disk["serial"], str(disk["size"])]

        with mock.patch("subprocess.run", return_value=result), mock.patch.object(sys, "argv", args):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    exec(compile(early_validation_code(), "<early-check>", "exec"), {})
        self.assertEqual(raised.exception.code, 2)

    def test_account_validation_and_password_hash_requirements(self) -> None:
        validate_account("nivus", "nivus-node")
        with self.assertRaises(GenerationError):
            validate_account("Admin", "nivus-node")
        with self.assertRaises(GenerationError):
            build_autoinstall_user_data(
                selection_record(usb_disk(size=64 * GIB))["device"],
                "nivus",
                "nivus-node",
                "plaintext-password",
            )

    def test_seed_iso_is_private_and_has_checksum_without_overwrite(self) -> None:
        device = selection_record(usb_disk(size=64 * GIB))["device"]
        user_data = build_autoinstall_user_data(
            device, "nivus", "nivus-node", "$6$test-salt$test-hash"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_dir = Path(temp_dir) / "seed"
            seed_dir.mkdir(mode=0o700)
            (seed_dir / "user-data").write_text(user_data, encoding="utf-8")
            (seed_dir / "meta-data").write_text("instance-id: test\\n", encoding="utf-8")

            def fake_cloud_localds(command, **kwargs):
                Path(command[2]).write_bytes(b"synthetic-no-cloud-iso")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with mock.patch(
                "deploy.portable_usb.generate_autoinstall.shutil.which",
                return_value="/usr/bin/cloud-localds",
            ), mock.patch(
                "deploy.portable_usb.generate_autoinstall.subprocess.run",
                side_effect=fake_cloud_localds,
            ) as run:
                iso_path = build_seed_iso(seed_dir)

            self.assertEqual(iso_path.name, "nivus-autoinstall-seed.iso")
            self.assertEqual(iso_path.read_bytes(), b"synthetic-no-cloud-iso")
            self.assertEqual(iso_path.stat().st_mode & 0o777, 0o600)
            checksum = iso_path.with_suffix(iso_path.suffix + ".sha256")
            self.assertEqual(\n                checksum.read_text(encoding="utf-8").splitlines(),\n                [f"{hashlib.sha256(iso_path.read_bytes()).hexdigest()}  {iso_path.name}"],\n            )
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][1], "--filesystem=iso")

            with mock.patch(
                "deploy.portable_usb.generate_autoinstall.shutil.which",
                return_value="/usr/bin/cloud-localds",
            ), mock.patch(
                "deploy.portable_usb.generate_autoinstall.subprocess.run",
            ) as run_again:
                with self.assertRaises(GenerationError):
                    build_seed_iso(seed_dir)
                run_again.assert_not_called()

    def test_seed_iso_requires_cloud_localds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_dir = Path(temp_dir)
            with mock.patch(
                "deploy.portable_usb.generate_autoinstall.shutil.which",
                return_value=None,
            ):
                with self.assertRaises(GenerationError):
                    build_seed_iso(seed_dir)

    def test_seed_is_private_and_never_overwrites_existing_directory(self) -> None:
        device = selection_record(usb_disk(size=64 * GIB))["device"]
        user_data = build_autoinstall_user_data(
            device, "nivus", "nivus-node", "$6$test-salt$test-hash"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "seed"
            write_seed(output, user_data, device)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertEqual((output / "user-data").stat().st_mode & 0o777, 0o600)
            self.assertTrue((output / "meta-data").is_file())
            self.assertTrue((output / "TARGET-IDENTITY.txt").is_file())
            checksums = (output / "SHA256SUMS").read_text(encoding="utf-8")
            expected = hashlib.sha256((output / "user-data").read_bytes()).hexdigest()
            self.assertIn(expected, checksums)
            original = (output / "user-data").read_bytes()
            with self.assertRaises(GenerationError):
                write_seed(output, "replacement", device)
            self.assertEqual((output / "user-data").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
