"""Tests for Windows EXE/MSIX packaging helpers, asset dimensions, and manifest XML."""

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

from installers.windows.build_windows import (
    PACKAGING_WIN_DIR,
    _read_project_version,
    _to_four_part_version,
)
from installers.windows.generate_assets import generate_windows_assets

from password_generator import __version__


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def test_version_parsing_matches_package() -> None:
    assert _read_project_version() == __version__
    assert _to_four_part_version("2.0.0") == (2, 0, 0, 0)
    assert _to_four_part_version("v2.3.4") == (2, 3, 4, 0)
    assert _to_four_part_version("2.1.0.7") == (2, 1, 0, 7)


def test_generate_windows_assets_creates_valid_ico_and_msix_pngs(tmp_path: Path) -> None:
    out_dir = generate_windows_assets(tmp_path / "assets")
    ico_bytes = (out_dir / "AegisKey.ico").read_bytes()
    reserved, ico_type, count = struct.unpack("<HHH", ico_bytes[:6])
    assert reserved == 0
    assert ico_type == 1
    assert count == 7

    msix_dir = out_dir / "msix_assets"
    expected_sizes = {
        "StoreLogo.png": (50, 50),
        "Square44x44Logo.png": (44, 44),
        "Square44x44Logo.scale-200.png": (88, 88),
        "Square150x150Logo.png": (150, 150),
        "Square150x150Logo.scale-200.png": (300, 300),
        "Wide310x150Logo.png": (310, 150),
    }
    for filename, dims in expected_sizes.items():
        assert _png_dimensions(msix_dir / filename) == dims


def test_appx_manifest_template_renders_valid_xml() -> None:
    template = (PACKAGING_WIN_DIR / "AppxManifest.xml.template").read_text(encoding="utf-8")
    rendered = template.format(
        PACKAGE_NAME="AegisKey.PasswordStudio",
        PUBLISHER="CN=AegisKey Test Publisher",
        VERSION="2.0.0.0",
        DISPLAY_NAME="AegisKey Password Studio",
        PUBLISHER_DISPLAY_NAME="AegisKey Contributors",
    )
    root = ET.fromstring(rendered)  # noqa: S314 - static local repository template
    assert root.tag.endswith("Package")
