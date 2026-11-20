"""Build Windows Portable EXE, Inno Setup Installer EXE, and signed MSIX bundles."""

import argparse
import base64
import ctypes
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from installers.windows.generate_assets import generate_windows_assets

ROOT_DIR = Path(__file__).resolve().parents[2]
PACKAGING_WIN_DIR = ROOT_DIR / "installers" / "windows"
BUILD_WIN_DIR = ROOT_DIR / "build" / "windows"
DIST_WIN_DIR = ROOT_DIR / "dist" / "windows"

_DEFAULT_SELF_SIGN_SUBJECT = "CN=AegisKey Open Source Publisher"
_MSIX_PACKAGE_NAME = "AegisKey.PasswordStudio"
_DISPLAY_NAME = "AegisKey Password Studio"
_PUBLISHER_DISPLAY_NAME = "AegisKey Open Source Contributors"


def _read_project_version() -> str:
    data = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    version = str(project.get("version", "2.0.0")).strip()
    return version.lstrip("v")


def _to_four_part_version(version: str) -> tuple[int, int, int, int]:
    cleaned = version.lstrip("v").strip()
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?", cleaned)
    if match is None:
        msg = f"Cannot derive numeric Windows version from: {version!r}"
        raise ValueError(msg)
    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    build = int(match.group(4) or 0)
    return (major, minor, patch, build)


def _write_version_info_file(target: Path, version_tuple: tuple[int, int, int, int]) -> Path:
    ver_str = ".".join(str(part) for part in version_tuple)
    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{_PUBLISHER_DISPLAY_NAME}'),
          StringStruct('FileDescription', '{_DISPLAY_NAME} (CSPRNG Password Generator)'),
          StringStruct('FileVersion', '{ver_str}'),
          StringStruct('InternalName', 'AegisKey'),
          StringStruct('OriginalFilename', 'AegisKey.exe'),
          StringStruct('ProductName', '{_DISPLAY_NAME}'),
          StringStruct('ProductVersion', '{ver_str}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _find_tool(exe_name: str, candidate_globs: list[Path]) -> Path | None:
    which_hit = shutil.which(exe_name)
    if which_hit:
        return Path(which_hit)

    candidates: list[Path] = []
    for base in candidate_globs:
        if base.is_file():
            candidates.append(base)
        elif base.exists():
            candidates.extend(base.rglob(exe_name))

    x64_candidates = [p for p in candidates if p.parent.name.lower() == "x64"]
    pool = x64_candidates or candidates
    if not pool:
        return None
    pool.sort(reverse=True)
    return pool[0]


def _find_windows_sdk_tool(exe_name: str) -> Path | None:
    sdk_roots = [
        Path(r"C:\Program Files (x86)\Windows Kits\10\bin"),
        Path(r"C:\Program Files\Windows Kits\10\bin"),
    ]
    return _find_tool(exe_name, sdk_roots)


def _find_inno_setup() -> Path | None:
    inno_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    return _find_tool("ISCC.exe", inno_paths)


def _find_powershell() -> Path:
    pwsh = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if pwsh:
        return Path(pwsh)
    return Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")


def _run_pyinstaller(
    *,
    mode: str,
    dist_path: Path,
    work_path: Path,
    icon_path: Path,
    version_file: Path,
) -> Path:
    spec_path = PACKAGING_WIN_DIR / "aegiskey.spec"
    env = os.environ.copy()
    env["AEGISKEY_BUILD_MODE"] = mode
    env["AEGISKEY_APP_NAME"] = "AegisKey"
    env["AEGISKEY_ICON_PATH"] = str(icon_path)
    env["AEGISKEY_VERSION_FILE"] = str(version_file)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        str(spec_path),
    ]
    subprocess.run(cmd, cwd=ROOT_DIR, env=env, check=True)
    if mode == "onefile":
        return dist_path / "AegisKey.exe"
    return dist_path / "AegisKey"


