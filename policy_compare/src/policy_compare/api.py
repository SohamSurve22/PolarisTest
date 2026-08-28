"""FastAPI app: upload a company privacy policy and return overlay graphs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata
from document_pipeline.pipeline.orchestrator import create_default_orchestrator
from document_pipeline.utils.document_ids import generate_document_id
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from policy_compare.service import compare_document, default_law_paths

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


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


@app.post("/compare")
async def compare(file: UploadFile = File(...)) -> dict:
  suffix = Path(file.filename or "policy.txt").suffix.lower() or ".txt"
  fmt = _EXTENSIONS.get(suffix)
  if fmt is None:
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

  raw = await file.read()
  if not raw:
    raise HTTPException(status_code=400, detail="Empty file")

  with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
    handle.write(raw)
    temp_path = Path(handle.name)

  try:
    source = DocumentSource(
      metadata=DocumentMetadata(
        document_id=generate_document_id(),
        filename=file.filename or temp_path.name,
        format=fmt,
        source_path=str(temp_path),
      ),
    )
    outputs = create_default_orchestrator().run(source)
    law_paths = _law_paths()
    missing = [str(path) for path in law_paths if not path.is_file()]
    if missing:
      raise HTTPException(status_code=500, detail=f"Law graphs missing: {missing}")
    result = compare_document(outputs.entity, law_paths)
    return result.model_dump()
  except HTTPException:
    raise
  except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
  finally:
    temp_path.unlink(missing_ok=True)
