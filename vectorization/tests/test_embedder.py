from unittest.mock import MagicMock, patch

import pytest

from vectorization.config import VectorizationSettings
from vectorization.embedder import (
  EmbeddingError,
  OllamaEmbedder,
  provider_from_settings,
)


def _settings(**overrides: object) -> VectorizationSettings:
  values: dict[str, object] = {
    "ollama_url": "http://localhost:11434/api/embeddings",
    "embedding_model": "nomic-embed-text",
    "embedding_dim": 3,
  }
  values.update(overrides)
  return VectorizationSettings.model_validate(values)


def _mock_client(embedding: list[float] | None = None) -> MagicMock:
  client = MagicMock()
  response = MagicMock()
  response.json.return_value = {"embedding": embedding or [0.1, 0.2, 0.3]}
  client.post.return_value = response
  return client


@patch("vectorization.embedder.httpx.Client")
def test_embed_document_sends_nomic_search_document_prefix(
  mock_client_cls: MagicMock,
) -> None:
  client = _mock_client()
  mock_client_cls.return_value = client
  embedder = OllamaEmbedder(_settings())

  embedder.embed("Controllers must delete data.", task="document")

  prompt = client.post.call_args.kwargs["json"]["prompt"]
  assert prompt == "search_document: Controllers must delete data."


@patch("vectorization.embedder.httpx.Client")
def test_embed_query_sends_nomic_search_query_prefix(
  mock_client_cls: MagicMock,
) -> None:
  client = _mock_client()
  mock_client_cls.return_value = client
  embedder = OllamaEmbedder(_settings())

  embedder.embed("personal data", task="query")

  prompt = client.post.call_args.kwargs["json"]["prompt"]
  assert prompt == "search_query: personal data"


@patch("vectorization.embedder.httpx.Client")
def test_embed_default_task_is_document(mock_client_cls: MagicMock) -> None:
  client = _mock_client()
  mock_client_cls.return_value = client
  embedder = OllamaEmbedder(_settings())

  embedder.embed("clause text")

  prompt = client.post.call_args.kwargs["json"]["prompt"]
  assert prompt.startswith("search_document: ")


@patch("vectorization.embedder.httpx.Client")
def test_embed_batch_preserves_order(mock_client_cls: MagicMock) -> None:
  client = MagicMock()
  responses = []
  for vector in ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]):
    response = MagicMock()
    response.json.return_value = {"embedding": vector}
    responses.append(response)
  client.post.side_effect = responses
  mock_client_cls.return_value = client
  embedder = OllamaEmbedder(_settings())

  vectors = embedder.embed_batch(["first", "second"], task="document")

  assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
  assert client.post.call_count == 2
  prompts = [call.kwargs["json"]["prompt"] for call in client.post.call_args_list]
  assert prompts == ["search_document: first", "search_document: second"]


@patch("vectorization.embedder.httpx.Client")
def test_embed_batch_empty_list(mock_client_cls: MagicMock) -> None:
  mock_client_cls.return_value = _mock_client()
  embedder = OllamaEmbedder(_settings())

  assert embedder.embed_batch([]) == []
  mock_client_cls.return_value.post.assert_not_called()


@patch("vectorization.embedder.httpx.Client")
def test_factory_default_is_ollama(mock_client_cls: MagicMock) -> None:
  mock_client_cls.return_value = _mock_client()

  provider = provider_from_settings(_settings())

  assert isinstance(provider, OllamaEmbedder)


def test_factory_unknown_backend() -> None:
  with pytest.raises(ValueError, match="backend"):
    provider_from_settings(_settings(embedding_backend="mystery"))


def test_sentence_transformers_missing_extra() -> None:
  with patch(
    "vectorization.embedder._load_sentence_transformer",
    side_effect=ImportError("No module named sentence_transformers"),
  ):
    with pytest.raises(EmbeddingError, match="sentence-transformers"):
      provider_from_settings(_settings(embedding_backend="sentence_transformers"))


def test_sentence_transformers_embed_batch_calls_encode() -> None:
  model = MagicMock()
  model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
  with patch("vectorization.embedder._load_sentence_transformer", return_value=model):
    provider = provider_from_settings(_settings(embedding_backend="sentence_transformers"))
    vectors = provider.embed_batch(["a", "b"])

  assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
  _, kwargs = model.encode.call_args
  assert kwargs["normalize_embeddings"] is False
  assert list(model.encode.call_args.args[0]) == ["a", "b"]
