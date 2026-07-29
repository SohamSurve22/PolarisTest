"""Prompt templates for LLM-based clause analysis.

The template asks the model to return structured JSON representing the
semantic obligations found in a legal clause.  The output is validated
against the ``Obligation`` model before being accepted.
"""

from __future__ import annotations

_SYSTEM_PROMPT = (
    "You are a legal document semantic analyzer. "
    "Analyze the following legal clause. "
    "Extract obligations. "
    "Return ONLY valid JSON."
)

_USER_TEMPLATE = (
    "Required JSON schema:\n"
    "{{\n"
    '    "obligations": [\n'
    "        {{\n"
    '            "subject": "",\n'
    '            "action": "",\n'
    '            "object": "",\n'
    '            "condition": "",\n'
    '            "exception": ""\n'
    "        }}\n"
    "    ]\n"
    "}}\n\n"
    "Clause:\n\n"
    "{clause_text}"
)


def build_analysis_prompt(clause_text: str) -> tuple[str, str]:
    """Build the system and user prompt pair for clause analysis.

    Args:
        clause_text: The raw clause text to analyse.

    Returns:
        A ``(system_prompt, user_prompt)`` tuple.
    """
    return _SYSTEM_PROMPT, _USER_TEMPLATE.format(clause_text=clause_text)
