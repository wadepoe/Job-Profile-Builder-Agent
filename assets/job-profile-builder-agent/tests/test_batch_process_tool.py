"""Tests for batch_process_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from batch_process_tool import batch_process_tool, _parse_csv_batch, _parse_list_batch

_VALID_CSV = """job_title,job_code,job_family,job_level
Software Engineer,SE-001,Technology,P3
Product Manager,PM-001,Product,M2
"""

_LIST_INPUT = "Software Engineer\nProduct Manager\nData Analyst"


def test_csv_parsing_returns_correct_count():
    rows, errors = _parse_csv_batch(_VALID_CSV)
    assert len(rows) == 2
    assert errors == []


def test_csv_missing_job_title_returns_error():
    csv = "job_code,job_family\nSE-001,Tech\n"
    rows, errors = _parse_csv_batch(csv)
    assert rows == []
    assert len(errors) > 0


def test_csv_empty_title_row_skipped():
    csv = "job_title,job_code\n,SE-001\nEngineer,SE-002\n"
    rows, errors = _parse_csv_batch(csv)
    assert len(rows) == 1
    assert len(errors) == 1


def test_list_parsing_returns_correct_count():
    rows = _parse_list_batch(_LIST_INPUT)
    assert len(rows) == 3
    assert rows[0]["job_title"] == "Software Engineer"


def test_batch_csv_processes_roles():
    result_json = batch_process_tool.invoke({
        "batch_content": _VALID_CSV,
        "batch_format": "csv",
        "output_mode": "csv_export",
    })
    result = json.loads(result_json)
    assert result["total_roles"] == 2
    assert result["profiles_generated"] + result["profiles_flagged"] + result["profiles_failed"] == 2


def test_batch_list_processes_roles():
    result_json = batch_process_tool.invoke({
        "batch_content": _LIST_INPUT,
        "batch_format": "list",
    })
    result = json.loads(result_json)
    assert result["total_roles"] == 3


def test_batch_empty_input_returns_error():
    result_json = batch_process_tool.invoke({
        "batch_content": "",
        "batch_format": "list",
    })
    result = json.loads(result_json)
    assert "error" in result


def test_batch_unknown_format_returns_error():
    result_json = batch_process_tool.invoke({
        "batch_content": "something",
        "batch_format": "xml",
    })
    result = json.loads(result_json)
    assert "error" in result


def test_batch_summary_contains_required_fields():
    result_json = batch_process_tool.invoke({
        "batch_content": _LIST_INPUT,
        "batch_format": "list",
    })
    result = json.loads(result_json)
    assert "total_roles" in result
    assert "profiles_generated" in result
    assert "profiles_flagged" in result
    assert "profiles_failed" in result
