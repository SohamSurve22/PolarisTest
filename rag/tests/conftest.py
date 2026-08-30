from vectorization.models import SearchHit


def hit(
  *,
  source_type: str,
  cid: str,
  text: str,
  score: float = 0.9,
  title: str = "",
  obligation_id: str | None = None,
  section_id: str | None = None,
) -> SearchHit:
  payload = {
    "source_type": source_type,
    "clause_id": cid if source_type == "rag_section" else None,
    "obligation_id": obligation_id,
    "section_id": section_id,
    "title": title,
    "clause_text": text,
    "retrieval_text": text,
  }
  return SearchHit(
    score=score,
    source_type=source_type,
    clause_id=cid if source_type == "rag_section" else None,
    section_id=section_id,
    clause_text=text,
    retrieval_text=text,
    payload=payload,
  )
