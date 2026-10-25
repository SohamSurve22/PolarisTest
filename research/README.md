# Research Evaluation Framework for PolarisLex

## Overview

This directory contains the experimental infrastructure for evaluating:
> "Requirement-Element Decomposition and Denial-Polarity Detection for Reducing False-Covered Errors in Automated Privacy Compliance Auditing"

## Configurations

| Config | Name | Description |
|--------|------|-------------|
| A | baseline | Existing baseline (element decomposition off, denial-polarity off) |
| B | element_decomp | Element decomposition on, denial-polarity off |
| C | polarity_aware | Element decomposition off, denial-polarity on |
| D | combined | Both features on |

## Structure

`
research/
+-- README.md (this file)
+-- IMPLEMENTATION_AUDIT.md
+-- METHODOLOGY.md
+-- ANNOTATION_GUIDELINES.md
+-- RESULTS.md
+-- LIMITATIONS.md
+-- evaluate.py
+-- src/research/
¦   +-- config.py
¦   +-- element_decomposition.py
¦   +-- polarity_detection.py
¦   +-- metrics.py
+-- datasets/
¦   +-- cases.jsonl
¦   +-- annotations.jsonl
¦   +-- dataset_card.md
¦   +-- annotation_guidelines.md
¦   +-- data_manifest.json
+-- results/
+-- figures/
`

## Running Experiments

`ash
# Activate venv
.venv\Scripts\activate  # Windows
# or source .venv/bin/activate on Linux/Mac

# Run evaluation
python research/evaluate.py --dataset research/datasets/cases.jsonl --split test
`

## Checklist
- [x] Stage 1 - Audit completed (IMPLEMENTATION_AUDIT.md)
- [ ] Stage 2 - Design (METHODOLOGY.md, schemas)
- [ ] Stage 3 - Implementation (configs, modules, harness)
- [ ] Stage 4 - Tests
- [ ] Stage 5 - Pilot
- [ ] Stage 6 - Experiments
- [ ] Stage 7 - Figures and documentation
