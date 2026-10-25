"""
pytest configuration for research/tests.

Inserts compliance and document_pipeline src directories into sys.path so
that pipeline_adapter.py can import them without installation.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # Codebase2/

for pkg in [
    "compliance/src",
    "document_pipeline/src",
    "vectorization/src",
    "graph_builder/src",
    "policy_compare/src",
    "rag/src",
]:
    p = str(_ROOT / pkg)
    if p not in sys.path:
        sys.path.insert(0, p)
