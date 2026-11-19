"""Preconfigured 2026 security profiles for common password and credential scenarios."""

from password_generator.core.models import (
    GenerationMode,
    PassphrasePolicy,
    PasswordPolicy,
    PinPolicy,
    PresetProfile,
    TokenFormat,
    TokenPolicy,
    WordCase,
)

SECURITY_PRESETS: tuple[PresetProfile, ...] = (
    PresetProfile(
        key="near_unbreakable",
        name="Near-Unbreakable (24-Char)",
        description="24 random ASCII characters across all 4 classes (~157 bits entropy).",
        mode=GenerationMode.PASSWORD,
        password_policy=PasswordPolicy(
            length=24,
            use_uppercase=True,
            use_lowercase=True,
            use_digits=True,
            use_symbols=True,
            exclude_ambiguous=False,
            no_adjacent_repeats=False,
            start_with_letter=False,
        ),
    ),
    PresetProfile(
        key="standard_strong",
        name="Standard Strong (16-Char)",
        description="16 random characters with full class coverage (~105 bits entropy).",
        mode=GenerationMode.PASSWORD,
        password_policy=PasswordPolicy(
            length=16,
            use_uppercase=True,
            use_lowercase=True,
            use_digits=True,
            use_symbols=True,
        ),
    ),
    PresetProfile(
        key="web_compatible",
        name="Web-Safe (No Ambiguous)",
        description="20 chars, starts with a letter, excludes 0/O/1/l/I and quotes.",
        mode=GenerationMode.PASSWORD,
        password_policy=PasswordPolicy(
            length=20,
            use_uppercase=True,
            use_lowercase=True,
            use_digits=True,
            use_symbols=True,
            exclude_ambiguous=True,
            no_adjacent_repeats=True,
            start_with_letter=True,
            custom_symbols="!@#$%^&*-_+=?",
        ),
    ),
    PresetProfile(
        key="memorable_passphrase",
        name="Diceware Passphrase (7 Words)",
        description="7 high-entropy English words + digit (~87 bits, easy to type).",
        mode=GenerationMode.PASSPHRASE,
        passphrase_policy=PassphrasePolicy(
            word_count=7,
            separator="-",
            word_case=WordCase.TITLE,
            append_digit=True,
            append_symbol=False,
        ),
    ),
    PresetProfile(
        key="api_secret_256",
        name="API Secret (256-Bit Token)",
        description="256-bit URL-safe Base64 token for services, webhooks, and signing keys.",
        mode=GenerationMode.TOKEN,
        token_policy=TokenPolicy(
            bit_strength=256,
            token_format=TokenFormat.URLSAFE_B64,
            prefix="ak_live_",
        ),
    ),
    PresetProfile(
        key="hardened_pin",
        name="Hardened PIN (6-Digit)",
        description="6-digit PIN rejecting sequences (123) and adjacent repeated digits.",
        mode=GenerationMode.PIN,
        pin_policy=PinPolicy(
            length=6,
            disallow_sequences=True,
            disallow_repeated_digits=True,
        ),
    ),
)


def get_preset_by_key(key: str) -> PresetProfile | None:
    """Return the matching preset profile or ``None`` if unknown."""
    for preset in SECURITY_PRESETS:
        if preset.key == key:
            return preset
    return None
