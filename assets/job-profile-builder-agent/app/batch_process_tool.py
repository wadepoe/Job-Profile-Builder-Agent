"""
Batch profile processing tool.
Processes a CSV file or line-delimited list of job roles and generates
profiles for all of them, with rate-limit management and batch summary.
"""

import asyncio
import csv
import io
import json
import logging
import time
from typing import Any

from langchain_core.tools import tool

from guardrail_check import guardrail_check

logger = logging.getLogger(__name__)

# Required CSV columns
_OPTIONAL_COLUMNS = {"job_code", "job_family", "job_function", "job_level", "template_id", "source_text"}


def _parse_csv_batch(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse CSV batch input. Returns (valid_rows, error_messages)."""
    rows = []
    errors = []
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        return [], ["CSV has no headers"]

    headers = {h.lower().strip() for h in reader.fieldnames}
    if "job_title" not in headers:
        errors.append("CSV is missing required column 'job_title'")
        return [], errors

    for i, row in enumerate(reader, start=2):
        title = row.get("job_title", "").strip()
        if not title:
            errors.append(f"Row {i}: job_title is empty — skipped")
            continue
        rows.append({
            "job_title": title,
            "job_code": row.get("job_code", "").strip(),
            "job_family": row.get("job_family", "").strip(),
            "job_function": row.get("job_function", "").strip(),
            "job_level": row.get("job_level", "").strip(),
            "template_id": row.get("template_id", "").strip(),
            "source_text": row.get("source_text", "").strip(),
        })

    return rows, errors


def _parse_list_batch(content: str) -> list[dict[str, Any]]:
    """Parse newline-delimited list of role names."""
    rows = []
    for line in content.strip().split("\n"):
        title = line.strip()
        if title:
            rows.append({"job_title": title})
    return rows


def _process_single_role(role: dict[str, Any]) -> dict[str, Any]:
    """
    Process a single role synchronously (for batch context).
    Returns the outcome dict.
    """
    title = role.get("job_title", "Unknown")

    # Identify missing fields
    missing = []
    for field in ["job_code", "job_family", "job_level", "template_id"]:
        if not role.get(field):
            missing.append(field)

    if len(missing) >= 4:
        # All structural fields missing — flag for manual input
        return {
            "job_title": title,
            "status": "flagged",
            "reason": f"Missing required fields: {', '.join(missing)}",
            "missing_fields": missing,
        }

    # Simulate generation — in production the agent drives this via MCP tools
    sections = []
    for section_type in ["purpose", "responsibilities", "qualifications", "competencies"]:
        content = f"[Generated content for {section_type} of {title}]"
        check = guardrail_check(content)
        sections.append({
            "section_type": section_type,
            "content": content,
            "source": "ai_generated",
            "guardrail_clean": check.clean,
        })

    return {
        "job_title": title,
        "job_code": role.get("job_code", ""),
        "status": "generated",
        "sections": sections,
        "missing_fields": missing,
    }


@tool
def batch_process_tool(
    batch_content: str,
    batch_format: str = "csv",
    output_mode: str = "csv_export",
) -> str:
    """
    Process a batch of job roles and generate profiles for all of them.

    Args:
        batch_content: CSV string or newline-delimited list of role names
        batch_format: 'csv' or 'list'
        output_mode: 'csv_export', 'api_write', or 'document' (default: csv_export)

    Returns:
        JSON with batch summary and generated profiles.
    """
    # Parse input
    parse_errors: list[str] = []
    if batch_format == "csv":
        roles, parse_errors = _parse_csv_batch(batch_content)
    elif batch_format == "list":
        roles = _parse_list_batch(batch_content)
    else:
        return json.dumps({"error": f"Unknown batch_format: '{batch_format}'. Use 'csv' or 'list'."})

    if not roles:
        logger.warning(
            "M6.missed: batch run did not complete — roles_processed=0, reason=no_valid_roles_in_input"
        )
        return json.dumps({
            "error": "No valid roles found in batch input.",
            "parse_errors": parse_errors,
        })

    total_roles = len(roles)
    generated = []
    flagged = []
    failed = []

    for i, role in enumerate(roles):
        # Rate-limit pause between roles
        if i > 0:
            time.sleep(0.2)

        retries = 0
        max_retries = 3
        delay = 1.0

        while retries <= max_retries:
            try:
                outcome = _process_single_role(role)
                if outcome["status"] == "generated":
                    generated.append(outcome)
                elif outcome["status"] == "flagged":
                    flagged.append(outcome)
                break
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    failed.append({
                        "job_title": role.get("job_title", "Unknown"),
                        "status": "failed",
                        "error": str(e),
                    })
                    break
                time.sleep(min(delay, 30.0))
                delay *= 2

    profiles_generated = len(generated)
    profiles_flagged = len(flagged)
    profiles_failed = len(failed)

    if profiles_generated > 0 or profiles_flagged > 0:
        logger.info(
            "M6.achieved: batch run completed — total_roles=%d, profiles_generated=%d, flagged=%d",
            total_roles,
            profiles_generated,
            profiles_flagged,
        )
    else:
        logger.warning(
            "M6.missed: batch run did not complete — roles_processed=%d, reason=all_roles_failed",
            total_roles,
        )

    summary = {
        "total_roles": total_roles,
        "profiles_generated": profiles_generated,
        "profiles_flagged": profiles_flagged,
        "profiles_failed": profiles_failed,
        "output_mode": output_mode,
        "parse_errors": parse_errors,
        "flagged_roles": [
            {"job_title": r["job_title"], "missing_fields": r.get("missing_fields", [])}
            for r in flagged
        ],
        "failed_roles": [
            {"job_title": r["job_title"], "error": r.get("error", "")}
            for r in failed
        ],
        "generated_profiles": generated,
    }

    return json.dumps(summary)
