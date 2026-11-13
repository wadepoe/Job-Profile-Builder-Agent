"""Tests for guardrail_check utility."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from guardrail_check import guardrail_check, clean_content


def test_clean_content_passes():
    result = guardrail_check("The candidate will lead a team of engineers.")
    assert result.clean is True
    assert result.flagged_phrases == []


def test_gendered_term_flagged():
    result = guardrail_check("The chairman will oversee the department.")
    assert result.clean is False
    assert any("chairman" in p.lower() for p in result.flagged_phrases)


def test_manpower_flagged():
    result = guardrail_check("We need more manpower for this project.")
    assert result.clean is False


def test_clean_content_fixes_chairman():
    cleaned = clean_content("The chairman approved the budget.")
    assert "chairperson" in cleaned
    assert "chairman" not in cleaned


def test_clean_content_fixes_manpower():
    cleaned = clean_content("We need more manpower.")
    assert "workforce" in cleaned


def test_empty_string_passes():
    result = guardrail_check("")
    assert result.clean is True


def test_professional_content_passes():
    content = (
        "The candidate will be responsible for managing a portfolio of projects, "
        "collaborating with cross-functional teams, and driving business outcomes."
    )
    result = guardrail_check(content)
    assert result.clean is True
