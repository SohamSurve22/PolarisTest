from unittest.mock import MagicMock, patch

from vectorization.config import VectorizationSettings
from vectorization.pipeline import reembed, run
from vectorization.sources import EmbeddableSource
from vectorization.store import VectorStore

from tests.conftest import make_clause


def _settings(**overrides: object) -> VectorizationSettings:
  values: dict[str, object] = {
    "qdrant_url": "http://localhost:6333",
    "qdrant_collection": "document_clauses",
    "embedding_model": "all-mpnet-base-v2",
    "embedding_dim": 3,
    "embedding_backend": "ollama",
    "clauses_dir": "/tmp/unused-clauses",
    "kg_dir": "/tmp/unused-kg",
    "embed_batch_size": 32,
    "batch_size": 50,
  }
  values.update(overrides)
  return VectorizationSettings.model_validate(values)


@patch("vectorization.pipeline.run")
@patch("vectorization.pipeline.run_kg")
def test_reembed_runs_kg_then_documents(
  mock_run_kg: MagicMock,
  mock_run: MagicMock,
) -> None:
  settings = _settings()
  order: list[str] = []
  mock_run_kg.side_effect = lambda _settings: order.append("kg")
  mock_run.side_effect = lambda _settings: order.append("docs")

  reembed(settings)

  assert order == ["kg", "docs"]
  mock_run_kg.assert_called_once_with(settings)
  mock_run.assert_called_once_with(settings)


@patch("vectorization.cli.reembed")
def test_cli_reembed_calls_reembed(mock_reembed: MagicMock) -> None:
  from vectorization.cli import main

  assert main(["reembed"]) == 0
  mock_reembed.assert_called_once()


def test_run_upserts_payload_with_current_embedding_model() -> None:
  client = MagicMock()
  client.collection_exists.return_value = True
  settings = _settings()
  source = EmbeddableSource(clause=make_clause())
  embedder = MagicMock()
  embedder.embed_batch.return_value = [[3.0, 4.0, 0.0]]
  provider = MagicMock()
  provider.__enter__.return_value = embedder
  provider.__exit__.return_value = False

  with (
    patch("vectorization.pipeline.load_embeddable_sources", return_value=[source]),
    patch("vectorization.pipeline.provider_from_settings", return_value=provider),
    patch(
      "vectorization.pipeline.VectorStore",
      side_effect=lambda s: VectorStore(s, client=client),
    ),
  ):
    run(settings)

  point = client.upsert.call_args.kwargs["points"][0]
  assert point.payload["embedding_model_version"] == "all-mpnet-base-v2"
  assert point.payload["source_type"] == "document_clause"
