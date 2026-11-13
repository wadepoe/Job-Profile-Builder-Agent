"""
Source data intake tool for job profile generation.
Accepts content in multiple formats (text, file, clone instruction, verbal)
and extracts structured job profile fields with confidence annotations.
"""

import json
import logging
import os
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Standard job profile fields we attempt to extract
PROFILE_FIELDS = [
    "job_title", "job_code", "job_family", "job_function", "job_level",
    "template_id", "purpose", "responsibilities", "qualifications",
    "competencies", "skills", "physical_requirements", "additional_information",
]


def _extract_fields_from_text(text: str) -> dict[str, Any]:
    """
    Extract job profile fields from raw text using heuristic keyword matching.
    Returns dict with field values and confidence flags.
    """
    fields: dict[str, Any] = {}
    confidence: dict[str, str] = {}

    lower = text.lower()

    # Attempt simple heuristic extraction
    lines = text.split("\n")
    for line in lines:
        ll = line.lower().strip()
        if ll.startswith("job title:") or ll.startswith("title:"):
            val = line.split(":", 1)[1].strip()
            if val:
                fields["job_title"] = val
                confidence["job_title"] = "found"
        elif ll.startswith("job code:") or ll.startswith("code:"):
            val = line.split(":", 1)[1].strip()
            if val:
                fields["job_code"] = val
                confidence["job_code"] = "found"
        elif ll.startswith("job family:") or ll.startswith("family:"):
            val = line.split(":", 1)[1].strip()
            if val:
                fields["job_family"] = val
                confidence["job_family"] = "found"
        elif ll.startswith("job function:") or ll.startswith("function:"):
            val = line.split(":", 1)[1].strip()
            if val:
                fields["job_function"] = val
                confidence["job_function"] = "found"
        elif ll.startswith("level:") or ll.startswith("job level:") or ll.startswith("grade:"):
            val = line.split(":", 1)[1].strip()
            if val:
                fields["job_level"] = val
                confidence["job_level"] = "found"

    # Look for responsibilities block
    if "responsibilit" in lower:
        idx = lower.find("responsibilit")
        snippet = text[idx:idx + 2000]
        fields["responsibilities"] = snippet.strip()
        confidence["responsibilities"] = "found"

    # Look for qualifications block
    if "qualification" in lower or "requirement" in lower:
        for kw in ["qualification", "requirement"]:
            idx = lower.find(kw)
            if idx != -1:
                snippet = text[idx:idx + 1500]
                fields["qualifications"] = snippet.strip()
                confidence["qualifications"] = "found"
                break

    # Mark all standard fields not found as missing
    for f in PROFILE_FIELDS:
        if f not in fields:
            confidence[f] = "missing"

    return {"fields": fields, "confidence": confidence}


try:
    import pypdf as _pypdf  # type: ignore
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

try:
    import docx as _docx  # type: ignore
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


def _parse_document(file_path: str) -> str:
    """Parse a Word or PDF document and return its text content."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            if not _PYPDF_AVAILABLE:
                return f"[PDF parsing unavailable — pypdf not installed. File: {file_path}]"
            reader = _pypdf.PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext in (".docx", ".doc"):
            if not _DOCX_AVAILABLE:
                return f"[DOCX parsing unavailable — python-docx not installed. File: {file_path}]"
            doc = _docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        else:
            # Attempt plain text read
            with open(file_path, encoding="utf-8", errors="replace") as f:
                return f.read()
    except Exception as e:
        return f"[Error reading file {file_path}: {e}]"


@tool
def intake_tool(
    source_type: str,
    content: str = "",
    file_path: str = "",
    clone_profile_code: str = "",
) -> str:
    """
    Process source data for job profile creation. Accepts text, file path, clone instruction, or verbal description.

    Args:
        source_type: One of 'text', 'file', 'clone', 'verbal'
        content: Raw text content (for source_type='text' or 'verbal')
        file_path: Path to a Word or PDF file (for source_type='file')
        clone_profile_code: Job profile code to clone (for source_type='clone')

    Returns:
        JSON string with extracted fields, confidence flags, and source_type.
        Emits M1 milestone log.
    """
    result: dict[str, Any] = {
        "source_type": source_type,
        "fields": {},
        "confidence": {},
        "raw_text": "",
    }

    if source_type == "file":
        if not file_path:
            logger.warning("M1.missed: no job profile fields could be identified from the provided input — input_type=file (no path provided)")
            return json.dumps({"error": "file_path is required for source_type='file'"})
        raw_text = _parse_document(file_path)
        result["raw_text"] = raw_text[:500]  # truncate for context
        extracted = _extract_fields_from_text(raw_text)
        result["fields"] = extracted["fields"]
        result["confidence"] = extracted["confidence"]

    elif source_type == "clone":
        if not clone_profile_code:
            logger.warning("M1.missed: no job profile fields could be identified from the provided input — input_type=clone (no code provided)")
            return json.dumps({"error": "clone_profile_code is required for source_type='clone'"})
        # Signal to the agent that it should fetch the profile from SuccessFactors
        result["fields"] = {"clone_source": clone_profile_code}
        result["confidence"] = {"clone_source": "found"}
        result["instruction"] = f"Retrieve existing job profile with code '{clone_profile_code}' from SuccessFactors Generic Objects API and use it as the base for the new profile."

    elif source_type in ("text", "verbal"):
        text = content.strip()
        if not text:
            logger.warning("M1.missed: no job profile fields could be identified from the provided input — input_type=%s (empty content)", source_type)
            return json.dumps({"error": "content is required for source_type='text' or 'verbal'"})
        result["raw_text"] = text[:500]
        extracted = _extract_fields_from_text(text)
        result["fields"] = extracted["fields"]
        result["confidence"] = extracted["confidence"]

    else:
        logger.warning("M1.missed: no job profile fields could be identified from the provided input — input_type=%s (unknown type)", source_type)
        return json.dumps({"error": f"Unknown source_type: {source_type}. Use 'text', 'file', 'clone', or 'verbal'."})

    fields_found = len([k for k, v in result["confidence"].items() if v == "found"])

    if fields_found == 0 and source_type != "clone":
        logger.warning(
            "M1.missed: no job profile fields could be identified from the provided input — input_type=%s",
            source_type,
        )
    else:
        logger.info(
            "M1.achieved: source data received and fields identified — source_type=%s, fields_found=%d",
            source_type,
            fields_found,
        )

    return json.dumps(result)
