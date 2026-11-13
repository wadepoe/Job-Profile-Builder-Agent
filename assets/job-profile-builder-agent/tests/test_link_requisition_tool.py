"""Tests for link_requisition_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from link_requisition_tool import link_requisition_tool


def test_link_by_requisition_id():
    result_json = link_requisition_tool.invoke({
        "job_profile_code": "SSE-001",
        "requisition_id": "REQ-12345",
    })
    result = json.loads(result_json)
    assert result["job_profile_code"] == "SSE-001"
    assert "instruction" in result
    assert "REQ-12345" in result["instruction"]


def test_link_by_requisition_title():
    result_json = link_requisition_tool.invoke({
        "job_profile_code": "HR-200",
        "requisition_title": "HR Business Partner - EMEA",
    })
    result = json.loads(result_json)
    assert "HR Business Partner - EMEA" in result["instruction"]


def test_missing_profile_code_returns_error():
    result_json = link_requisition_tool.invoke({"job_profile_code": ""})
    result = json.loads(result_json)
    assert "error" in result


def test_missing_both_id_and_title_returns_error():
    result_json = link_requisition_tool.invoke({"job_profile_code": "SSE-001"})
    result = json.loads(result_json)
    assert "error" in result


def test_prefers_id_over_title():
    result_json = link_requisition_tool.invoke({
        "job_profile_code": "SSE-001",
        "requisition_id": "REQ-999",
        "requisition_title": "Some Title",
    })
    result = json.loads(result_json)
    assert result["requisition_lookup"].get("jobReqId") == "REQ-999"
