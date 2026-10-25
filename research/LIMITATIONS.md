# Limitations

## Dataset Limitations
- Pilot dataset is small (10 synthetic cases currently)
- Labels are researcher-annotated, not reviewed by legal experts
- Synthetic cases may not reflect real policy complexity
- Limited coverage of all obligations

## Methodological Limitations
- Denial-polarity detection uses rule-based patterns, not full NLP
- Element decomposition relies on existing duty_rules structure
- Cannot claim statistical significance with small sample
- Policy-level clustering not fully implemented in split logic

## Technical Limitations
- Integration with full compliance pipeline in evaluation harness is partial (placeholder)
- Some tests may require Qdrant/Ollama running
- Jev tests have pre-existing failures

## Threats to Validity
- Internal: configuration differences between runs
- External: generalizability to other jurisdictions
- Construct: mapping between system statuses and research labels
- Conclusion: correlation vs causation for feature effects
