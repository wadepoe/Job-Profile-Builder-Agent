"""Tests for find_similar_profiles_tool."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from find_similar_profiles_tool import find_similar_profiles_tool, _similarity_score

_PROFILES = [
    {"job_title": "Senior Software Engineer", "job_code": "SSE-001", "job_family": "Technology", "job_level": "P4"},
    {"job_title": "Junior Software Engineer", "job_code": "JSE-001", "job_family": "Technology", "job_level": "P2"},
    {"job_title": "HR Business Partner", "job_code": "HR-200", "job_family": "Human Resources", "job_level": "M2"},
    {"job_title": "Data Scientist", "job_code": "DS-001", "job_family": "Analytics", "job_level": "P3"},
]


def test_returns_top_3_matches():
    result_json = find_similar_profiles_tool.invoke({
        "job_title": "Software Engineer",
        "profiles_json": json.dumps(_PROFILES),
    })
    result = json.loads(result_json)
    assert len(result["top_matches"]) <= 3


def test_most_similar_is_ranked_first():
    result_json = find_similar_profiles_tool.invoke({
        "job_title": "Senior Software Engineer",
        "job_family": "Technology",
        "profiles_json": json.dumps(_PROFILES),
    })
    result = json.loads(result_json)
    assert result["top_matches"][0]["job_title"] == "Senior Software Engineer"


def test_empty_profiles_returns_note():
    result_json = find_similar_profiles_tool.invoke({
        "job_title": "Engineer",
        "profiles_json": "[]",
    })
    result = json.loads(result_json)
    assert result["top_matches"] == []
    assert "note" in result


def test_empty_job_title_returns_error():
    result_json = find_similar_profiles_tool.invoke({
        "job_title": "",
        "profiles_json": "[]",
    })
    result = json.loads(result_json)
    assert "error" in result


def test_similarity_score_exact_match():
    candidate = {"job_title": "Senior Software Engineer", "job_family": "Technology", "job_function": "", "job_level": "P4"}
    score = _similarity_score(candidate, "Senior Software Engineer", "Technology")
    assert score > 0.5


def test_similarity_score_no_overlap():
    candidate = {"job_title": "Chef", "job_family": "Culinary", "job_function": "", "job_level": ""}
    score = _similarity_score(candidate, "Software Engineer", "Technology")
    assert score == 0.0


def test_invalid_profiles_json_returns_error():
    result_json = find_similar_profiles_tool.invoke({
        "job_title": "Engineer",
        "profiles_json": "not json",
    })
    result = json.loads(result_json)
    assert "error" in result
