# Tests for polarity detection

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from research.polarity_detection import DenialPolarityDetector, Polarity


def test_direct_denial():
    detector = DenialPolarityDetector()
    findings = detector.detect("We do not collect personal data.")
    assert len(findings) > 0
    assert findings[0].polarity == Polarity.NEGATIVE
    assert detector.has_blocking_denial(findings)


def test_positive_disclosure():
    detector = DenialPolarityDetector()
    findings = detector.detect("We collect your email address.")
    assert len(findings) > 0
    assert findings[0].polarity == Polarity.POSITIVE


def test_mixed_polarity():
    detector = DenialPolarityDetector()
    findings = detector.detect("We collect emails, but we do not collect financial data.")
    assert any(f.polarity == Polarity.UNCERTAIN for f in findings)


def test_third_party():
    detector = DenialPolarityDetector()
    findings = detector.detect("Third party advertisers may collect your data.")
    assert findings[0].is_third_party or not detector.has_blocking_denial(findings)
