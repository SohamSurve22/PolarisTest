"""Ollama /api/chat client for LLMClauseAnalyzer (LLMClient protocol)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_DEFAULT_URL = "http://localhost:11434"


class OllamaChatClient:
  """POST to Ollama chat. Env: POLARIS_OLLAMA_URL, POLARIS_CHAT_MODEL."""

  def __init__(
    self,
    model: str | None = None,
    base_url: str | None = None,
    *,
    timeout_seconds: float = 120.0,
  ) -> None:
    self._model = model or os.environ.get("POLARIS_CHAT_MODEL", _DEFAULT_MODEL)
    base = (base_url or os.environ.get("POLARIS_OLLAMA_URL", _DEFAULT_URL)).rstrip("/")
    self._url = f"{base}/api/chat"
    self._timeout = timeout_seconds

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    payload = {
      "model": self._model,
      "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
      ],
      "stream": False,
      "format": "json",
    }
    request = urllib.request.Request(
      self._url,
      data=json.dumps(payload).encode("utf-8"),
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    try:
      with urllib.request.urlopen(request, timeout=self._timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
      raise RuntimeError(f"local LLM request failed ({self._model}): {exc}") from exc
    content = data.get("message", {}).get("content", "")
    if not content:
      raise RuntimeError(f"empty response from local model {self._model}")
    return content
