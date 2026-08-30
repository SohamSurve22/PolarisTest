"""Local Qwen generation for statute Q&A. Same Ollama path as the memo, no JSON schema."""

from __future__ import annotations

import os
from collections.abc import Callable

from rag.models import RagCitation, RagError

ChatFn = Callable[[str, str], str]

SYSTEM_PROMPT = (
  "Answer the user's question using ONLY the statute excerpts provided. "
  "If the excerpts do not contain the answer, say you cannot tell from the provided text. "
  "List the cited ids at the end of the answer."
)

DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"


def build_user_prompt(question: str, citations: list[RagCitation]) -> str:
  blocks = []
  for row in citations:
    blocks.append(f"[{row.id}] {row.title}\n{row.text}".strip())
  excerpts = "\n\n".join(blocks) if blocks else "(no excerpts)"
  return f"Excerpts:\n{excerpts}\n\nQuestion: {question}"


def generate_answer(
  question: str,
  citations: list[RagCitation],
  *,
  chat: ChatFn | None = None,
) -> str:
  chat_fn = chat or default_chat
  return chat_fn(SYSTEM_PROMPT, build_user_prompt(question, citations))


def default_chat(system_prompt: str, user_prompt: str) -> str:
  import httpx

  model = os.environ.get("POLARIS_CHAT_MODEL", DEFAULT_MODEL)
  base = os.environ.get("POLARIS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
  url = f"{base}/api/chat"
  payload = {
    "model": model,
    "messages": [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
    ],
    "stream": False,
    "options": {"temperature": 0.2, "num_ctx": 8192},
  }
  try:
    response = httpx.post(url, json=payload, timeout=180.0)
    response.raise_for_status()
  except httpx.HTTPError as exc:
    raise RagError(f"local LLM request failed ({model}): {exc}") from exc
  data = response.json()
  content = data.get("message", {}).get("content", "")
  if not content:
    raise RagError(f"empty response from local model {model}")
  return content
