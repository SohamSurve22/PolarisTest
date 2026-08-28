"""File contract for KG obligation / section ingest. Not GraphIR, not Neo4j."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KgSection(BaseModel):
  model_config = ConfigDict(extra="ignore")

  section_id: str
  title: str | None = None
  text: str = ""


class KgObligation(BaseModel):
  model_config = ConfigDict(extra="ignore")

  obligation_id: str
  section_id: str | None = None
  text: str = ""


class KgFile(BaseModel):
  """One law/framework JSON file under VECTORIZATION_KG_DIR."""

  model_config = ConfigDict(extra="ignore")

  law_code: str
  language: str = "en"
  sections: list[KgSection] = Field(default_factory=list)
  obligations: list[KgObligation] = Field(default_factory=list)
