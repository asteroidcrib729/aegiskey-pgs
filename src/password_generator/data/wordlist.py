"""Packaged loader for the curated 4,096-word A-Z English Diceware dictionary."""

from importlib import resources


def _load_wordlist() -> tuple[str, ...]:
    text = (
        resources.files("password_generator.data")
        .joinpath("wordlist.txt")
        .read_text(encoding="utf-8")
    )
    return tuple(line.strip() for line in text.splitlines() if line.strip())


PASSPHRASE_WORDS: tuple[str, ...] = _load_wordlist()
