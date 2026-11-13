"""
Content guardrail utility for job profile generation.
Scans generated content for discriminatory language patterns before
presenting to users, ensuring regulatory-safe and inclusive content.
"""

import re
from typing import NamedTuple


class GuardrailResult(NamedTuple):
    clean: bool
    flagged_phrases: list[str]


# Configurable blocklist — add organisation-specific terms as needed
_PROHIBITED_PATTERNS = [
    # Age-related
    r"\byoung\b", r"\brecent\s+graduate\b", r"\bdigital\s+native\b",
    r"\benergetic\s+young\b", r"\bage\s+\d+", r"\bunder\s+\d+\s+years\b",
    # Gendered language
    r"\bhe\s+will\b", r"\bshe\s+will\b", r"\bhis\s+\b", r"\bher\s+\b",
    r"\bmanpower\b", r"\bchairman\b", r"\bstewardess\b", r"\bfireman\b",
    r"\bpoliceman\b", r"\bforefathers\b", r"\bworkingman\b",
    # Physical requirements language (non-essential)
    r"\bmust\s+be\s+physically\s+fit\b", r"\bable\s+bodied\b",
    # Protected class references (unless legitimately required)
    r"\bnative\s+english\s+speaker\b", r"\bmother\s+tongue\b",
    r"\bno\s+disability\b", r"\bnot\s+disabled\b",
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), p) for p in _PROHIBITED_PATTERNS]


def guardrail_check(content: str) -> GuardrailResult:
    """
    Check content for discriminatory or non-compliant language.

    Args:
        content: The generated text to check.

    Returns:
        GuardrailResult with clean=True if no issues found,
        or clean=False with list of flagged phrases if issues detected.
    """
    flagged = []
    for pattern, raw in _COMPILED_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            flagged.extend(matches)

    return GuardrailResult(clean=len(flagged) == 0, flagged_phrases=flagged)


def clean_content(content: str) -> str:
    """
    Apply basic automatic fixes for known patterns.
    Returns cleaned content — callers should re-run guardrail_check after.
    """
    fixes = {
        r"\bmanpower\b": "workforce",
        r"\bchairman\b": "chairperson",
        r"\bstewardess\b": "flight attendant",
        r"\bfireman\b": "firefighter",
        r"\bpoliceman\b": "police officer",
    }
    result = content
    for pattern, replacement in fixes.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result
