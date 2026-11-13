"""Tests for deliver_profile_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from deliver_profile_tool import deliver_profile_tool, _build_csv, _build_document

_PROFILE = {
    "job_title": "Data Analyst",
    "job_code": "DA-101",
    "job_family": "Analytics",
    "job_function": "Data",
    "job_level": "P3",
    "template_id": "ANALYTICS-TEMPLATE",
    "sections": [
        {"section_type": "purpose", "content": "Analyzes data to support decisions.", "source": "ai_generated"},
        {"section_type": "responsibilities", "content": "Build dashboards and reports.", "source": "doc_extracted"},
    ],
}


def test_api_write_mode_returns_payload():
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(_PROFILE),
        "output_mode": "api_write",
    })
    result = json.loads(result_json)
    assert result["mode"] == "api_write"
    assert result["status"] == "ready"
    assert "payload" in result
    assert result["payload"]["externalCode"] == "DA-101"


def test_csv_export_mode_returns_csv():
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(_PROFILE),
        "output_mode": "csv_export",
    })
    result = json.loads(result_json)
    assert result["mode"] == "csv_export"
    assert result["status"] == "success"
    assert "DA-101" in result["content"]
    assert "filename" in result


def test_csv_contains_all_sections():
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(_PROFILE),
        "output_mode": "csv_export",
    })
    result = json.loads(result_json)
    assert "purpose" in result["content"]
    assert "responsibilities" in result["content"]


def test_document_mode_returns_markdown():
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(_PROFILE),
        "output_mode": "document",
    })
    result = json.loads(result_json)
    assert result["mode"] == "document"
    assert "# Job Profile: Data Analyst" in result["content"]
    assert "DA-101" in result["content"]


def test_unknown_mode_returns_error():
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(_PROFILE),
        "output_mode": "fax",
    })
    result = json.loads(result_json)
    assert "error" in result


def test_invalid_profile_json_returns_error():
    result_json = deliver_profile_tool.invoke({
        "profile_json": "not json",
        "output_mode": "csv_export",
    })
    result = json.loads(result_json)
    assert "error" in result


def test_build_csv_has_header():
    csv = _build_csv(_PROFILE)
    assert "profile_external_code" in csv
    assert "section_type" in csv


def test_build_document_has_all_sections():
    doc = _build_document(_PROFILE)
    assert "Purpose" in doc
    assert "Responsibilities" in doc
