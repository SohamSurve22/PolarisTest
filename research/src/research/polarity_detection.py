# Denial-polarity detection module

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import re


class Polarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


@dataclass
class PolarityFinding:
    text_span: str
    polarity: Polarity
    confidence: float
    matched_patterns: list[str] = field(default_factory=list)
    reason: str = ""
    obligation_id: str | None = None
    element_id: str | None = None
    is_third_party: bool = False
    context: dict[str, Any] = field(default_factory=dict)


class DenialPolarityDetector:
    def __init__(self):
        self.direct_denial_patterns = [
            r'we do not',
            r'we will not',
            r'we cannot',
            r'we do not collect',
            r'we do not share',
            r'we do not disclose',
            r'no.*collect',
            r'will not.*collect',
            r'does not apply',
        ]
        self.positive_patterns = [
            r'we collect',
            r'we may collect',
            r'we share',
            r'we disclose',
        ]
        self.third_party_indicators = [
            r'third party',
            r'service provider',
            r'advertiser',
        ]
        self.uncertainty_markers = [
            r'may',
            r'might',
            r'could',
            r'as appropriate',
            r'to the extent',
        ]
    
    def detect(self, text: str, obligation_id: str | None = None) -> list[PolarityFinding]:
        findings = []
        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            findings.extend(self._analyze_sentence(sent, obligation_id))
        return findings
    
    def _analyze_sentence(self, sentence: str, obligation_id: str | None = None) -> list[PolarityFinding]:
        findings = []
        sent_lower = sentence.lower()
        
        is_third_party = any(re.search(p, sent_lower) for p in self.third_party_indicators)
        
        denial_matches = []
        for pattern in self.direct_denial_patterns:
            if re.search(pattern, sent_lower):
                denial_matches.append(pattern)
        
        positive_matches = []
        for pattern in self.positive_patterns:
            if re.search(pattern, sent_lower):
                positive_matches.append(pattern)
        
        if denial_matches and positive_matches:
            findings.append(PolarityFinding(
                text_span=sentence,
                polarity=Polarity.UNCERTAIN,
                confidence=0.6,
                matched_patterns=denial_matches + positive_matches,
                reason="Mixed denial and positive patterns in same sentence - scope unclear",
                obligation_id=obligation_id,
                is_third_party=is_third_party
            ))
        elif denial_matches and not positive_matches:
            if is_third_party and 'we' not in sent_lower and 'our' not in sent_lower:
                findings.append(PolarityFinding(
                    text_span=sentence,
                    polarity=Polarity.UNCERTAIN,
                    confidence=0.5,
                    matched_patterns=denial_matches,
                    reason="Denial appears to be about third party, not policy publisher",
                    obligation_id=obligation_id,
                    is_third_party=True
                ))
            else:
                findings.append(PolarityFinding(
                    text_span=sentence,
                    polarity=Polarity.NEGATIVE,
                    confidence=0.85,
                    matched_patterns=denial_matches,
                    reason="Direct denial pattern detected",
                    obligation_id=obligation_id,
                    is_third_party=is_third_party
                ))
        elif positive_matches and not denial_matches:
            findings.append(PolarityFinding(
                text_span=sentence,
                polarity=Polarity.POSITIVE,
                confidence=0.9,
                matched_patterns=positive_matches,
                reason="Positive disclosure pattern detected",
                obligation_id=obligation_id,
                is_third_party=is_third_party
            ))
        else:
            has_uncertainty = any(re.search(m, sent_lower) for m in self.uncertainty_markers)
            if has_uncertainty:
                findings.append(PolarityFinding(
                    text_span=sentence,
                    polarity=Polarity.UNCERTAIN,
                    confidence=0.4,
                    matched_patterns=[],
                    reason="Uncertain/conditional language",
                    obligation_id=obligation_id,
                    is_third_party=is_third_party
                ))
        return findings
    
    def has_blocking_denial(self, findings: list[PolarityFinding]) -> bool:
        for f in findings:
            if f.polarity == Polarity.NEGATIVE and f.confidence >= 0.7 and not f.is_third_party:
                return True
        return False
