# Tests for element decomposition

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from research.element_decomposition import ElementDecomposer, DecomposedObligation, AtomicElement


def test_decomposition_basic():
    decomposer = ElementDecomposer()
    elem1 = AtomicElement(
        element_id="elem1",
        parent_obligation_id="OB1",
        description="Purpose stated",
        keywords=["purpose", "why"]
    )
    elem2 = AtomicElement(
        element_id="elem2",
        parent_obligation_id="OB1",
        description="Data categories identified",
        keywords=["data", "information"]
    )
    decomp = DecomposedObligation(
        obligation_id="OB1",
        source_document="test",
        source_section="1",
        supporting_legal_text="test text",
        elements=[elem1, elem2]
    )
    decomposer.register_decomposition(decomp)
    
    satisfied, diag = decomposer.assess_elements("OB1", ["We collect data for purpose X"])
    assert "elem1" in satisfied
    assert "elem2" in satisfied
    assert decomp.is_fully_satisfied(satisfied)


def test_partial_satisfaction():
    decomposer = ElementDecomposer()
    elem1 = AtomicElement(element_id="elem1", parent_obligation_id="OB1", description="d1", keywords=["purpose"])
    elem2 = AtomicElement(element_id="elem2", parent_obligation_id="OB1", description="d2", keywords=["data"])
    decomp = DecomposedObligation(obligation_id="OB1", source_document="t", source_section="1", supporting_legal_text="t", elements=[elem1, elem2])
    decomposer.register_decomposition(decomp)
    
    satisfied, diag = decomposer.assess_elements("OB1", ["For purpose X"])
    assert "elem1" in satisfied
    assert "elem2" not in satisfied
    assert not decomp.is_fully_satisfied(satisfied)
    unsatisfied = decomp.get_unsatisfied_elements(satisfied)
    assert len(unsatisfied) == 1
