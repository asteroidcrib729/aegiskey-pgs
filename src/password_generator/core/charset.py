"""Character pool resolution and policy validation for cryptographic password generation."""

from dataclasses import dataclass

from password_generator.core.models import PasswordPolicy, PolicyValidationError

UPPERCASE_CHARS: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWERCASE_CHARS: str = "abcdefghijklmnopqrstuvwxyz"
DIGIT_CHARS: str = "0123456789"
DEFAULT_SYMBOL_CHARS: str = "!@#$%^&*()-_=+[]{};:,.<>?/"
AMBIGUOUS_CHARS: frozenset[str] = frozenset("0Oo1lI|`'\"")
BASE62_ALPHABET: str = DIGIT_CHARS + UPPERCASE_CHARS + LOWERCASE_CHARS

MIN_PASSWORD_LENGTH: int = 4
MAX_PASSWORD_LENGTH: int = 128


@dataclass(frozen=True, slots=True)
class CharsetPools:
    """Resolved non-empty character pools after exclusions and policy validation."""

    uppercase: str
    lowercase: str
    digits: str
    symbols: str
    combined: str
    active_pools: tuple[str, ...]
    letter_pool: str


def _filter_chars(chars: str, excluded: frozenset[str]) -> str:
    """Return unique characters from ``chars`` preserving order, excluding ``excluded``."""
    seen: set[str] = set()
    kept: list[str] = []
    for ch in chars:
        if ch not in excluded and ch not in seen:
            seen.add(ch)
            kept.append(ch)
    return "".join(kept)


def _sanitize_custom_symbols(raw_symbols: str) -> str:
    """Keep printable non-whitespace ASCII punctuation/symbol characters from custom input."""
    valid: list[str] = []
    seen: set[str] = set()
    for ch in raw_symbols:
        code = ord(ch)
        if 33 <= code <= 126 and not ch.isalnum() and ch not in seen:
            seen.add(ch)
            valid.append(ch)
    return "".join(valid)


def resolve_charset_pools(policy: PasswordPolicy) -> CharsetPools:
    """Validate a ``PasswordPolicy`` and return sanitized, non-empty character pools.

    Raises:
        PolicyValidationError: If length bounds, character exclusions, or class guarantees
            produce an unsatisfiable policy.
    """
    if not (MIN_PASSWORD_LENGTH <= policy.length <= MAX_PASSWORD_LENGTH):
        raise PolicyValidationError(
            f"Password length must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH}."
        )

    excluded = set(policy.excluded_chars)
    if policy.exclude_ambiguous:
        excluded.update(AMBIGUOUS_CHARS)
    excluded_frozen = frozenset(excluded)

    upper = _filter_chars(UPPERCASE_CHARS, excluded_frozen) if policy.use_uppercase else ""
    lower = _filter_chars(LOWERCASE_CHARS, excluded_frozen) if policy.use_lowercase else ""
    digits = _filter_chars(DIGIT_CHARS, excluded_frozen) if policy.use_digits else ""

    raw_symbols = (
        _sanitize_custom_symbols(policy.custom_symbols)
        if policy.custom_symbols.strip()
        else DEFAULT_SYMBOL_CHARS
    )
    if policy.use_symbols and not raw_symbols:
        raise PolicyValidationError(
            "Custom symbols contained no valid printable ASCII symbol characters."
        )
    symbols = _filter_chars(raw_symbols, excluded_frozen) if policy.use_symbols else ""

    if policy.use_uppercase and not upper:
        raise PolicyValidationError("All uppercase letters were excluded by filter rules.")
    if policy.use_lowercase and not lower:
        raise PolicyValidationError("All lowercase letters were excluded by filter rules.")
    if policy.use_digits and not digits:
        raise PolicyValidationError("All digits were excluded by filter rules.")
    if policy.use_symbols and not symbols:
        raise PolicyValidationError("All symbol characters were excluded by filter rules.")

    active_pools = tuple(pool for pool in (upper, lower, digits, symbols) if pool)
    if not active_pools:
        raise PolicyValidationError(
            "Enable at least one character set (upper, lower, digits, symbols)."
        )

    combined = _filter_chars("".join(active_pools), frozenset())
    letter_pool = _filter_chars(upper + lower, frozenset())

    if policy.start_with_letter and not letter_pool:
        raise PolicyValidationError(
            "Starting with a letter requires Uppercase or Lowercase characters to be enabled."
        )

    if policy.no_adjacent_repeats and len(combined) < 2 and policy.length > 1:
        raise PolicyValidationError(
            "Cannot avoid adjacent repeating characters with fewer than 2 unique characters."
        )

    return CharsetPools(
        uppercase=upper,
        lowercase=lower,
        digits=digits,
        symbols=symbols,
        combined=combined,
        active_pools=active_pools,
        letter_pool=letter_pool,
    )
