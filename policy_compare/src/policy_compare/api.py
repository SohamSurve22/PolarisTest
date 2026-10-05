"""FastAPI app: overlay compare and India/DPDP compliance analyze."""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.orchestrator import PipelineOutputs, create_default_orchestrator
from document_pipeline.utils.document_ids import generate_document_id
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from compliance.models import AnalysisResult, ComplianceReport
from compliance.pdf import pdf_download_name, render_pdf
from compliance.report import ReportError, generate_report
from compliance.service import AnalyzeError, analyze_document
from graph_builder.graph_builder_pipeline import GraphBuilderPipeline
from graph_builder.llm_graph_builder import LLMGraphBuilder
from graph_builder.openie import OpenIEExtractor
from graph_builder.policy_graph_builder import PolicyGraphBuilder
from policy_compare.openie_view import graph_ir_to_view_graph
from policy_compare.service import compare_document, default_law_paths
from rag.models import RagError
from rag.service import answer_question

_EXTENSIONS: dict[str, DocumentFormat] = {
  ".txt": DocumentFormat.TXT,
  ".pdf": DocumentFormat.PDF,
  ".docx": DocumentFormat.DOCX,
  ".html": DocumentFormat.HTML,
  ".htm": DocumentFormat.HTML,
}

app = FastAPI(title="PolarisLex policy compare")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)


def _repo_root() -> Path:
  return Path(__file__).resolve().parents[3]


def _law_paths() -> list[Path]:
  configured = os.environ.get("POLARIS_LAW_DIR")
  root = Path(configured) if configured else _repo_root()
  named = default_law_paths(root)
  if all(path.is_file() for path in named):
    return named
  return sorted(root.glob("*.json"))


def _parse_upload(raw: bytes, filename: str, suffix: str, fmt: DocumentFormat) -> tuple[PipelineOutputs, Path]:
  with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
    handle.write(raw)
    temp_path = Path(handle.name)
  source = DocumentSource(
    metadata=DocumentMetadata(
      document_id=generate_document_id(),
      filename=filename or temp_path.name,
      format=fmt,
      source_path=str(temp_path),
    ),
  )
  outputs = create_default_orchestrator().run(source)
  return outputs, temp_path


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


@app.post("/compare")
async def compare(file: UploadFile = File(...)) -> dict:
  suffix, fmt, raw = await _read_upload(file)
  temp_path: Path | None = None
  try:
    outputs, temp_path = _parse_upload(raw, file.filename or "policy.txt", suffix, fmt)
    law_paths = _law_paths()
    missing = [str(path) for path in law_paths if not path.is_file()]
    if missing:
      raise HTTPException(status_code=500, detail=f"Law graphs missing: {missing}")
    result = compare_document(outputs.entity, law_paths, outputs.sectioned)
    return result.model_dump()
  except HTTPException:
    raise
  except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
  finally:
    if temp_path is not None:
      temp_path.unlink(missing_ok=True)


@app.post("/analyze")
async def analyze(
  file: UploadFile = File(...),
  jurisdiction: str = Form("IN"),
  analysis_date: str = Form(""),
  roles: str = Form(""),
) -> dict:
  suffix, fmt, raw = await _read_upload(file)
  temp_path: Path | None = None
  try:
    outputs, temp_path = _parse_upload(raw, file.filename or "policy.txt", suffix, fmt)
    law_paths = _law_paths()
    missing = [str(path) for path in law_paths if not path.is_file()]
    if missing:
      raise HTTPException(status_code=500, detail=f"Law graphs missing: {missing}")
    parsed_date = _parse_analysis_date(analysis_date)
    parsed_roles = [item.strip() for item in roles.split(",") if item.strip()] or None
    policy_graph = None
    mapping_failures = []
    policy_openie_view = None
    ollama_client = None
    try:
      from semantic_graph.semantic_enrichment.ollama_chat import OllamaChatClient

      ollama_client = OllamaChatClient()
    except Exception:
      # Ollama down / not installed: keep Path A, policy_graph stays null.
      ollama_client = None
    if ollama_client is not None:
      try:
        llm_client = ollama_client  # type: ignore[assignment]
        policy_builder = PolicyGraphBuilder(OpenIEExtractor(llm_client))
        graph_builder = GraphBuilderPipeline(llm_builder=LLMGraphBuilder(llm_client), policy_builder=policy_builder)
        graph_ir, failures = graph_builder.build(outputs.entity)
        policy_graph = graph_ir.to_dict()
        mapping_failures = [item.to_dict() for item in failures]
        policy_openie_view = graph_ir_to_view_graph(policy_graph, outputs.entity.metadata.document_id)
      except Exception:
        # OpenIE / GraphIR failure: Path A unchanged, policy_graph stays null.
        policy_graph = None
        mapping_failures = []
        policy_openie_view = None

    result = analyze_document(
      outputs.entity,
      law_paths,
      jurisdiction=jurisdiction,
      analysis_date=parsed_date,
      roles=parsed_roles,
      policy_builder=policy_builder if ollama_client is not None else None,
    )
    result.policy_graph = policy_graph
    result.mapping_failures = mapping_failures
    result.policy_openie_view = policy_openie_view
    return result.model_dump()
  except HTTPException:
    raise
  except AnalyzeError as exc:
    raise HTTPException(
      status_code=503,
      detail="Analysis search backend unavailable (Qdrant or Ollama).",
    ) from exc
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
  except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
  finally:
    if temp_path is not None:
      temp_path.unlink(missing_ok=True)


@app.post("/report")
def report(body: AnalysisResult) -> dict:
  try:
    return generate_report(body).model_dump()
  except ReportError as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/report.pdf")
def report_pdf(body: ComplianceReport) -> Response:
  pdf = render_pdf(body)
  filename = pdf_download_name(body)
  return Response(
    content=pdf,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )


class RagRequest(BaseModel):
  question: str
  mode: str = Field(default="dense")


@app.post("/rag")
def rag(body: RagRequest) -> dict:
  if body.mode not in {"dense", "graph"}:
    raise HTTPException(status_code=400, detail="mode must be dense or graph")
  try:
    return answer_question(body.question, mode=body.mode, law_paths=_law_paths()).model_dump()
  except RagError as exc:
    raise HTTPException(
      status_code=503,
      detail="Q&A backend unavailable (Qdrant or Ollama).",
    ) from exc
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def _parse_analysis_date(raw: str) -> date | None:
  text = (raw or "").strip()
  if not text:
    return None
  try:
    return datetime.strptime(text, "%Y-%m-%d").date()
  except ValueError:
    return None


async def _read_upload(file: UploadFile) -> tuple[str, DocumentFormat, bytes]:
  suffix = Path(file.filename or "policy.txt").suffix.lower() or ".txt"
  fmt = _EXTENSIONS.get(suffix)
  if fmt is None:
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
  raw = await file.read()
  if not raw:
    raise HTTPException(status_code=400, detail="Empty file")
  return suffix, fmt, raw
