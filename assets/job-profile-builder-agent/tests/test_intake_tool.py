"""Tests for intake_tool."""
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from intake_tool import intake_tool, _extract_fields_from_text


def test_text_intake_extracts_title():
    result_json = intake_tool.invoke({
        "source_type": "text",
        "content": "Job Title: Senior Data Scientist\nJob Code: DS-101\nJob Family: Analytics",
    })
    result = json.loads(result_json)
    assert result["fields"].get("job_title") == "Senior Data Scientist"
    assert result["confidence"]["job_title"] == "found"


def test_text_intake_empty_content_returns_error():
    result_json = intake_tool.invoke({"source_type": "text", "content": ""})
    result = json.loads(result_json)
    assert "error" in result


def test_clone_intake_sets_clone_source():
    result_json = intake_tool.invoke({
        "source_type": "clone",
        "clone_profile_code": "SE-001",
    })
    result = json.loads(result_json)
    assert result["fields"]["clone_source"] == "SE-001"
    assert result["confidence"]["clone_source"] == "found"


def test_clone_intake_missing_code_returns_error():
    result_json = intake_tool.invoke({"source_type": "clone"})
    result = json.loads(result_json)
    assert "error" in result


def test_verbal_intake():
    result_json = intake_tool.invoke({
        "source_type": "verbal",
        "content": "I need a profile for a Product Manager level 3.",
    })
    result = json.loads(result_json)
    assert result["source_type"] == "verbal"


def test_unknown_source_type_returns_error():
    result_json = intake_tool.invoke({"source_type": "unknown"})
    result = json.loads(result_json)
    assert "error" in result


def test_extract_fields_from_structured_text():
    text = "Job Title: HR Business Partner\nJob Code: HR-200\nLevel: M2\n\nResponsibilities:\nManage employee relations\nCoach managers"
    result = _extract_fields_from_text(text)
    assert result["fields"]["job_title"] == "HR Business Partner"
    assert result["fields"]["job_code"] == "HR-200"
    assert "responsibilities" in result["fields"]


def test_file_intake_missing_path_returns_error():
    result_json = intake_tool.invoke({"source_type": "file"})
    result = json.loads(result_json)
    assert "error" in result


def test_file_intake_text_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Job Title: Test Engineer\nJob Code: TE-001\n")
        path = f.name
    try:
        result_json = intake_tool.invoke({"source_type": "file", "file_path": path})
        result = json.loads(result_json)
        assert result["fields"].get("job_title") == "Test Engineer"
    finally:
        os.unlink(path)
