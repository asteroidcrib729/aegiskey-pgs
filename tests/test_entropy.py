"""Unit tests for entropy calculation, weakness heuristics, and duration formatting."""

from password_generator.core.entropy import evaluate_secret, format_duration
from password_generator.core.models import SecurityTier


def test_empty_secret_reports_critical_zero() -> None:
    report = evaluate_secret("")
    assert report.score == 0
    assert report.entropy_bits == 0.0
    assert report.tier == SecurityTier.CRITICAL
    assert report.warnings


def test_weak_keyboard_and_sequence_patterns_trigger_warnings() -> None:
    report = evaluate_secret("qwerty123456")
    assert report.tier in (SecurityTier.CRITICAL, SecurityTier.WEAK, SecurityTier.FAIR)
    assert any("keyboard walk" in w.lower() for w in report.warnings)
    assert any("sequential" in w.lower() for w in report.warnings)
    assert report.effective_bits < report.entropy_bits


def test_repeated_character_secret_receives_diversity_penalty() -> None:
    report = evaluate_secret("aaaaaaaaaa")
    assert any("diversity" in w.lower() or "repeated" in w.lower() for w in report.warnings)
    assert report.tier == SecurityTier.CRITICAL


def test_quantum_resistant_secret_scores_100() -> None:
    report = evaluate_secret(
        "X9!kP4#mQ2@vL7$zW5^rT8&n",
        known_entropy_bits=157.0,
        charset_size_override=94,
        skip_pattern_penalties=True,
    )
    assert report.score == 100
    assert report.tier == SecurityTier.QUANTUM_RESISTANT
    assert len(report.attack_estimates) == 3
    assert "universe age" in report.attack_estimates[-1].human_duration


def test_format_duration_scales_cleanly() -> None:
    assert format_duration(0.2) == "Instantly (< 1 sec)"
    assert format_duration(45.0) == "45.0 sec"
    assert format_duration(180.0) == "3.0 min"
    assert format_duration(7200.0) == "2.0 hours"
    assert format_duration(172800.0) == "2.0 days"
