"""Immutable domain models and validation errors for secret generation and auditing."""

from dataclasses import dataclass
from enum import StrEnum


class PolicyValidationError(ValueError):
    """Raised when a generation policy cannot satisfy security or character-pool constraints."""


class GenerationMode(StrEnum):
    """Supported secret generation workflows."""

    PASSWORD = "password"  # noqa: S105
    PASSPHRASE = "passphrase"  # noqa: S105
    TOKEN = "token"  # noqa: S105
    PIN = "pin"


class TokenFormat(StrEnum):
    """Encoding formats for cryptographic API tokens and keys."""

    URLSAFE_B64 = "urlsafe_b64"
    HEX = "hex"
    BASE62 = "base62"


class WordCase(StrEnum):
    """Capitalization strategies for Diceware-style passphrases."""

    LOWER = "lower"
    TITLE = "title"
    UPPER = "upper"
    RANDOM_WORD = "random_word"


class SecurityTier(StrEnum):
    """Human-readable strength classification derived from effective entropy bits."""

    CRITICAL = "Critical"
    WEAK = "Weak"
    FAIR = "Fair"
    STRONG = "Strong"
    NEAR_UNBREAKABLE = "Near-Unbreakable"
    QUANTUM_RESISTANT = "Quantum-Resistant"


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Configuration constraints for random character-pool password generation."""

    length: int = 20
    use_uppercase: bool = True
    use_lowercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    exclude_ambiguous: bool = False
    no_adjacent_repeats: bool = False
    start_with_letter: bool = False
    custom_symbols: str = ""
    excluded_chars: str = ""


@dataclass(frozen=True, slots=True)
class PassphrasePolicy:
    """Configuration constraints for cryptographic multi-word passphrase generation."""

    word_count: int = 6
    separator: str = "-"
    word_case: WordCase = WordCase.TITLE
    append_digit: bool = True
    append_symbol: bool = False


@dataclass(frozen=True, slots=True)
class TokenPolicy:
    """Configuration constraints for developer API secret and cryptographic token generation."""

    bit_strength: int = 256
    token_format: TokenFormat = TokenFormat.URLSAFE_B64
    prefix: str = ""


@dataclass(frozen=True, slots=True)
class PinPolicy:
    """Configuration constraints for high-integrity numeric PIN generation."""

    length: int = 6
    disallow_sequences: bool = True
    disallow_repeated_digits: bool = True


@dataclass(frozen=True, slots=True)
class AttackEstimate:
    """Estimated brute-force crack duration under a defined attacker capability model."""

    label: str
    guesses_per_second: float
    seconds_to_crack: float
    human_duration: str


@dataclass(frozen=True, slots=True)
class StrengthReport:
    """Detailed cryptographic entropy audit and weakness evaluation for a secret."""

    entropy_bits: float
    effective_bits: float
    score: int
    tier: SecurityTier
    charset_size: int
    length: int
    warnings: tuple[str, ...]
    recommendations: tuple[str, ...]
    attack_estimates: tuple[AttackEstimate, ...]


@dataclass(frozen=True, slots=True)
class GeneratedSecret:
    """Result returned by the generator containing the secret and its cryptographic report."""

    value: str
    mode: GenerationMode
    report: StrengthReport
    summary: str


@dataclass(frozen=True, slots=True)
class PresetProfile:
    """Named security preset binding a mode to a hardened default policy."""

    key: str
    name: str
    description: str
    mode: GenerationMode
    password_policy: PasswordPolicy | None = None
    passphrase_policy: PassphrasePolicy | None = None
    token_policy: TokenPolicy | None = None
    pin_policy: PinPolicy | None = None
