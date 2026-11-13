"""Tests for generate_profile_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from generate_profile_tool import generate_profile_tool


_FIELDS = {
    "job_title": "Senior Software Engineer",
    "job_code": "SSE-001",
    "job_family": "Technology",
    "job_function": "Engineering",
    "job_level": "P4",
    "template_id": "TECH-TEMPLATE-001",
}
_SECTIONS = ["purpose", "responsibilities", "qualifications", "competencies"]


def test_generates_all_sections():
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(_FIELDS),
        "template_sections_json": json.dumps(_SECTIONS),
    })
    result = json.loads(result_json)
    assert result["sections_populated"] == len(_SECTIONS)
    assert len(result["sections"]) == len(_SECTIONS)


def test_sections_have_source_annotation():
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(_FIELDS),
        "template_sections_json": json.dumps(_SECTIONS),
    })
    result = json.loads(result_json)
    for section in result["sections"]:
        assert "source" in section
        assert section["source"] != ""


def test_source_content_uses_doc_extracted():
    source = {"responsibilities": "Lead technical architecture decisions."}
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(_FIELDS),
        "template_sections_json": json.dumps(["responsibilities"]),
        "source_sections_json": json.dumps(source),
    })
    result = json.loads(result_json)
    assert result["sections"][0]["source"] == "doc_extracted"
    assert "Lead technical architecture" in result["sections"][0]["content"]


def test_guardrail_flags_discriminatory_content():
    fields = dict(_FIELDS)
    source = {"purpose": "Looking for a young and energetic chairman for this role."}
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(fields),
        "template_sections_json": json.dumps(["purpose"]),
        "source_sections_json": json.dumps(source),
    })
    result = json.loads(result_json)
    # Should be flagged or cleaned
    section = result["sections"][0]
    # Content should either be cleaned or guardrail flagged
    assert "guardrail_flagged" in section["source"] or "chairman" not in section["content"].lower()


def test_empty_sections_returns_zero_populated():
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(_FIELDS),
        "template_sections_json": json.dumps([]),
    })
    result = json.loads(result_json)
    assert result["sections_populated"] == 0


def test_invalid_json_returns_error():
    result_json = generate_profile_tool.invoke({
        "resolved_fields_json": "not json",
        "template_sections_json": "[]",
    })
    result = json.loads(result_json)
    assert "error" in result
