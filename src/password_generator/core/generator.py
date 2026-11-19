"""Cryptographically secure secret generators using Python's ``secrets`` CSPRNG."""

import math
import secrets

from password_generator.core.charset import (
    BASE62_ALPHABET,
    DEFAULT_SYMBOL_CHARS,
    DIGIT_CHARS,
    resolve_charset_pools,
)
from password_generator.core.entropy import evaluate_secret
from password_generator.core.models import (
    GeneratedSecret,
    GenerationMode,
    PassphrasePolicy,
    PasswordPolicy,
    PinPolicy,
    PolicyValidationError,
    TokenFormat,
    TokenPolicy,
    WordCase,
)
from password_generator.data.wordlist import PASSPHRASE_WORDS

_CSPRNG = secrets.SystemRandom()

_VALID_TOKEN_BITS: frozenset[int] = frozenset({128, 192, 256, 384, 512})
MIN_PASSPHRASE_WORDS: int = 4
MAX_PASSPHRASE_WORDS: int = 12
MIN_PIN_LENGTH: int = 4
MAX_PIN_LENGTH: int = 16


def _has_adjacent_repeat(chars: list[str]) -> bool:
    return any(chars[i] == chars[i - 1] for i in range(1, len(chars)))


def _apply_no_adjacent_repeats(
    chars: list[str],
    combined_pool: str,
    *,
    active_pools: tuple[str, ...],
    lock_first_as_letter: bool,
    letter_pool: str,
) -> list[str]:
    """Repair adjacent duplicate characters via CSPRNG without losing class coverage."""
    if len(chars) <= 1:
        return chars

    # Special case: exact 2-character pool can only alternate cleanly.
    if len(combined_pool) == 2:
        a, b = combined_pool[0], combined_pool[1]
        if (lock_first_as_letter and a not in letter_pool) or (
            not lock_first_as_letter and _CSPRNG.randint(0, 1) == 1
        ):
            a, b = b, a
        return [a if idx % 2 == 0 else b for idx in range(len(chars))]

    result = list(chars)
    for idx in range(1, len(result)):
        if result[idx] == result[idx - 1]:
            forbidden = {result[idx - 1]}
            if idx + 1 < len(result):
                forbidden.add(result[idx + 1])

            # Swap with a later slot keeping neighbors distinct and class counts intact.
            swap_candidates = [
                j
                for j in range(idx + 1, len(result))
                if result[j] not in forbidden
                and result[idx] != result[j - 1]
                and (j + 1 >= len(result) or result[idx] != result[j + 1])
            ]
            if swap_candidates:
                swap_idx = secrets.choice(swap_candidates)
                result[idx], result[swap_idx] = result[swap_idx], result[idx]
            else:
                # Preserve any class where result[idx] is currently the sole representative.
                sole_pool: str | None = None
                for pool in active_pools:
                    if result[idx] in pool and sum(1 for ch in result if ch in pool) == 1:
                        sole_pool = pool
                        break

                candidate_pool = sole_pool if sole_pool is not None else combined_pool
                alternatives = [ch for ch in candidate_pool if ch not in forbidden]
                if not alternatives:
                    alternatives = [ch for ch in combined_pool if ch not in forbidden]
                if not alternatives:
                    raise PolicyValidationError(
                        "Unable to eliminate adjacent duplicate characters with current pool."
                    )
                result[idx] = secrets.choice(alternatives)

    return result


def _build_shuffled_password(
    length: int,
    active_pools: tuple[str, ...],
    combined_pool: str,
    *,
    start_with_letter: bool,
    letter_pool: str,
) -> list[str]:
    chars: list[str] = [secrets.choice(pool) for pool in active_pools]
    remaining = length - len(chars)
    chars.extend(secrets.choice(combined_pool) for _ in range(remaining))
    _CSPRNG.shuffle(chars)

    if start_with_letter and chars[0] not in letter_pool:
        letter_indices = [idx for idx, ch in enumerate(chars) if ch in letter_pool]
        if letter_indices:
            swap_idx = secrets.choice(letter_indices)
            chars[0], chars[swap_idx] = chars[swap_idx], chars[0]
        else:
            chars[0] = secrets.choice(letter_pool)
    return chars


