"""Tests verifying built-in 2026 security presets end-to-end."""

from password_generator.core.generator import (
    generate_passphrase,
    generate_password,
    generate_pin,
    generate_token,
)
from password_generator.core.models import GenerationMode
from password_generator.core.presets import SECURITY_PRESETS, get_preset_by_key


def test_all_presets_generate_valid_secrets() -> None:
    assert len(SECURITY_PRESETS) >= 5
    for preset in SECURITY_PRESETS:
        assert get_preset_by_key(preset.key) == preset
        if preset.mode == GenerationMode.PASSWORD and preset.password_policy is not None:
            out = generate_password(preset.password_policy)
        elif preset.mode == GenerationMode.PASSPHRASE and preset.passphrase_policy is not None:
            out = generate_passphrase(preset.passphrase_policy)
        elif preset.mode == GenerationMode.TOKEN and preset.token_policy is not None:
            out = generate_token(preset.token_policy)
        elif preset.mode == GenerationMode.PIN and preset.pin_policy is not None:
            out = generate_pin(preset.pin_policy)
        else:
            raise AssertionError(f"Preset {preset.key} missing policy for mode {preset.mode}")

        assert out.value
        assert out.report.effective_bits > 0.0
