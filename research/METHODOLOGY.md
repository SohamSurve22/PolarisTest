# Methodology

## Experimental Design

We compare four configurations A, B, C, D using the same dataset, retrieval settings, and scoring protocol.

### Configurations
- **A (Baseline)**: Existing semantic retrieval, element decomposition off, denial-polarity filtering off
- **B (Element decomposition)**: Existing semantic retrieval + atomic requirement-element decomposition on
- **C (Polarity-aware)**: Existing semantic retrieval + denial-polarity filtering on  
- **D (Combined)**: Existing semantic retrieval + both features on

### Baseline
From actual codebase inspection:
- Retrieval threshold (PARTIAL_SCORE): 0.30
- Covered threshold (COVERED_SCORE): 0.55
- Element covered ratio (ELEMENT_COVERED_RATIO): 0.60
- Denial lexicon: cannot, without obtaining, does not, will not, no dedicated, waive, irrevocable

### Metrics
- **Precision/Recall/F1**: Standard classification metrics
- **False-Covered Rate (FCR)**: FP / (FP + TN) where "covered" means fully covered status. This measures cases where system incorrectly marks obligation as covered when it should not be.
- **False-Negative Rate (FNR)**: FN / (TP + FN)
- **Element-level Precision/Recall/F1**: For requirement element satisfaction
- **Macro-F1**: Unweighted average across classes

### Data Splits
- Development set: for tuning (if needed)
- Validation set: for model selection
- Held-out test set: frozen, never used for tuning

Policy-level grouping maintained to avoid leakage.

### Research Integrity
- Gold labels established independently, not from system predictions
- Synthetic cases labeled as synthetic
- Uncertain cases marked as uncertain
- Negative results reported
- No fabrication of results
