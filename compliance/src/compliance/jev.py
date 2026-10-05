"""Iberian-style second-opinion classifier (Path B).

Jev scores every applicable catalog duty a second time, using the same
catalogue rows and policy clauses as Path A. It never overwrites .status,
gaps, penalties, or the Path A paint. Status stays long-lived on
ObligationFinding from collect_credits/classify_duty; Jev data lands in
sidecar fields.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DECISIONS_PREVIEW_URL = os.environ.get(
    "OPENAI_DECISIONS_PREVIEW_URL", "https://decisions.preview.openai.com/v1/decisions"
)
DECISIONS_PREVIEW_MODEL = os.environ.get("OPENAI_DECISIONS_PREVIEW_MODEL", "gpt-6-luna")
CHAT_MODEL = os.environ.get("JEV_CHAT_MODEL", "gpt-4o-mini")
DECISIONS_TRY_COUNT = int(os.environ.get("OPENAI_DECISIONS_TRY_COUNT", "2"))


class JevError(Exception):
    """Transport or JSON error from the Jev service. Missing key/outage means
    the calling analyze_document keeps Path A and leaves jev fields empty."""


class JevClient:
    """Second-opinion classifier over catalog duties.

    Selection order:
      1. Decisions preview (OPENAI_DECISIONS_PREVIEW_URL), if the base URL is set.
      2. Chat completions with a strict JSON schema limited to the existing
         ObligationStatus values.
    """

    def __init__(self) -> None:
        self._client = None
        # Decides how to build the callable. Missing packages / env keep the
        # caller on Path A; the returned client always returns an empty block.
        try:
            if os.environ.get("OPENAI_DECISIONS_PREVIEW_URL"):
                self._client = self._decisions_client()
            else:
                self._client = self._chat_client()
        except ImportError:
            # No OpenAI packages installed -> caller keeps Path A (empty block).
            self._client = self._noop_client

    def _noop_client(self, payload: dict[str, object]) -> dict[str, object]:
        """Return the empty block Path A keeps when Jev cannot answer."""
        return {
            "status": "undetermined",
            "clause_ids": [],
            "reason": "Jev unavailable",
            "confidence": 0.0,
        }

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
        try:
            return self._client(payload)
        except JevError:
            # Outage / missing key must never 503: caller keeps Path A.
            return {
                "status": "undetermined",
                "clause_ids": [],
                "reason": "Jev unavailable",
                "confidence": 0.0,
            }

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
            body = self._decisions_payload(payload)
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
    def _decisions_payload(payload: dict[str, object]) -> dict[str, object]:
        return {
            "model": DECISIONS_PREVIEW_MODEL,
            "reasoning": {
                "effort": "low",
                "summary": "auto",
            },
            "input": {
                "obligation_id": payload["obligation_id"],
                "act": payload["act"],
                "title": payload["title"],
                "summary": payload["summary"],
                "requirement_elements": payload["requirement_elements"],
                "policy_clauses": payload["policy_clauses"],
                "fallback": payload.get("fallback", False),
            },
        }

    @staticmethod
    def _decisions_parse(raw: str) -> dict[str, object]:
        data = json.loads(raw)
        text = data.get("output", "")
        if not isinstance(text, str) or not text.strip():
            raise JevError("decisions preview returned empty output")
        return json.loads(text.strip())

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
            except Exception as exc:
                raise JevError(str(exc)) from exc
            text = resp.choices[0].message.content or ""
            return json.loads(text.strip())

        return _call