def _resolve_signing_cert(
    cert_dir: Path,
) -> tuple[Path | None, str, str, Path | None]:
    """Return ``(pfx_path, pfx_password, publisher_subject, public_cer_path)``."""
    pfx_b64 = os.environ.get("WINDOWS_CERT_PFX_BASE64", "").strip()
    pfx_pass = os.environ.get("WINDOWS_CERT_PASSWORD", "").strip()
    ps = _find_powershell()

    if pfx_b64:
        cert_dir.mkdir(parents=True, exist_ok=True)
        pfx_path = cert_dir / "signing_secret.pfx"
        pfx_path.write_bytes(base64.b64decode(pfx_b64))
        script = (
            "$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new("
            f"'{pfx_path}', $env:AEGISKEY_PFX_PASS); "
            "Write-Output $cert.Subject"
        )
        env = os.environ.copy()
        env["AEGISKEY_PFX_PASS"] = pfx_pass
        res = subprocess.run(
            [str(ps), "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        subject = res.stdout.strip() or _DEFAULT_SELF_SIGN_SUBJECT
        return pfx_path, pfx_pass, subject, None

    # Fall back to a deterministic ephemeral self-signed certificate for local/CI verification.
    cert_dir.mkdir(parents=True, exist_ok=True)
    pfx_path = cert_dir / "ci_self_signed.pfx"
    cer_path = DIST_WIN_DIR / "AegisKey-CI-Signing.cer"
    # Non-sensitive temporary password scoped only to the disposable CI test certificate.
    gen_pass = "AegisKeyTempBuildCert!"  # noqa: S105
    ps_script = (
        "$ErrorActionPreference = 'Stop'; "
        "$rsa = [System.Security.Cryptography.RSA]::Create(2048); "
        "$sha = [System.Security.Cryptography.HashAlgorithmName]::SHA256; "
        "$pad = [System.Security.Cryptography.RSASignaturePadding]::Pkcs1; "
        "$req = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new("
        f"'{_DEFAULT_SELF_SIGN_SUBJECT}', $rsa, $sha, $pad); "
        "$kuFlags = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]"
        "::DigitalSignature; "
        "$ku = [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new("
        "$kuFlags, $true); "
        "$req.CertificateExtensions.Add($ku); "
        "$oids = [System.Security.Cryptography.OidCollection]::new(); "
        "[void]$oids.Add([System.Security.Cryptography.Oid]::new('1.3.6.1.5.5.7.3.3')); "
        "$eku = [System.Security.Cryptography.X509Certificates."
        "X509EnhancedKeyUsageExtension]::new($oids, $true); "
        "$req.CertificateExtensions.Add($eku); "
        "$bc = [System.Security.Cryptography.X509Certificates."
        "X509BasicConstraintsExtension]::new($false, $false, 0, $true); "
        "$req.CertificateExtensions.Add($bc); "
        "$now = [DateTimeOffset]::UtcNow; "
        "$cert = $req.CreateSelfSigned($now.AddMinutes(-5), $now.AddYears(2)); "
        "$pfxType = [System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx; "
        "$cerType = [System.Security.Cryptography.X509Certificates.X509ContentType]::Cert; "
        "$pfxBytes = $cert.Export($pfxType, $env:AEGISKEY_PFX_PASS); "
        "$cerBytes = $cert.Export($cerType); "
        f"[System.IO.File]::WriteAllBytes('{pfx_path}', $pfxBytes); "
        f"[System.IO.File]::WriteAllBytes('{cer_path}', $cerBytes)"
    )
    env = os.environ.copy()
    env["AEGISKEY_PFX_PASS"] = gen_pass
    subprocess.run(
        [str(ps), "-NoProfile", "-NonInteractive", "-Command", ps_script],
        env=env,
        check=True,
    )
    return pfx_path, gen_pass, _DEFAULT_SELF_SIGN_SUBJECT, cer_path


def _sign_artifact(
    signtool: Path,
    artifact: Path,
    pfx_path: Path,
    pfx_password: str,
    *,
    timestamp: bool,
) -> None:
    cmd = [
        str(signtool),
        "sign",
        "/fd",
        "SHA256",
        "/f",
        str(pfx_path),
    ]
    if pfx_password:
        cmd.extend(["/p", pfx_password])
    if timestamp:
        cmd.extend(["/tr", "http://timestamp.digicert.com", "/td", "SHA256"])
    cmd.append(str(artifact))
    subprocess.run(cmd, check=True)


def _build_msix(
    *,
    onedir: Path,
    assets_dir: Path,
    version_tuple: tuple[int, int, int, int],
    version_label: str,
    makeappx: Path,
    signtool: Path | None,
) -> Path:
    msix_stage = BUILD_WIN_DIR / "msix_stage"
    if msix_stage.exists():
        shutil.rmtree(msix_stage)
    shutil.copytree(onedir, msix_stage)

    stage_assets = msix_stage / "Assets"
    shutil.copytree(assets_dir / "msix_assets", stage_assets)

    cert_dir = BUILD_WIN_DIR / "cert"
    pfx_path: Path | None = None
    try:
        pfx_path, pfx_pass, publisher_subject, _cer = _resolve_signing_cert(cert_dir)
        manifest_tmpl = (PACKAGING_WIN_DIR / "AppxManifest.xml.template").read_text(
            encoding="utf-8"
        )
        msix_version = ".".join(str(part) for part in version_tuple)
        manifest_xml = manifest_tmpl.format(
            PACKAGE_NAME=xml_escape(_MSIX_PACKAGE_NAME, {'"': "&quot;"}),
            PUBLISHER=xml_escape(publisher_subject, {'"': "&quot;"}),
            VERSION=msix_version,
            DISPLAY_NAME=xml_escape(_DISPLAY_NAME, {'"': "&quot;"}),
            PUBLISHER_DISPLAY_NAME=xml_escape(_PUBLISHER_DISPLAY_NAME, {'"': "&quot;"}),
        )
        (msix_stage / "AppxManifest.xml").write_text(manifest_xml, encoding="utf-8")

        msix_out = DIST_WIN_DIR / f"AegisKey-{version_label}-win64.msix"
        subprocess.run(
            [str(makeappx), "pack", "/o", "/d", str(msix_stage), "/p", str(msix_out)],
            check=True,
        )

        if signtool is not None and pfx_path is not None and pfx_path.exists():
            is_prod_cert = bool(os.environ.get("WINDOWS_CERT_PFX_BASE64", "").strip())
            _sign_artifact(
                signtool,
                msix_out,
                pfx_path,
                pfx_pass,
                timestamp=is_prod_cert,
            )
        return msix_out
    finally:
        if pfx_path is not None and pfx_path.exists():
            pfx_path.unlink(missing_ok=True)


def _smoke_test_executable(exe_path: Path) -> None:
    """Verify packaged Windows EXE launches cleanly, renders AegisKey window, and closes."""
    ver_res = subprocess.run(
        [str(exe_path), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    if ver_res.stdout.strip() and "password-generator" not in ver_res.stdout:
        msg = f"Unexpected --version output from {exe_path}: {ver_res.stdout!r}"
        raise RuntimeError(msg)

    if sys.platform != "win32":
        return

    from ctypes import wintypes

    windll: Any = getattr(ctypes, "windll", None)
    winfunctypes: Any = getattr(ctypes, "WINFUNCTYPE", None)
    if windll is None or winfunctypes is None:
        return

    proc = subprocess.Popen([str(exe_path)])
    user32 = windll.user32
    enum_windows_proc = winfunctypes(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _find_visible_hwnd() -> int | None:
        found: list[int] = []

        @enum_windows_proc
        def _cb(hwnd: int, _lparam: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                length = int(user32.GetWindowTextLengthW(hwnd))
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "AegisKey" in buf.value:
                        found.append(hwnd)
            return True

        user32.EnumWindows(_cb, 0)
        return found[0] if found else None

    try:
        hwnd: int | None = None
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                msg = f"Frozen app {exe_path} exited prematurely with code {proc.returncode}"
                raise RuntimeError(msg)
            candidate = _find_visible_hwnd()
            if (
                candidate is not None
                and (int(user32.GetWindowLongW(candidate, -20)) & 0x80000) == 0
            ):
                hwnd = candidate
                break
            time.sleep(0.1)

        if hwnd is None:
            msg = f"Timed out waiting for AegisKey window from {exe_path}"
            raise RuntimeError(msg)

        user32.PostMessageW(hwnd, 0x0010, 0, 0)
        rc = proc.wait(timeout=10)
        if rc != 0:
            msg = f"Frozen app {exe_path} returned non-zero exit code on WM_CLOSE: {rc}"
            raise RuntimeError(msg)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)


def _write_sha256sums(dist_dir: Path, artifacts: list[Path]) -> Path:
    lines: list[str] = []
    for path in sorted(artifacts, key=lambda p: p.name.lower()):
        if path.exists() and path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.name}")
    out_file = dist_dir / "SHA256SUMS.txt"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_file


def main() -> int:
    """Build selected Windows installers and portable binaries."""
    parser = argparse.ArgumentParser(description="Build AegisKey Windows EXE & MSIX deliverables.")
    parser.add_argument(
        "--version",
        default=_read_project_version(),
        help="Semantic release version (defaults to pyproject.toml version).",
    )
    parser.add_argument(
        "--format",
        choices=("all", "portable", "setup", "msix"),
        default="all",
        help="Target installer/binary artifact group to build.",
    )
    parser.add_argument(
        "--require-setup",
        action="store_true",
        help="Fail if Inno Setup (ISCC.exe) is not installed.",
    )
    parser.add_argument(
        "--require-msix",
        action="store_true",
        help="Fail if Windows SDK makeappx.exe is not installed.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Launch compiled EXE binaries and verify live GUI initialization + clean exit.",
    )
    args = parser.parse_args()

    version_label = args.version.lstrip("v").strip()
    version_tuple = _to_four_part_version(version_label)

    DIST_WIN_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_WIN_DIR.mkdir(parents=True, exist_ok=True)

    assets_dir = generate_windows_assets(BUILD_WIN_DIR / "assets")
    icon_path = assets_dir / "AegisKey.ico"
    version_file = _write_version_info_file(BUILD_WIN_DIR / "version_info.txt", version_tuple)

    artifacts: list[Path] = []
    onedir_path: Path | None = None

    need_onedir = args.format in ("all", "setup", "msix")
    if need_onedir:
        staged_dir = DIST_WIN_DIR / "staged"
        onedir_path = _run_pyinstaller(
            mode="onedir",
            dist_path=staged_dir,
            work_path=BUILD_WIN_DIR / "pyinstaller-onedir",
            icon_path=icon_path,
            version_file=version_file,
        )
        print(f"Built onedir bundle: {onedir_path}")
        if args.smoke_test:
            _smoke_test_executable(onedir_path / "AegisKey.exe")
            print("Smoke test passed for onedir AegisKey.exe")

    if args.format in ("all", "portable"):
        portable_stage = BUILD_WIN_DIR / "portable_dist"
        raw_exe = _run_pyinstaller(
            mode="onefile",
            dist_path=portable_stage,
            work_path=BUILD_WIN_DIR / "pyinstaller-onefile",
            icon_path=icon_path,
            version_file=version_file,
        )
        portable_out = DIST_WIN_DIR / f"AegisKey-{version_label}-win64-portable.exe"
        shutil.copy2(raw_exe, portable_out)
        artifacts.append(portable_out)
        print(f"Built portable EXE: {portable_out}")
        if args.smoke_test:
            _smoke_test_executable(portable_out)
            print(f"Smoke test passed for {portable_out.name}")

    if args.format in ("all", "setup"):
        iscc = _find_inno_setup()
        if iscc is None:
            if args.require_setup:
                msg = "Inno Setup compiler (ISCC.exe) not found."
                raise FileNotFoundError(msg)
            print("Skipping Inno Setup installer (.exe): ISCC.exe not installed locally.")
        elif onedir_path is not None:
            setup_name = f"AegisKey-{version_label}-win64-setup"
            iss_file = PACKAGING_WIN_DIR / "installer.iss"
            subprocess.run(
                [
                    str(iscc),
                    f"/DAppVersion={version_label}",
                    f"/DSourceDir={onedir_path.resolve()}",
                    f"/DOutputDir={DIST_WIN_DIR.resolve()}",
                    f"/DOutputBaseFilename={setup_name}",
                    f"/DIconFile={icon_path.resolve()}",
                    f"/DLicenseFile={(ROOT_DIR / 'LICENSE').resolve()}",
                    str(iss_file),
                ],
                check=True,
            )
            setup_out = DIST_WIN_DIR / f"{setup_name}.exe"
            artifacts.append(setup_out)
            print(f"Built Inno Setup EXE installer: {setup_out}")

    if args.format in ("all", "msix"):
        makeappx = _find_windows_sdk_tool("makeappx.exe")
        signtool = _find_windows_sdk_tool("signtool.exe")
        if makeappx is None:
            if args.require_msix:
                msg = "Windows SDK makeappx.exe not found."
                raise FileNotFoundError(msg)
            print("Skipping MSIX package: makeappx.exe not installed.")
        elif onedir_path is not None:
            msix_out = _build_msix(
                onedir=onedir_path,
                assets_dir=assets_dir,
                version_tuple=version_tuple,
                version_label=version_label,
                makeappx=makeappx,
                signtool=signtool,
            )
            artifacts.append(msix_out)
            cer_out = DIST_WIN_DIR / "AegisKey-CI-Signing.cer"
            if cer_out.exists():
                artifacts.append(cer_out)
            print(f"Built signed MSIX package: {msix_out}")

    sums_file = _write_sha256sums(DIST_WIN_DIR, artifacts)
    print(f"Wrote checksums manifest: {sums_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
