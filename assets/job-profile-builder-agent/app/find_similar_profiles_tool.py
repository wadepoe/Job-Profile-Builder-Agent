"""
Similarity search tool for existing SuccessFactors job profiles.
Returns the top 3 most similar profiles to help users start from an existing one.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _similarity_score(candidate: dict[str, Any], job_title: str, job_family: str = "") -> float:
    """Simple token-overlap similarity score."""
    query_tokens = set((job_title + " " + job_family).lower().split())
    candidate_str = " ".join([
        candidate.get("job_title", ""),
        candidate.get("job_family", ""),
        candidate.get("job_function", ""),
        candidate.get("job_level", ""),
    ]).lower()
    candidate_tokens = set(candidate_str.split())
    if not query_tokens:
        return 0.0
    intersection = query_tokens & candidate_tokens
    return len(intersection) / len(query_tokens)


@tool
def find_similar_profiles_tool(
    job_title: str,
    job_family: str = "",
    profiles_json: str = "[]",
) -> str:
    """
    Find the top 3 most similar existing job profiles for a given job title.
    The agent should first retrieve existing profiles from SuccessFactors via
    the Generic Objects MCP tool, then pass them to this tool for ranking.

    Args:
        job_title: The target job title to search for
        job_family: Optional job family to narrow results
        profiles_json: JSON array of existing profiles from SuccessFactors

    Returns:
        JSON with top 3 similar profiles and their similarity scores.
    """
    if not job_title.strip():
        return json.dumps({"error": "job_title is required"})

    try:
        profiles: list[dict[str, Any]] = json.loads(profiles_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid profiles_json: {e}"})

    if not profiles:
        return json.dumps({
            "top_matches": [],
            "note": "No existing profiles provided. Retrieve profiles from SuccessFactors first using the Generic Objects API tool.",
        })

    # Score and rank
    scored = [
        (profile, _similarity_score(profile, job_title, job_family))
        for profile in profiles
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_3 = scored[:3]

    results = [
        {
            "rank": i + 1,
            "job_title": p.get("job_title", "Unknown"),
            "job_code": p.get("job_code", ""),
            "job_family": p.get("job_family", ""),
            "job_level": p.get("job_level", ""),
            "similarity_score": round(score, 2),
        }
        for i, (p, score) in enumerate(top_3)
        if score > 0
    ]

    logger.info(
        "Similarity search complete for '%s': found %d matches",
        job_title,
        len(results),
    )

    return json.dumps({
        "query": {"job_title": job_title, "job_family": job_family},
        "top_matches": results,
        "instruction": "Present these matches to the user and ask if they want to clone one as a starting point, or proceed with generation from scratch.",
    })
