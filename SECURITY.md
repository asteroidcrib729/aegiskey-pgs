# Security Policy

## Security Architecture & Guarantees

AegisKey is engineered around local-only, high-assurance cryptographic hygiene:

- **CSPRNG Only:** Every random character, word index, token, and PIN uses Python's `secrets` module (backed by `os.urandom` / `BCryptGenRandom` on Windows and `getrandom` on Linux). Mersenne Twister (`random`) is never used.
- **Zero Disk Persistence of Secrets:** Generated secrets stay exclusively in memory (`SessionVaultService`) and are wiped when exiting or clicking **Wipe**. Only non-sensitive UI preferences (`theme`, `clipboard_clear_seconds`, `mask_secret_display`, `last_preset_key`) are saved to disk.
- **Clipboard Hygiene:** Auto-clear countdown timers hash/compare current clipboard contents before wiping so unrelated data copied afterward by the user is preserved.

## Supported Versions

| Version | Supported |
| :--- | :--- |
| `2.0.x` | Yes |
| `< 2.0` (legacy coursework notebook) | No |

## Reporting a Vulnerability

If you discover a cryptographic flaw, secret leak, clipboard hygiene bypass, or installer packaging issue:

1. **Do not open a public GitHub issue.**
2. Use GitHub **Security Advisories** (**Security** tab → **Report a vulnerability**) to disclose privately with reproduction steps and affected version.
3. Expect acknowledgment and coordinated remediation prior to public disclosure.
