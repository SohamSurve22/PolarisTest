"""OpenAI Jev classifier for catalog duties.

Jev scores every applicable catalog duty using the catalog row and policy
clauses. Its answer is normalized by the service and becomes the authoritative
obligation status. A Qwen comparison model is intentionally separate.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DECISIONS_PREVIEW_URL = os.environ.get("OPENAI_DECISIONS_PREVIEW_URL", "").strip()
DECISIONS_PREVIEW_BODY = os.environ.get("OPENAI_DECISIONS_PREVIEW_BODY", "").strip()
DECISIONS_PREVIEW_MODEL = os.environ.get("OPENAI_DECISIONS_PREVIEW_MODEL", "gpt-6-luna")
CHAT_MODEL = os.environ.get("JEV_CHAT_MODEL", "gpt-6-luna")
DECISIONS_TRY_COUNT = int(os.environ.get("OPENAI_DECISIONS_TRY_COUNT", "2"))


class JevError(Exception):
    """Transport, configuration, or JSON error from the Jev service."""


class JevClient:
    """Second-opinion classifier over catalog duties.

    Selection order:
      1. Decisions preview only when both its URL and an explicit body template
         (OPENAI_DECISIONS_PREVIEW_BODY) are set.
      2. Chat completions with a strict JSON schema limited to the existing
         ObligationStatus values.
    """

    def __init__(self) -> None:
        self._client = None
        if not os.environ.get("OPENAI_API_KEY"):
            self._client = self._unavailable_client
            return
        try:
            self._client = (
                self._preview_then_chat_client()
                if DECISIONS_PREVIEW_URL and DECISIONS_PREVIEW_BODY
                else self._chat_client()
            )
        except ImportError as exc:
            self._client = self._unavailable_client
            self._init_error = str(exc)

    @staticmethod
    def _unavailable_client(_payload: dict[str, object]) -> dict[str, object]:
        raise JevError("OPENAI_API_KEY and an OpenAI client are required for Jev")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

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
        """Classify one applicable duty.

        Returns the strict schema object: status, clause_ids, reason,
        confidence. Any other string from the model becomes "undetermined".
        """
        payload = {
            "obligation_id": obligation_id,
            "act": act,
            "title": title,
            "summary": summary,
            "requirement_elements": requirement_elements,
            "policy_clauses": policy_clauses,
            "fallback": fallback_,
        }
        if self._client is None:
            raise JevError("Jev client is not configured")
        if callable(self._client):
            return self._client(payload)
        method = getattr(self._client, "classify_applicable_duty", None)
        if method is None:
            raise JevError("Configured Jev client has no classification method")
        payload["fallback_"] = payload.pop("fallback")
        return method(**payload)

    def _preview_then_chat_client(self) -> callable:
        preview = self._decisions_client()
        chat = self._chat_client()

        def client(payload: dict[str, object]) -> dict[str, object]:
            try:
                return preview(payload)
            except JevError as exc:
                if "403" not in str(exc):
                    raise
                return chat(payload)

        return client

    # ------------------------------------------------------------------
    # decisions-preview client
    # ------------------------------------------------------------------

    def _decisions_client(self) -> callable:
        import requests

        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        def client(payload: dict[str, object]) -> dict[str, object]:
            body = self._decisions_body(payload)
            for _ in range(DECISIONS_TRY_COUNT):
                try:
                    resp = session.post(
                        DECISIONS_PREVIEW_URL,
                        json=body,
                        timeout=30.0,
                    )
                except requests.RequestException as exc:
                    raise JevError(str(exc)) from exc
                if resp.status_code == 403:
                    raise JevError("decisions preview 403")
                resp.raise_for_status()
                return self._decisions_parse(resp.text)
            raise JevError("decisions preview exhausted retries")

        return client

    @staticmethod
    def _decisions_body(payload: dict[str, object]) -> dict[str, object]:
        """Expand a caller-supplied preview body; never assume its schema."""
        try:
            body = json.loads(DECISIONS_PREVIEW_BODY)
        except json.JSONDecodeError as exc:
            raise JevError("OPENAI_DECISIONS_PREVIEW_BODY must be valid JSON") from exc

        def expand(value):
            if isinstance(value, dict):
                return {key: expand(item) for key, item in value.items()}
            if isinstance(value, list):
                return [expand(item) for item in value]
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                return payload.get(value[2:-2], value)
            return value

        result = expand(body)
        if not isinstance(result, dict):
            raise JevError("OPENAI_DECISIONS_PREVIEW_BODY must contain a JSON object")
        return result

    @staticmethod
    def _decisions_parse(raw: str) -> dict[str, object]:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise JevError("decisions preview returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise JevError("decisions preview returned a non-object response")
        text = data.get("output", "")
        if not isinstance(text, str) or not text.strip():
            raise JevError("decisions preview returned empty output")
        try:
            result = json.loads(text.strip())
        except json.JSONDecodeError as exc:
            raise JevError("decisions preview returned invalid output JSON") from exc
        if not isinstance(result, dict):
            raise JevError("decisions preview returned a non-object output")
        return result

    # ------------------------------------------------------------------
    # fallback chat-completions client
    # ------------------------------------------------------------------

    def _chat_client(self) -> callable:
        import openai  # noqa: F401 – ensures package is present before binding
        from openai import OpenAI

        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        def _call(payload: dict[str, object]) -> dict[str, object]:
            model = CHAT_MODEL  # use the chat model, not the decisions-preview one
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a deterministic second-opinion classifier for a "
                        "privacy-policy compliance duty. Return ONLY valid JSON with "
                        "exactly these keys: status, clause_ids, reason, confidence.\n"
                        "- status: exactly one of covered, partial, missing, not_applicable, "
                        "undetermined, conflict, violation.\n"
                        "- clause_ids: list of quoted clause IDs cited as support.\n"
                        "- reason: one short sentence.\n"
                        "- confidence: float 0.0-1.0.\n"
                        "If the model cannot map the answer, set status to \"undetermined\"."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ]
            try:
                resp = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                text = resp.choices[0].message.content or ""
                if not text.strip():
                    raise JevError("OpenAI Jev returned empty content")
                result = json.loads(text.strip())
                if not isinstance(result, dict):
                    raise JevError("OpenAI Jev returned a non-object JSON response")
                return result
            except JevError:
                raise
            except (json.JSONDecodeError, AttributeError, IndexError, TypeError) as exc:
                raise JevError("OpenAI Jev returned malformed JSON") from exc
            except Exception as exc:
                raise JevError(str(exc)) from exc

        return _call
