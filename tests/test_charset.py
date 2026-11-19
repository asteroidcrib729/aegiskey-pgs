"""Unit tests for character pool resolution and policy validation."""

import pytest

from password_generator.core.charset import (
    AMBIGUOUS_CHARS,
    DIGIT_CHARS,
    LOWERCASE_CHARS,
    UPPERCASE_CHARS,
    resolve_charset_pools,
)
from password_generator.core.models import PasswordPolicy, PolicyValidationError


def test_default_pools_contain_all_ascii_classes() -> None:
    pools = resolve_charset_pools(PasswordPolicy())
    assert pools.uppercase == UPPERCASE_CHARS
    assert pools.lowercase == LOWERCASE_CHARS
    assert pools.digits == DIGIT_CHARS
    assert len(pools.active_pools) == 4
    assert len(pools.combined) == len(set(pools.combined))


def test_exclude_ambiguous_filters_all_ambiguous_glyphs() -> None:
    pools = resolve_charset_pools(PasswordPolicy(exclude_ambiguous=True))
    assert not any(ch in AMBIGUOUS_CHARS for ch in pools.combined)


def test_custom_symbols_are_sanitized_and_deduplicated() -> None:
    pools = resolve_charset_pools(
        PasswordPolicy(custom_symbols="!@!# abc123\n$"),
    )
    assert pools.symbols == "!@#$"


def test_validation_rejects_empty_class_selection() -> None:
    policy = PasswordPolicy(
        use_uppercase=False,
        use_lowercase=False,
        use_digits=False,
        use_symbols=False,
    )
    with pytest.raises(PolicyValidationError, match="Enable at least one character set"):
        resolve_charset_pools(policy)


def test_validation_rejects_length_below_minimum() -> None:
    policy = PasswordPolicy(length=3)
    with pytest.raises(PolicyValidationError, match="between 4 and 128"):
        resolve_charset_pools(policy)


def test_validation_rejects_all_digits_excluded() -> None:
    policy = PasswordPolicy(excluded_chars=DIGIT_CHARS)
    with pytest.raises(PolicyValidationError, match="All digits were excluded"):
        resolve_charset_pools(policy)


def test_validation_rejects_start_with_letter_when_letters_disabled() -> None:
    policy = PasswordPolicy(
        use_uppercase=False,
        use_lowercase=False,
        start_with_letter=True,
    )
    with pytest.raises(PolicyValidationError, match="Starting with a letter"):
        resolve_charset_pools(policy)


def test_validation_rejects_no_adjacent_repeats_with_single_char_pool() -> None:
    policy = PasswordPolicy(
        length=4,
        use_uppercase=False,
        use_lowercase=True,
        use_digits=False,
        use_symbols=False,
        excluded_chars=LOWERCASE_CHARS[1:],
        no_adjacent_repeats=True,
    )
    with pytest.raises(PolicyValidationError, match="fewer than 2 unique characters"):
        resolve_charset_pools(policy)
