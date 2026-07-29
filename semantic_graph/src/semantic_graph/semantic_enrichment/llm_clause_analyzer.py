"""LLM-powered clause analyzer.

Uses an injected LLM client to analyse clause text and return structured
``ClauseMeaning`` objects.  The client protocol is kept generic so any
provider (OpenAI, Groq, Ollama, Claude) can be used.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from semantic_graph.semantic_enrichment.clause_analyzer import ClauseAnalyzer
from semantic_graph.semantic_enrichment.enrichment_models import ClauseMeaning, Obligation
from semantic_graph.semantic_enrichment.prompts import build_analysis_prompt


class LLMClient(Protocol):
    """Protocol for injectable LLM backends used by the clause analyzer."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a text completion from the given prompts.

        Args:
            system_prompt: System-level instructions.
            user_prompt:   User-level input payload.

        Returns:
            Raw model output string.
        """
        ...


class LLMClauseAnalyzer(ClauseAnalyzer):
    """Analyzes legal clauses using an injected LLM client.

    The analyzer formats a prompt, sends it to the LLM, parses the JSON
    response, and returns a ``ClauseMeaning``.

    Args:
        client: An ``LLMClient``-compatible backend.
    """

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def analyze(self, clause_text: str, clause_id: str) -> ClauseMeaning:
        """Extract semantic meaning from a clause via the LLM."""
        system_prompt, user_prompt = build_analysis_prompt(clause_text)
        raw = self._client.generate(system_prompt, user_prompt)
        data = _parse_response(raw)
        return _build_clause_meaning(clause_id, data)


def _parse_response(raw: str) -> dict[str, Any]:
    """Parse the LLM response string into a validated dict.

    Args:
        raw: Raw LLM output (should be valid JSON).

    Returns:
        Parsed dictionary with an ``"obligations"`` key.

    Raises:
        ValueError: If the response is empty or malformed.
    """
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("LLM returned an empty response.")

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from LLM: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object.")

    obligations_raw = data.get("obligations")
    if not isinstance(obligations_raw, list):
        raise ValueError("LLM response must contain an 'obligations' array.")

    return data


def _build_clause_meaning(clause_id: str, data: dict[str, Any]) -> ClauseMeaning:
    """Build a ``ClauseMeaning`` from a validated response dictionary."""
    obligations = [_build_obligation(o) for o in data.get("obligations", [])]
    return ClauseMeaning(clause_id=clause_id, obligations=obligations)


def _build_obligation(raw: Any) -> Obligation:
    """Build a single ``Obligation`` from a raw dictionary."""
    if not isinstance(raw, dict):
        raise ValueError("Each obligation must be a JSON object.")

    subject = raw.get("subject", "")
    if not isinstance(subject, str):
        raise ValueError("'subject' must be a string.")

    action = raw.get("action", "")
    if not isinstance(action, str):
        raise ValueError("'action' must be a string.")

    object_ = raw.get("object", "")
    if not isinstance(object_, str):
        raise ValueError("'object' must be a string.")

    condition = raw.get("condition")
    if condition is not None and not isinstance(condition, str):
        raise ValueError("'condition' must be a string or null.")

    exception = raw.get("exception")
    if exception is not None and not isinstance(exception, str):
        raise ValueError("'exception' must be a string or null.")

    return Obligation(
        subject=subject,
        action=action,
        object=object_,
        condition=condition or None,
        exception=exception or None,
    )
