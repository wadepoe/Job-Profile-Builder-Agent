"""
Job requisition linkage tool.
Optionally links a completed job profile to an open job requisition in SuccessFactors.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def link_requisition_tool(
    job_profile_code: str,
    requisition_id: str = "",
    requisition_title: str = "",
) -> str:
    """
    Link a completed job profile to a job requisition in SuccessFactors.
    The agent should use the Job Requisition MCP tool to confirm the requisition
    exists before calling this tool.

    Args:
        job_profile_code: The job profile's external code
        requisition_id: SuccessFactors job requisition ID (preferred)
        requisition_title: Job requisition title (used if ID not available)

    Returns:
        JSON with linkage instruction for the agent to execute via MCP tools.
    """
    if not job_profile_code.strip():
        return json.dumps({"error": "job_profile_code is required"})

    if not requisition_id and not requisition_title:
        return json.dumps({
            "error": "Either requisition_id or requisition_title must be provided."
        })

    lookup_field = "jobReqId" if requisition_id else "jobReqTitle"
    lookup_value = requisition_id or requisition_title

    logger.info(
        "Preparing requisition linkage for profile %s to requisition %s=%s",
        job_profile_code,
        lookup_field,
        lookup_value,
    )

    return json.dumps({
        "job_profile_code": job_profile_code,
        "requisition_lookup": {lookup_field: lookup_value},
        "instruction": (
            f"1. Use the Job Requisition MCP tool to look up the requisition "
            f"where {lookup_field} = '{lookup_value}' and confirm it exists.\n"
            f"2. If found, use the Generic Objects MCP tool to update the job profile "
            f"'{job_profile_code}' with the requisition reference.\n"
            f"3. If the write operation is not supported, return the profile code and "
            f"requisition ID to the user with instructions for manual linking in SuccessFactors."
        ),
    })
