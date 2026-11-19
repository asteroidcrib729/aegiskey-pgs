"""Unit tests for CSPRNG password, passphrase, token, PIN, and batch generation."""

import re

import pytest

from password_generator.core.charset import AMBIGUOUS_CHARS, BASE62_ALPHABET, DIGIT_CHARS
from password_generator.core.generator import (
    generate_batch,
    generate_passphrase,
    generate_password,
    generate_pin,
    generate_token,
)
from password_generator.core.models import (
    GenerationMode,
    PassphrasePolicy,
    PasswordPolicy,
    PinPolicy,
    PolicyValidationError,
    SecurityTier,
    TokenFormat,
    TokenPolicy,
    WordCase,
)
from password_generator.data.wordlist import PASSPHRASE_WORDS


def test_wordlist_has_4096_unique_clean_words() -> None:
    assert len(PASSPHRASE_WORDS) == 4096
    assert len(set(PASSPHRASE_WORDS)) == 4096
    assert all(re.fullmatch(r"[a-z]{3,14}", word) for word in PASSPHRASE_WORDS)


def test_generate_password_covers_all_enabled_classes() -> None:
    policy = PasswordPolicy(length=24)
    result = generate_password(policy)
    assert len(result.value) == 24
    assert any(ch.isupper() for ch in result.value)
    assert any(ch.islower() for ch in result.value)
    assert any(ch.isdigit() for ch in result.value)
    assert any(not ch.isalnum() for ch in result.value)
    assert result.report.tier == SecurityTier.QUANTUM_RESISTANT


def test_generate_password_respects_ambiguous_start_letter_and_no_repeats() -> None:
    policy = PasswordPolicy(
        length=20,
        exclude_ambiguous=True,
        no_adjacent_repeats=True,
        start_with_letter=True,
    )
    for _ in range(10):
        secret = generate_password(policy).value
        assert len(secret) == 20
        assert secret[0].isalpha()
        assert not any(ch in AMBIGUOUS_CHARS for ch in secret)
        assert all(secret[i] != secret[i - 1] for i in range(1, len(secret)))


def test_generate_password_two_char_pool_no_repeats_preserves_classes() -> None:
    policy = PasswordPolicy(
        length=6,
        use_uppercase=True,
        use_lowercase=False,
        use_digits=True,
        use_symbols=False,
        excluded_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ"[1:] + DIGIT_CHARS[1:],
        no_adjacent_repeats=True,
        start_with_letter=True,
    )
    secret = generate_password(policy).value
    assert secret == "A0A0A0"


def test_generate_passphrase_word_count_separator_and_suffixes() -> None:
    policy = PassphrasePolicy(
        word_count=7,
        separator="-",
        word_case=WordCase.TITLE,
        append_digit=True,
        append_symbol=False,
    )
    result = generate_passphrase(policy)
    parts = result.value.split("-")
    assert len(parts) == 7
    assert all(part[0].isupper() for part in parts)
    assert parts[-1][-1].isdigit()
    assert result.report.effective_bits > 85.0


def test_generate_passphrase_rejects_invalid_separator() -> None:
    with pytest.raises(PolicyValidationError):
        generate_passphrase(PassphrasePolicy(separator="\n"))


def test_generate_token_formats_and_prefix() -> None:
    hex_tok = generate_token(
        TokenPolicy(bit_strength=256, token_format=TokenFormat.HEX, prefix="sk_live_")
    )
    assert hex_tok.value.startswith("sk_live_")
    raw_hex = hex_tok.value.removeprefix("sk_live_")
    assert len(raw_hex) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", raw_hex)

    b62_tok = generate_token(TokenPolicy(bit_strength=128, token_format=TokenFormat.BASE62))
    assert all(ch in BASE62_ALPHABET for ch in b62_tok.value)
    assert b62_tok.report.effective_bits == 128.0


def test_generate_token_rejects_unsupported_bits() -> None:
    with pytest.raises(PolicyValidationError):
        generate_token(TokenPolicy(bit_strength=64))


def test_generate_pin_blocks_sequences_and_adjacent_repeats() -> None:
    policy = PinPolicy(length=8, disallow_sequences=True, disallow_repeated_digits=True)
    for _ in range(15):
        pin = generate_pin(policy).value
        assert len(pin) == 8
        assert pin.isdigit()
        assert all(pin[i] != pin[i - 1] for i in range(1, len(pin)))
        for idx in range(len(pin) - 2):
            d0, d1, d2 = int(pin[idx]), int(pin[idx + 1]), int(pin[idx + 2])
            assert not (d1 - d0 == 1 and d2 - d1 == 1)
            assert not (d0 - d1 == 1 and d1 - d2 == 1)


def test_generate_batch_returns_unique_secrets() -> None:
    items = generate_batch(GenerationMode.PASSWORD, 5)
    assert len(items) == 5
    assert len({item.value for item in items}) == 5
