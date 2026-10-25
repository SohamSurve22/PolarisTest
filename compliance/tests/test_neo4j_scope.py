from __future__ import annotations

from compliance.neo4j_scope import Neo4jScopeConfig, graph_ir_from_neo4j


class _Session:
  def __init__(self) -> None:
    self.queries: list[str] = []

  def __enter__(self) -> _Session:
    return self

  def __exit__(self, *_args: object) -> None:
    return None

  def run(self, query: str):
    self.queries.append(query)
    if "MATCH (n)" in query:
      return [
        {"id": "DPDP_SEC_1", "labels": ["Obligation"], "properties": {"act": "DPDP", "title": "Consent"}},
        {"id": "PENALTY_1", "labels": ["Penalty"], "properties": {"act": "DPDP", "amount_crore": 10}},
      ]
    return [{"source": "PENALTY_1", "target": "DPDP_SEC_1", "type": "PENALIZES", "properties": {}}]


class _Driver:
  def __init__(self) -> None:
    self.session_obj = _Session()
    self.closed = False

  def verify_connectivity(self) -> None:
    return None

  def session(self, *, database=None) -> _Session:
    assert database is None
    return self.session_obj

  def close(self) -> None:
    self.closed = True


def test_neo4j_scope_reads_graph_ir_with_parameterized_queries() -> None:
  driver = _Driver()
  seen: dict[str, object] = {}

  def factory(uri: str, *, auth: tuple[str, str]):
    seen["uri"] = uri
    seen["auth"] = auth
    return driver

  graph = graph_ir_from_neo4j(
    Neo4jScopeConfig("bolt://graph", "neo4j", "secret"),
    driver_factory=factory,
  )

  assert seen == {"uri": "bolt://graph", "auth": ("neo4j", "secret")}
  assert [node.label for node in graph.nodes] == ["Obligation", "Penalty"]
  assert graph.relationships[0].type == "PENALIZES"
  assert all("$" not in query for query in driver.session_obj.queries)
  assert driver.closed is True


def test_neo4j_scope_rejects_an_empty_catalog() -> None:
  class EmptySession(_Session):
    def run(self, query: str):
      self.queries.append(query)
      return []

  class EmptyDriver(_Driver):
    def __init__(self) -> None:
      self.session_obj = EmptySession()
      self.closed = False

  driver = EmptyDriver()
  try:
    graph_ir_from_neo4j(driver_factory=lambda *_args, **_kwargs: driver)
  except RuntimeError as exc:
    assert "no catalog nodes" in str(exc)
  else:
    raise AssertionError("empty Neo4j catalogs must fail closed")
