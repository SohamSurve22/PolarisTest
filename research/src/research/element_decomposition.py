# Atomic requirement-element decomposition module

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AtomicElement:
    element_id: str
    parent_obligation_id: str
    description: str
    evidence_requirements: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    source_document: str = ""
    source_section: str = ""
    supporting_text: str = ""
    requires_human_interpretation: bool = False


@dataclass
class DecomposedObligation:
    obligation_id: str
    source_document: str
    source_section: str
    supporting_legal_text: str
    elements: list[AtomicElement] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    
    def is_fully_satisfied(self, satisfied_element_ids: set[str]) -> bool:
        if not self.elements:
            return False
        return all(elem.element_id in satisfied_element_ids for elem in self.elements)
    
    def get_unsatisfied_elements(self, satisfied_element_ids: set[str]) -> list[AtomicElement]:
        return [elem for elem in self.elements if elem.element_id not in satisfied_element_ids]


class ElementDecomposer:
    def __init__(self):
        self.decompositions: dict[str, DecomposedObligation] = {}
    
    def register_decomposition(self, decomp: DecomposedObligation) -> None:
        self.decompositions[decomp.obligation_id] = decomp
    
    def get_decomposition(self, obligation_id: str) -> DecomposedObligation | None:
        return self.decompositions.get(obligation_id)
    
    def assess_elements(self, obligation_id: str, evidence_texts: list[str]) -> tuple[set[str], dict[str, dict[str, Any]]]:
        decomp = self.get_decomposition(obligation_id)
        if not decomp:
            return set(), {}
        
        satisfied = set()
        diagnostics = {}
        combined_text = " ".join(evidence_texts).lower()
        
        for elem in decomp.elements:
            elem_diagnostics = {
                "element_id": elem.element_id,
                "description": elem.description,
                "keywords_found": [],
                "matched_spans": []
            }
            found_keywords = []
            for kw in elem.keywords:
                if kw.lower() in combined_text:
                    found_keywords.append(kw)
            elem_diagnostics["keywords_found"] = found_keywords
            
            if found_keywords or any(req.lower() in combined_text for req in elem.evidence_requirements):
                satisfied.add(elem.element_id)
                elem_diagnostics["status"] = "satisfied"
            else:
                elem_diagnostics["status"] = "unsatisfied"
            
            diagnostics[elem.element_id] = elem_diagnostics
        
        return satisfied, diagnostics
