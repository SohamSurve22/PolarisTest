"""Optional local Qwen 2.5 3B duty classifier."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class QwenError(Exception):
    """The optional local Qwen classifier could not answer."""


class QwenClient:
    """Call the fine-tuned 3B comparison model through Ollama.

    The comparison column is opt-in via ``POLARIS_QWEN_MODEL``. This prevents
    the memo model (the existing 7B default) from being used accidentally.
    """

    def __init__(self) -> None:
        self.model = os.environ.get("POLARIS_QWEN_MODEL", "").strip()
        self._url = os.environ.get("POLARIS_OLLAMA_URL", "http://localhost:11434").rstrip("/")

    def classify_applicable_duty(
        self,
        *,
        obligation_id: str,
        act: str,
        title: str,
        summary: str,
        requirement_elements: list[dict[str, object]],
        policy_clauses: list[dict[str, object]],
        fallback_: bool = False,
    ) -> dict[str, object]:
        if not self.model:
            return {}
        prompt = json.dumps({
            "obligation_id": obligation_id,
            "act": act,
            "title": title,
            "summary": summary,
            "requirement_elements": requirement_elements,
            "policy_clauses": policy_clauses,
            "allowed_statuses": [
                "covered", "partial", "missing", "not_applicable",
                "undetermined", "conflict", "violation",
            ],
        }, ensure_ascii=False)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": (
                    "Classify the duty using only the allowed statuses. Return strict JSON "
                    "with status, clause_ids, reason, and confidence."
                )},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
        }
        request = urllib.request.Request(
            f"{self._url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120.0) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            raw = response_data.get("message", {}).get("content", "")
            data = json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, AttributeError) as exc:
            raise QwenError(str(exc)) from exc
        if not isinstance(data, dict):
            raise QwenError("Qwen returned a non-object response")
        return data
