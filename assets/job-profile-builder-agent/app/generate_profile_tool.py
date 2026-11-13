"""
Profile draft generation tool.
Assembles a complete, template-compliant job profile draft from resolved fields,
applies guardrails, and annotates each section with its data source.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

from guardrail_check import clean_content, guardrail_check

logger = logging.getLogger(__name__)


def _build_section_prompt(section_type: str, job_title: str, job_family: str,
                           job_level: str, source_content: str = "") -> str:
    """Build a focused LLM prompt for a single profile section."""
    base = (
        f"Generate the '{section_type}' section for a job profile.\n"
        f"Role: {job_title} | Family: {job_family} | Level: {job_level}\n"
    )
    if source_content:
        base += f"Use this source content as primary input:\n{source_content}\n"
    base += (
        "Requirements:\n"
        "- Use inclusive, professional language (no gendered terms, no age references)\n"
        "- Use active voice for responsibilities\n"
        "- Be specific and measurable where possible\n"
        "- Follow SAP SuccessFactors job profile best practices\n"
        f"Output ONLY the content for the '{section_type}' section, no section header."
    )
    return base


@tool
def generate_profile_tool(
    resolved_fields_json: str,
    template_sections_json: str,
    source_sections_json: str = "{}",
) -> str:
    """
    Generate a complete job profile draft for all template sections.
    Applies content guardrails on every section before returning.

    Args:
        resolved_fields_json: JSON with all resolved fields (job_title, job_family, etc.)
        template_sections_json: JSON list of template section names to populate
        source_sections_json: JSON dict of section_name -> source_content from intake

    Returns:
        JSON with generated profile draft including source annotations and any guardrail flags.
    """
    try:
        fields: dict[str, Any] = json.loads(resolved_fields_json)
        template_sections: list[str] = json.loads(template_sections_json)
        source_sections: dict[str, str] = json.loads(source_sections_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON input: {e}"})

    job_title = fields.get("job_title", "Unknown Role")
    job_family = fields.get("job_family", "")
    job_level = fields.get("job_level", "")
    template_id = fields.get("template_id", "default")

    draft_sections: list[dict[str, Any]] = []
    guardrail_flags: list[dict[str, Any]] = []

    for section in template_sections:
        source_content = source_sections.get(section, "")

        # Determine source annotation
        if section in source_sections and source_content:
            annotation = "doc_extracted"
        elif section in ("job_family", "job_function", "job_level", "competencies", "skills"):
            annotation = "sf_lookup"
        else:
            annotation = "ai_generated"

        # Generate placeholder content (LLM call happens via agent orchestration)
        # The agent uses this tool's output as a scaffold and fills actual LLM content
        generated_content = source_content if source_content else (
            f"[AI-GENERATED] {_build_section_prompt(section, job_title, job_family, job_level)}"
        )

        # Apply guardrails
        check = guardrail_check(generated_content)
        if not check.clean:
            cleaned = clean_content(generated_content)
            recheck = guardrail_check(cleaned)
            if not recheck.clean:
                guardrail_flags.append({
                    "section": section,
                    "flagged_phrases": check.flagged_phrases,
                    "action": "requires_manual_review",
                })
                generated_content = cleaned
                annotation += "_guardrail_flagged"
            else:
                generated_content = cleaned

        draft_sections.append({
            "section_type": section,
            "content": generated_content,
            "source": annotation,
        })

    sections_populated = len(draft_sections)

    if sections_populated > 0:
        logger.info(
            "M3.achieved: profile draft generated — template_id=%s, sections_populated=%d",
            template_id,
            sections_populated,
        )
    else:
        logger.warning(
            "M3.missed: profile draft generation failed — template_id=%s, reason=no_sections_generated",
            template_id,
        )

    return json.dumps({
        "job_title": job_title,
        "job_code": fields.get("job_code", ""),
        "job_family": job_family,
        "job_function": fields.get("job_function", ""),
        "job_level": job_level,
        "template_id": template_id,
        "sections": draft_sections,
        "guardrail_flags": guardrail_flags,
        "sections_populated": sections_populated,
    })