def generate_password(policy: PasswordPolicy) -> GeneratedSecret:
    """Generate a high-entropy cryptographic random password obeying ``policy``."""
    pools = resolve_charset_pools(policy)

    chars = _build_shuffled_password(
        policy.length,
        pools.active_pools,
        pools.combined,
        start_with_letter=policy.start_with_letter,
        letter_pool=pools.letter_pool,
    )

    if policy.no_adjacent_repeats:
        for _ in range(32):
            if not _has_adjacent_repeat(chars):
                break
            chars = _build_shuffled_password(
                policy.length,
                pools.active_pools,
                pools.combined,
                start_with_letter=policy.start_with_letter,
                letter_pool=pools.letter_pool,
            )
        if _has_adjacent_repeat(chars):
            chars = _apply_no_adjacent_repeats(
                chars,
                pools.combined,
                active_pools=pools.active_pools,
                lock_first_as_letter=policy.start_with_letter,
                letter_pool=pools.letter_pool,
            )

    value = "".join(chars)
    pool_size = len(pools.combined)
    effective_pool = max(pool_size - 1, 1) if policy.no_adjacent_repeats else pool_size

    if policy.start_with_letter:
        first_bits = math.log2(len(pools.letter_pool))
        rest_bits = (policy.length - 1) * math.log2(effective_pool)
        known_bits = first_bits + rest_bits
    else:
        first_bits = math.log2(pool_size)
        rest_bits = (policy.length - 1) * math.log2(effective_pool)
        known_bits = first_bits + rest_bits

    report = evaluate_secret(
        value,
        known_entropy_bits=known_bits,
        charset_size_override=pool_size,
        skip_pattern_penalties=True,
    )
    summary = f"{policy.length}-char CSPRNG password ({pool_size}-char alphabet)"
    return GeneratedSecret(
        value=value,
        mode=GenerationMode.PASSWORD,
        report=report,
        summary=summary,
    )


def _format_word(word: str, word_case: WordCase) -> str:
    if word_case == WordCase.LOWER:
        return word.lower()
    if word_case == WordCase.TITLE:
        return word.capitalize()
    if word_case == WordCase.UPPER:
        return word.upper()
    style = secrets.randbelow(3)
    if style == 0:
        return word.lower()
    if style == 1:
        return word.capitalize()
    return word.upper()


def generate_passphrase(policy: PassphrasePolicy) -> GeneratedSecret:
    """Generate a Diceware-style cryptographic passphrase from the curated 4,096-word list."""
    if not (MIN_PASSPHRASE_WORDS <= policy.word_count <= MAX_PASSPHRASE_WORDS):
        raise PolicyValidationError(
            f"Word count must be between {MIN_PASSPHRASE_WORDS} and {MAX_PASSPHRASE_WORDS}."
        )
    if len(policy.separator) > 3 or any(ch in ("\n", "\r", "\t") for ch in policy.separator):
        raise PolicyValidationError(
            "Passphrase separator must be at most 3 single-line characters."
        )

    chosen_words = [
        _format_word(secrets.choice(PASSPHRASE_WORDS), policy.word_case)
        for _ in range(policy.word_count)
    ]

    extra_bits = 0.0
    if policy.word_case == WordCase.RANDOM_WORD:
        extra_bits += policy.word_count * math.log2(3)

    if policy.append_digit:
        chosen_words[-1] = f"{chosen_words[-1]}{secrets.choice(DIGIT_CHARS)}"
        extra_bits += math.log2(10)

    if policy.append_symbol:
        chosen_words[-1] = f"{chosen_words[-1]}{secrets.choice(DEFAULT_SYMBOL_CHARS)}"
        extra_bits += math.log2(len(DEFAULT_SYMBOL_CHARS))

    value = policy.separator.join(chosen_words)
    known_bits = policy.word_count * math.log2(len(PASSPHRASE_WORDS)) + extra_bits
    report = evaluate_secret(
        value,
        known_entropy_bits=known_bits,
        charset_size_override=len(PASSPHRASE_WORDS),
        skip_pattern_penalties=True,
    )
    summary = f"{policy.word_count}-word Diceware passphrase ({len(PASSPHRASE_WORDS)}-word list)"
    return GeneratedSecret(
        value=value,
        mode=GenerationMode.PASSPHRASE,
        report=report,
        summary=summary,
    )


