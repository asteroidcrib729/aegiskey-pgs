# AegisKey · Secure Password Generator Studio (v2.0)

A modern, high-DPI Tkinter desktop workstation for generating and auditing cryptographically strong passwords, Diceware passphrases, developer API tokens, and hardened PINs — built with **Python 3.14.7**, **Astral `uv`**, **Ruff**, and **Pyrefly**.

> Transformed from a single 2022 coursework Jupyter Notebook (`Project FA22 - Password Generator With GUI.ipynb`) into a modular, zero-dependency, security-hardened 2026 desktop application. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full 2022 → 2026 breakdown.

---

## Key Capabilities

- **Cryptographically Secure Generation (`secrets` CSPRNG):**
  - **Random Passwords (4–128 chars):** Guaranteed class coverage across Uppercase, Lowercase, Digits, and Symbols, uniform filling, Fisher-Yates CSPRNG shuffle, ambiguous glyph exclusion (`0O1lI|\`'"`), no-adjacent-repeat option, start-with-letter option, custom symbols, and character exclusions.
  - **Diceware Passphrases (4–12 words):** Curated **4,096-word** A–Z dictionary (`12.00` bits/word), customizable separators, casing (`Title Case`, `lowercase`, `UPPERCASE`, `Random Word Case`), and optional digit/symbol suffixes.
  - **Developer API Tokens (128 / 192 / 256 / 384 / 512-bit):** URL-Safe Base64, Hexadecimal, and Base62 encodings with optional key prefixes (e.g. `ak_live_`).
  - **Hardened PINs (4–16 digits):** Rejects ascending/descending sequences (`123`, `987`) and repeated digits.
  - **4x Batch Generator:** Generate and inspect 4 distinct candidates in one click.
- **Real-Time Entropy & Brute-Force Auditor:**
  - Evaluates both generated secrets and manually typed/pasted inputs in real time.
  - Computes effective entropy bits, 0–100 security score, 6-tier classification (`Critical` → `Quantum-Resistant`), pattern warnings (repeats, monotonic runs, keyboard walks), and crack-time estimates across online throttled, offline Argon2id GPU, and offline SHA-256 ASIC models.
- **High-DPI Tkinter Workstation UI:**
  - Windows Per-Monitor v2 DPI awareness (`SetProcessDpiAwarenessContext`), synchronized `tk scaling`, DPI-proportional spacing, native DWM dark/light titlebar support, and flicker-free startup/teardown.
  - Anti-aliased Tk 9.0 SVG vector app icon, button icons, pill toggle switches, and rounded segmented strength meter.
  - Precision two-finger laptop touchpad scrolling (`<TouchpadScroll>` + sub-notch `<MouseWheel>`) across scrollable policy and vault viewports.
  - Switchable **Obsidian Dark** and **Studio Light** themes.
- **Zero-Persistence Secret Hygiene:**
  - **Auto-Clearing Clipboard:** Configurable countdown (`15s` / `30s` / `60s` / `120s` / `Manual`) that verifies clipboard ownership before wiping so unrelated copies stay untouched.
  - **RAM-Only Session Vault:** Masked-by-default history stored exclusively in memory and wiped on exit or on demand.

---

## Tech Stack & Tooling

| Tool | Purpose |
| :--- | :--- |
| **Python 3.14.7** | Runtime & Tcl/Tk 9.0 GUI (`tkinter` / `ttk`), zero third-party runtime dependencies |
| **Astral `uv`** | Virtual environment (`.venv`), `pyproject.toml`, and deterministic `uv.lock` |
| **Ruff** | Strict linting (incl. Bandit `S` security rules & type annotations `ANN`) and formatting |
| **Pyrefly** | Static/dynamic type checking and syntax validation |
| **Pytest** | Automated unit, service, and Tkinter UI smoke tests |

---

## Getting Started

```powershell
# 1. Create/sync the Python 3.14.7 environment
uv sync

# 2. Launch the GUI application
uv run password-generator
# or:
uv run python -m password_generator
```

---

## Quality Checks

