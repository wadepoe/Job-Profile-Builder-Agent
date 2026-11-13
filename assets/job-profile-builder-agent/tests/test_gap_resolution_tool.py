"""Tests for gap_resolution_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from gap_resolution_tool import gap_resolution_tool


def test_no_missing_fields_resolution_complete():
    fields = {"job_title": "Engineer", "job_code": "E001", "job_family": "Tech", "template_id": "T1"}
    confidence = {k: "found" for k in fields}
    result_json = gap_resolution_tool.invoke({
        "fields_json": json.dumps(fields),
        "confidence_json": json.dumps(confidence),
    })
    result = json.loads(result_json)
    assert result["resolution_complete"] is True
    assert result["sf_lookups"] == []
    assert result["user_questions"] == []


def test_missing_job_family_goes_to_sf_lookup():
    fields = {"job_title": "Engineer"}
    confidence = {"job_title": "found", "job_family": "missing", "job_code": "missing"}
    result_json = gap_resolution_tool.invoke({
        "fields_json": json.dumps(fields),
        "confidence_json": json.dumps(confidence),
    })
    result = json.loads(result_json)
    sf_fields = [l["field"] for l in result["sf_lookups"]]
    assert "job_family" in sf_fields
    assert "job_code" in sf_fields


def test_missing_competencies_go_to_skills_api():
    fields = {}
    confidence = {"competencies": "missing", "skills": "missing"}
    result_json = gap_resolution_tool.invoke({
        "fields_json": json.dumps(fields),
        "confidence_json": json.dumps(confidence),
    })
    result = json.loads(result_json)
    sf_fields = [(l["field"], l["api"]) for l in result["sf_lookups"]]
    assert ("competencies", "ECSkillsManagement") in sf_fields


def test_critical_missing_fields_identified():
    fields = {}
    confidence = {f: "missing" for f in ["job_title", "job_code", "job_family", "template_id"]}
    result_json = gap_resolution_tool.invoke({
        "fields_json": json.dumps(fields),
        "confidence_json": json.dumps(confidence),
    })
    result = json.loads(result_json)
    assert "job_title" in result["critical_missing"]
    assert "template_id" in result["critical_missing"]


def test_invalid_json_returns_error():
    result_json = gap_resolution_tool.invoke({
        "fields_json": "not json",
        "confidence_json": "{}",
    })
    result = json.loads(result_json)
    assert "error" in result