def generate_token(policy: TokenPolicy) -> GeneratedSecret:
    """Generate a cryptographic API secret or high-entropy developer token."""
    if policy.bit_strength not in _VALID_TOKEN_BITS:
        raise PolicyValidationError("Token bit strength must be 128, 192, 256, 384, or 512.")

    sanitized_prefix = "".join(
        ch for ch in policy.prefix.strip() if ch.isascii() and not ch.isspace()
    )
    if len(sanitized_prefix) > 24:
        raise PolicyValidationError("Token prefix must be 24 characters or fewer.")

    num_bytes = policy.bit_strength // 8
    if policy.token_format == TokenFormat.HEX:
        core_token = secrets.token_hex(num_bytes)
        alphabet_size = 16
        format_label = "Hex"
    elif policy.token_format == TokenFormat.URLSAFE_B64:
        core_token = secrets.token_urlsafe(num_bytes)
        alphabet_size = 64
        format_label = "URL-Safe Base64"
    else:
        token_len = math.ceil(policy.bit_strength / math.log2(len(BASE62_ALPHABET)))
        core_token = "".join(secrets.choice(BASE62_ALPHABET) for _ in range(token_len))
        alphabet_size = len(BASE62_ALPHABET)
        format_label = "Base62"

    value = f"{sanitized_prefix}{core_token}"
    report = evaluate_secret(
        value,
        known_entropy_bits=float(policy.bit_strength),
        charset_size_override=alphabet_size,
        skip_pattern_penalties=True,
    )
    summary = f"{policy.bit_strength}-bit {format_label} cryptographic token"
    return GeneratedSecret(
        value=value,
        mode=GenerationMode.TOKEN,
        report=report,
        summary=summary,
    )


def _has_digit_sequence(pin: str) -> bool:
    """Return True if any 3 consecutive digits ascend or descend monotonically by 1."""
    for idx in range(len(pin) - 2):
        d0, d1, d2 = int(pin[idx]), int(pin[idx + 1]), int(pin[idx + 2])
        if (d1 - d0 == 1 and d2 - d1 == 1) or (d0 - d1 == 1 and d1 - d2 == 1):
            return True
    return False


def generate_pin(policy: PinPolicy) -> GeneratedSecret:
    """Generate a cryptographic numeric PIN with optional sequence/repetition guards."""
    if not (MIN_PIN_LENGTH <= policy.length <= MAX_PIN_LENGTH):
        raise PolicyValidationError(
            f"PIN length must be between {MIN_PIN_LENGTH} and {MAX_PIN_LENGTH}."
        )

    for _ in range(512):
        digits: list[str] = []
        for _ in range(policy.length):
            if policy.disallow_repeated_digits and digits:
                choices = [d for d in DIGIT_CHARS if d != digits[-1]]
                digits.append(secrets.choice(choices))
            else:
                digits.append(secrets.choice(DIGIT_CHARS))

        candidate = "".join(digits)
        if policy.disallow_repeated_digits and len(set(candidate)) < 2:
            continue
        if policy.disallow_sequences and _has_digit_sequence(candidate):
            continue

        effective_bits = (
            math.log2(10) + (policy.length - 1) * math.log2(9)
            if policy.disallow_repeated_digits
            else policy.length * math.log2(10)
        )
        report = evaluate_secret(
            candidate,
            known_entropy_bits=effective_bits,
            charset_size_override=10,
            skip_pattern_penalties=True,
        )
        summary = f"{policy.length}-digit hardened CSPRNG PIN"
        return GeneratedSecret(
            value=candidate,
            mode=GenerationMode.PIN,
            report=report,
            summary=summary,
        )

    raise PolicyValidationError("Failed to generate PIN satisfying constraints within retry limit.")


def generate_batch(
    mode: GenerationMode,
    count: int,
    *,
    password_policy: PasswordPolicy | None = None,
    passphrase_policy: PassphrasePolicy | None = None,
    token_policy: TokenPolicy | None = None,
    pin_policy: PinPolicy | None = None,
) -> list[GeneratedSecret]:
    """Generate ``count`` (1..20) distinct secrets for the active generation mode."""
    if not (1 <= count <= 20):
        raise PolicyValidationError("Batch count must be between 1 and 20.")

    results: list[GeneratedSecret] = []
    seen_values: set[str] = set()
    attempts = 0
    max_attempts = count * 10

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        if mode == GenerationMode.PASSWORD:
            item = generate_password(password_policy or PasswordPolicy())
        elif mode == GenerationMode.PASSPHRASE:
            item = generate_passphrase(passphrase_policy or PassphrasePolicy())
        elif mode == GenerationMode.TOKEN:
            item = generate_token(token_policy or TokenPolicy())
        else:
            item = generate_pin(pin_policy or PinPolicy())

        if item.value not in seen_values:
            seen_values.add(item.value)
            results.append(item)

    return results
