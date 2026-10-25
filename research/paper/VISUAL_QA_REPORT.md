# PolarisLex Paper Visual QA Report

Date: 2026-10-25

## Artifacts checked

- Word manuscript: `PolarisLex_IEEE_Paper.docx`
- Source manuscript: `PolarisLex_IEEE_Paper.md`
- Figure generator: `FIGURES/generate_figures.py`
- Raster figures: five 300-DPI PNG files in `FIGURES/`
- Vector figures: five SVG files in `FIGURES/`
- Independent metrics: `results/phase3_20261025_173000/independent_metrics.json`
- Confusion matrices: `results/phase3_20261025_173000/confusion_matrices.json`

## Automated checks

The final DOCX was reopened successfully with `python-docx` and contains:

- 2 sections: a 1-column opening section and a 2-column main-body section;
- 5 embedded inline figures;
- 5 figure captions labeled Fig. 1 through Fig. 5;
- 3 existing data tables;
- the manuscript title, abstract, references [1]–[8], and the verified pilot metrics.

The figure generator was rerun successfully after DOCX assembly. The generated figures encode the verified results: 42 total synthetic cases, a 33/9 split, and for every configuration TP=0, FP=0, TN=7, FN=2, precision=0, recall=0, F1=0, specificity=1, and false-covered rate=0. The feature-impact figure also matches the independent case comparison: decomposition changes no final status, while polarity-aware and combined modes change SYN_010 and SYN_027 to violation even though both gold labels are partial.

## Layout decisions

The title, abstract, and index terms remain full-width. The main paper begins at “I. Introduction” in a two-column section. Figures are embedded at the end of the manuscript with centered captions so that the source document remains editable and reproducible.

## Limitation and manual review

No LibreOffice, Microsoft Word automation interface, `soffice`, or `pandoc` renderer was available in the execution environment. Therefore, this report verifies the DOCX package structure, embedded media, captions, section XML, and source/result consistency, but it does not claim pixel-level rendering approval. A final manual opening in Microsoft Word or LibreOffice should check column flow, figure legibility, page breaks, and caption placement before submission.
