"""Local LLM client backed by Ollama.

Implements the LLMClient protocol defined in
semantic_graph.semantic_enrichment.llm_clause_analyzer, so it can back
both LLMClauseAnalyzer (obligations) and LLMRetrievalSummarizer
(retrieval_text) without either of those modules knowing it's local.

Sized for a MacBook with 16GB unified memory: defaults to a 7B q4
instruct model (~5GB), which leaves headroom for the embedding model,
Ollama's own overhead, and everything else running on the machine.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OllamaLLMClient:
  """Calls a local Ollama model's /api/chat endpoint.

  Args:
      model:       Ollama model tag. Defaults to a 7B q4 instruct model
                   sized for 16GB unified memory — see the sizing table
                   in the project README before switching to something
                   larger (e.g. a 14B variant).
      base_url:    Ollama server base URL.
      force_json:  If True (default), sets Ollama's `format: "json"`
                   option, which constrains sampling to valid JSON —
                   this matters because both LLMClauseAnalyzer and
                   LLMRetrievalSummarizer do strict json.loads() on the
                   response and will raise on malformed output.
      timeout_seconds: Local 7B models on Apple Silicon are slow enough
                   that the default httpx timeout is too tight; this
                   defaults higher than OllamaEmbedder's.
  """

  def __init__(
    self,
    model: str = "qwen2.5:7b-instruct-q4_K_M",
    base_url: str = "http://localhost:11434",
    *,
    force_json: bool = True,
    timeout_seconds: float = 120.0,
  ) -> None:
    self._model = model
    self._url = f"{base_url.rstrip('/')}/api/chat"
    self._force_json = force_json
    self._client = httpx.Client(timeout=timeout_seconds)

  def generate(self, system_prompt: str, user_prompt: str) -> str:
    """Generate a completion from the local model. Satisfies LLMClient."""
    payload: dict[str, object] = {
      "model": self._model,
      "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
      ],
      "stream": False,
    }
    if self._force_json:
      payload["format"] = "json"

    try:
      response = self._client.post(self._url, json=payload)
      response.raise_for_status()
    except httpx.HTTPError as exc:
      raise RuntimeError(f"local LLM request failed ({self._model}): {exc}") from exc

    data = response.json()
    content = data.get("message", {}).get("content", "")
    if not content:
      raise RuntimeError(f"empty response from local model {self._model}: {data}")
    return content

  def close(self) -> None:
    self._client.close()

  def __enter__(self) -> "OllamaLLMClient":
    return self

  def __exit__(self, *exc_info: object) -> None:
    self.close()
