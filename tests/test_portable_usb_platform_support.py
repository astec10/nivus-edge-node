from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from deploy.portable_usb.platform_support import identify_supported_platform, read_os_release


class PortableUsbPlatformSupportTests(unittest.TestCase):
    def test_accepts_supported_ubuntu_server_releases(self) -> None:
        for version in ("24.04", "24.10", "26.04"):
            with self.subTest(version=version):
                result = identify_supported_platform({"ID": "ubuntu", "VERSION_ID": version})
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result.distro_id, "ubuntu")

    def test_rejects_older_ubuntu_and_unlisted_derivatives(self) -> None:
        self.assertIsNone(identify_supported_platform({"ID": "ubuntu", "VERSION_ID": "22.04"}))
        self.assertIsNone(identify_supported_platform({"ID": "linuxmint", "VERSION_ID": "22"}))
        self.assertIsNone(identify_supported_platform({"ID": "pop", "VERSION_ID": "24.04"}))

    def test_accepts_only_debian_13_trixie(self) -> None:
        self.assertIsNotNone(
            identify_supported_platform(
                {"ID": "debian", "VERSION_ID": "13", "VERSION_CODENAME": "trixie"}
            )
        )
        self.assertIsNone(
            identify_supported_platform(
                {"ID": "debian", "VERSION_ID": "12", "VERSION_CODENAME": "bookworm"}
            )
        )
        self.assertIsNone(
            identify_supported_platform(
                {"ID": "debian", "VERSION_ID": "13", "VERSION_CODENAME": "forky"}
            )
        )

    def test_reads_quoted_os_release_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "os-release"
            path.write_text(
                'ID=debian\nVERSION_ID="13"\nVERSION_CODENAME=trixie\nPRETTY_NAME="Debian GNU/Linux 13 (trixie)"\n',
                encoding="utf-8",
            )
            self.assertEqual(read_os_release(path)["PRETTY_NAME"], "Debian GNU/Linux 13 (trixie)")


if __name__ == "__main__":
    unittest.main()
