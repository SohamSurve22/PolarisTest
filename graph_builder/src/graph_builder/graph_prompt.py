"""Prompt templates and input serialization for the LLM graph builder."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from graph_builder.graph_models import ALLOWED_NODE_LABELS, ALLOWED_RELATIONSHIP_TYPES

if TYPE_CHECKING:
  from document_pipeline.models.entity import EntityDocument


SYSTEM_PROMPT = """You are a legal knowledge graph extraction engine for PolarisLex.

Your task is to convert structured legal document data into a knowledge graph
intermediate representation (GraphIR) as JSON.

STRICT RULES:
- Return ONLY valid JSON. No markdown fences. No explanations. No commentary.
- Never hallucinate entities, obligations, sections, or relationships.
- Use ONLY information explicitly present in the input JSON.
- Use ONLY the approved node labels and relationship types listed below.
- Every node MUST have a unique ``id``, a valid ``label``, and non-empty ``properties``.
- Set ``source_clause`` to the clause ID when a node is derived from a clause.
- Relationship ``source`` and ``target`` MUST reference existing node IDs.
- Do NOT generate Cypher or any database commands.

APPROVED NODE LABELS:
{node_labels}

APPROVED RELATIONSHIP TYPES:
{relationship_types}

OUTPUT JSON SCHEMA:
{{
  "nodes": [
    {{
      "id": "unique_node_id",
      "label": "OneOfApprovedLabels",
      "properties": {{ "name": "...", "text": "..." }},
      "source_clause": "clause_id_or_null"
    }}
  ],
  "relationships": [
    {{
      "source": "source_node_id",
      "target": "target_node_id",
      "type": "OneOfApprovedTypes",
      "properties": {{}}
    }}
  ]
}}
"""


def build_system_prompt() -> str:
  """Build the system prompt with allowed labels and relationship types.

  Returns:
    Fully formatted system prompt string.
  """
  node_labels = ", ".join(sorted(ALLOWED_NODE_LABELS))
  relationship_types = ", ".join(sorted(ALLOWED_RELATIONSHIP_TYPES))
  return SYSTEM_PROMPT.format(
    node_labels=node_labels,
    relationship_types=relationship_types,
  )


def serialize_entity_document(entity_document: EntityDocument) -> str:
  """Serialize an ``EntityDocument`` into structured JSON for the LLM.

  Only structured pipeline output is sent — never raw PDFs, OCR text,
  or entire unsegmented documents.

  Args:
    entity_document: Output of the entity extractor stage.

  Returns:
    Pretty-printed JSON string suitable for the LLM user prompt.
  """
  metadata = entity_document.metadata
  payload: dict[str, Any] = {
    "document": {
      "document_id": metadata.document_id,
      "filename": metadata.filename,
      "format": metadata.format.value,
      "title": metadata.title,
    },
    "clauses": [],
  }

  for entity_clause in entity_document.entity_clauses:
    contextual = entity_clause.contextual_clause
    classified = contextual.classified_clause
    clause = classified.clause

    clause_payload: dict[str, Any] = {
      "clause_id": clause.clause_id,
      "section_id": clause.section_id,
      "section_title": clause.section_title,
      "text": clause.clause_text.strip(),
      "role": classified.role.value,
      "classification_confidence": classified.confidence,
      "entities": [
        {
          "entity_id": entity.entity_id,
          "entity_text": entity.entity_text,
          "entity_type": entity.entity_type.value,
          "confidence": entity.confidence,
        }
        for entity in entity_clause.entities
      ],
      "references": [
        {
          "reference_text": reference.reference_text,
          "reference_type": reference.reference_type,
          "resolved": reference.resolved,
          "resolved_clause_id": reference.resolved_clause_id,
          "resolved_section_id": reference.resolved_section_id,
        }
        for reference in contextual.detected_references
      ],
      "context": {
        "previous_clause_id": contextual.previous_clause_id,
        "next_clause_id": contextual.next_clause_id,
        "section_position": contextual.section_position,
        "is_first_in_section": contextual.is_first_in_section,
        "is_last_in_section": contextual.is_last_in_section,
        "neighbor_clause_ids": contextual.neighbor_clause_ids,
      },
    }
    payload["clauses"].append(clause_payload)

  return json.dumps(payload, indent=2, ensure_ascii=False)


def build_user_prompt(entity_document: EntityDocument) -> str:
  """Build the user prompt containing structured document JSON.

  Args:
    entity_document: Output of the entity extractor stage.

  Returns:
    User prompt string with embedded structured JSON.
  """
  structured_json = serialize_entity_document(entity_document)
  return (
    "Convert the following structured legal document JSON into GraphIR.\n"
    "Return ONLY the GraphIR JSON object.\n\n"
    f"{structured_json}"
  )
