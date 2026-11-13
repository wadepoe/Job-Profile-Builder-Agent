"""
Integration test: Full single-profile flow
paste input → gap resolution → draft generation → review approval → CSV export delivery
"""
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from intake_tool import intake_tool
from gap_resolution_tool import gap_resolution_tool
from generate_profile_tool import generate_profile_tool
from deliver_profile_tool import deliver_profile_tool


def test_full_single_profile_flow_csv():
    """Test the complete pipeline from text intake to CSV export."""

    # Step 1: Intake
    intake_result = intake_tool.invoke({
        "source_type": "text",
        "content": (
            "Job Title: Cloud Solutions Architect\n"
            "Job Code: CSA-001\n"
            "Job Family: Technology\n"
            "Job Level: P5\n"
            "Responsibilities:\n"
            "- Design and implement cloud architectures\n"
            "- Lead technical discovery workshops\n"
            "Qualifications:\n"
            "- 8+ years of cloud experience\n"
            "- AWS/Azure/GCP certification preferred"
        ),
    })
    intake = json.loads(intake_result)
    assert intake["fields"]["job_title"] == "Cloud Solutions Architect"
    assert intake["confidence"]["job_title"] == "found"

    # Step 2: Gap resolution
    gap_result = gap_resolution_tool.invoke({
        "fields_json": json.dumps(intake["fields"]),
        "confidence_json": json.dumps(intake["confidence"]),
    })
    gaps = json.loads(gap_result)
    # template_id will be missing (not in source text) — should be flagged for SF or user
    assert "sf_lookups" in gaps or "user_questions" in gaps

    # Step 3: Generate profile (simulate resolved fields with template_id filled)
    resolved_fields = {
        "job_title": "Cloud Solutions Architect",
        "job_code": "CSA-001",
        "job_family": "Technology",
        "job_function": "Architecture",
        "job_level": "P5",
        "template_id": "TECH-TEMPLATE-001",
    }
    source_sections = {
        "responsibilities": "- Design and implement cloud architectures\n- Lead technical discovery workshops",
        "qualifications": "- 8+ years of cloud experience\n- AWS/Azure/GCP certification preferred",
    }
    template_sections = ["purpose", "responsibilities", "qualifications", "competencies"]

    gen_result = generate_profile_tool.invoke({
        "resolved_fields_json": json.dumps(resolved_fields),
        "template_sections_json": json.dumps(template_sections),
        "source_sections_json": json.dumps(source_sections),
    })
    profile_draft = json.loads(gen_result)
    assert profile_draft["sections_populated"] == len(template_sections)
    assert profile_draft["job_title"] == "Cloud Solutions Architect"

    # Step 4: Deliver as CSV (simulating user approval)
    deliver_result = deliver_profile_tool.invoke({
        "profile_json": json.dumps(profile_draft),
        "output_mode": "csv_export",
    })
    delivery = json.loads(deliver_result)
    assert delivery["mode"] == "csv_export"
    assert delivery["status"] == "success"
    assert "CSA-001" in delivery["content"]
    assert "Cloud Solutions Architect" in delivery["content"]
    assert delivery["filename"].endswith(".csv")


def test_full_flow_api_write_fallback():
    """Test that API write mode prepares correct payload for MCP tool."""
    profile = {
        "job_title": "Test Role",
        "job_code": "TR-001",
        "job_family": "Test Family",
        "job_function": "Testing",
        "job_level": "P1",
        "template_id": "TEST-TEMPLATE",
        "sections": [
            {"section_type": "purpose", "content": "Test purpose.", "source": "ai_generated"},
        ],
    }
    result_json = deliver_profile_tool.invoke({
        "profile_json": json.dumps(profile),
        "output_mode": "api_write",
    })
    result = json.loads(result_json)
    assert result["mode"] == "api_write"
    assert result["payload"]["objectType"] == "JobProfile"
    assert "fallback_note" in result
