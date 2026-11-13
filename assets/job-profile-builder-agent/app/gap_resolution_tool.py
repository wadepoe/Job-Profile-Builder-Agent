"""
Gap resolution tool for job profile generation.
Resolves missing fields by querying SuccessFactors APIs before asking the user.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Fields and their preferred SuccessFactors resolution source
FIELD_RESOLUTION_MAP = {
    "job_family": "generic_objects",       # PLTGenericObjects
    "job_function": "generic_objects",
    "job_level": "generic_objects",
    "job_code": "generic_objects",
    "template_id": "generic_objects",
    "competencies": "skills_management",   # ECSkillsManagement
    "skills": "skills_management",
    "position_context": "position_mgmt",   # ECPositionManagement
}


@tool
def gap_resolution_tool(
    fields_json: str,
    confidence_json: str,
    position_id: str = "",
) -> str:
    """
    Analyze extracted job profile fields and identify which gaps can be resolved
    from SuccessFactors. Returns resolution guidance for the agent.

    Args:
        fields_json: JSON string of extracted fields from intake_tool
        confidence_json: JSON string of confidence flags from intake_tool
        position_id: Optional SuccessFactors position ID for context enrichment

    Returns:
        JSON with resolution plan: which fields to look up from SF and which to ask the user
    """
    try:
        fields: dict[str, Any] = json.loads(fields_json)
        confidence: dict[str, str] = json.loads(confidence_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON input: {e}"})

    missing_fields = [f for f, c in confidence.items() if c == "missing"]
    sf_lookups: list[dict[str, str]] = []
    user_questions: list[str] = []

    for field in missing_fields:
        source = FIELD_RESOLUTION_MAP.get(field)
        if source == "generic_objects":
            sf_lookups.append({
                "field": field,
                "api": "PLTGenericObjects",
                "instruction": f"Query Generic Objects API to find valid {field} values. Filter by job_title or job_family context if available.",
            })
        elif source == "skills_management":
            sf_lookups.append({
                "field": field,
                "api": "ECSkillsManagement",
                "instruction": f"Query Skills Management API for competency/skill profiles relevant to this job title and family.",
            })
        elif source == "position_mgmt" and position_id:
            sf_lookups.append({
                "field": field,
                "api": "ECPositionManagement",
                "instruction": f"Query Position Management API for position {position_id} to get contextual data.",
            })
        else:
            # Cannot resolve from SF — must ask user
            user_questions.append(field)

    # Core fields that MUST be resolved before generation
    critical_missing = [
        f for f in ["job_title", "job_code", "job_family", "template_id"]
        if confidence.get(f) == "missing"
    ]

    result = {
        "fields_found": [f for f, c in confidence.items() if c in ("found", "inferred")],
        "sf_lookups": sf_lookups,
        "user_questions": user_questions,
        "critical_missing": critical_missing,
        "resolution_complete": len(missing_fields) == 0,
    }

    if not missing_fields:
        logger.info(
            "M2.achieved: all required fields resolved — fields_from_sf=%d, fields_from_user=0",
            len([f for f, c in confidence.items() if c == "found"]),
        )
    else:
        sf_count = len(sf_lookups)
        user_count = len(user_questions)
        logger.info(
            "Gap resolution plan: %d SF lookups, %d user questions needed for missing fields: %s",
            sf_count, user_count, missing_fields,
        )

    return json.dumps(result)