```powershell
# Lint check (Ruff)
uv run ruff check .

# Format check (Ruff)
uv run ruff format --check .

# Type check (Pyrefly)
uv run pyrefly check

# Test suite (Pytest)
uv run pytest -v
```

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+G` | Generate a new secret |
| `Ctrl+Shift+C` | Copy active secret & start auto-clear timer |
| `Ctrl+B` | Refresh 4x batch candidates |
| `Ctrl+M` | Toggle secret masking (Show / Hide) |
| `Ctrl+L` | Clear OS clipboard immediately |
| `Ctrl+T` | Toggle Obsidian Dark / Studio Light theme |
| `F1` | Open Shortcuts & Security Reference modal |

---

## Installers & CI/CD Workflows (GitHub Ready)

### Windows Installer Formats

1. **Portable EXE (`AegisKey-<version>-win64-portable.exe`):** Standalone zero-install PyInstaller single-file Windows binary.
2. **Setup Installer EXE (`AegisKey-<version>-win64-setup.exe`):** Modern Inno Setup 6 installer with Start Menu/Desktop shortcuts and native uninstaller.
3. **Signed MSIX (`AegisKey-<version>-win64.msix`):** Windows App Package packed with Windows SDK `makeappx.exe` and signed with `signtool.exe`.

> **Signing Notes:** If `WINDOWS_CERT_PFX_BASE64` and `WINDOWS_CERT_PASSWORD` repository secrets are configured on GitHub, releases sign and RFC-3161 timestamp with your Authenticode certificate. Otherwise, CI signs the `.msix` with an ephemeral test certificate and exports `AegisKey-CI-Signing.cer` alongside `SHA256SUMS.txt`.

Build installers locally on Windows (uses PyInstaller, Windows SDK `makeappx.exe`/`signtool.exe`, and Inno Setup 6 if installed):

```powershell
uv sync --all-groups
uv run python -m installers.windows.build_windows --format all --smoke-test
```

### Automated GitHub Actions Workflows

- **[`ci.yml`](.github/workflows/ci.yml):** Enforces `uv lock --check`, Ruff formatting & lint, Pyrefly type checking, cross-platform Pytest (`windows-latest` and headless `ubuntu-latest` under `Xvfb`), plus Windows EXE & MSIX builds + live smoke tests.
- **[`release-windows.yml`](.github/workflows/release-windows.yml):** Triggered by `v*.*.*` tags or manual dispatch; validates all quality checks, compiles Portable EXE, Setup EXE, signed MSIX, wheel/sdist, `SHA256SUMS.txt`, and publishes them to a GitHub Release.
- **[`security.yml`](.github/workflows/security.yml):** Runs CodeQL static analysis, Bandit (`S`) lint checks, PR dependency review, and enforces zero third-party runtime dependencies in `pyproject.toml`.
- **[`python-package.yml`](.github/workflows/python-package.yml):** Builds and validates `.whl`/`.tar.gz` artifacts, dictionary bundling, and CLI entry points.

---

## Publishing Checklist for GitHub

```powershell
# 1. Create an empty repository on GitHub, add the remote, and push main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main

# 2. (Optional) Tag a release to automatically export EXE & MSIX installers to GitHub Releases
git tag v2.0.0
git push origin v2.0.0
```

---

## Project Layout

```text
password-generator-app/
├── .github/
│   ├── ISSUE_TEMPLATE/          # Bug report & feature request forms
│   ├── workflows/               # CI, Windows EXE/MSIX release, Security/CodeQL & Wheel builds
│   ├── dependabot.yml           # Weekly uv & GitHub Actions dependency updates
│   └── pull_request_template.md
├── .vscode/                     # Dedicated IDE settings, extensions, launch & tasks
├── docs/
│   └── ARCHITECTURE.md          # 2022 -> 2026 transformation & security architecture
├── installers/
│   └── windows/                 # PyInstaller spec, Inno Setup .iss, MSIX manifest & build scripts
├── src/password_generator/
│   ├── __main__.py              # CLI / module entry point
│   ├── app.py                   # Bootstrapper (DPI awareness + Tk root)
│   ├── core/                    # Pure CSPRNG generators, charset, entropy & presets
│   ├── data/                    # Packaged 4,096-word Diceware dictionary
│   ├── services/                # Clipboard auto-wipe, RAM vault & non-secret prefs
│   └── ui/                      # HiDPI Tkinter workstation, themes & canvas widgets
├── tests/                       # Unit, service & UI integration tests
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
├── .python-version              # Pinned to 3.14.7
├── pyproject.toml               # uv, Ruff, Pyrefly & Pytest configuration
└── uv.lock                      # Reproducible lockfile
```
