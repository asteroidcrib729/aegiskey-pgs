# Contributing to AegisKey

Contributions that strengthen cryptographic correctness, accessibility, HiDPI polish, or cross-platform packaging are welcome.

## Development Setup

```powershell
# 1. Install uv (https://docs.astral.sh/uv/) and sync Python 3.14.7 + dev tools
uv sync --all-groups

# 2. Launch the desktop application
uv run password-generator
```

## Verification Before Opening a Pull Request

Every change must pass all formatting, lint, type-check, and automated test gates cleanly:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pyrefly check
uv run pytest -v
```

### Cryptography & Security Rules

- Never replace `secrets` with `random`.
- Never write generated secrets or session history to disk, temporary files, or logs.
- Keep third-party runtime `dependencies = []` empty in `pyproject.toml`.
- Preserve full type annotations (`ANN` rules) and clean Ruff Bandit (`S`) checks.

## Building Windows Installers Locally

With Windows 10/11 SDK (`makeappx.exe`, `signtool.exe`) and optionally [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed:

```powershell
# Build Portable EXE, Inno Setup EXE (if ISCC.exe is installed), and MSIX + SHA256SUMS.txt
uv run python -m installers.windows.build_windows --format all --smoke-test
```
