---
name: Policy heading fixtures
overview: "Synthetic policy fixture library plus heading-detector patches driven by those gold lists. HTML parser and SQLite stay out of scope."
todos:
  - id: fixtures
    content: Six synthetic policy .txt files + expected.json gold heading lists
    status: completed
  - id: regression-test
    content: Parametrized HeadingDetector/SectionExtractor test over the fixture library
    status: completed
  - id: detector-patches
    content: Patch STANDALONE (and only other gaps the fixtures expose); keep country-list tests green
    status: completed
isProject: true
---

# Policy fixture library + heading patches

> **For agentic workers:** Use executing-plans. TDD: fixtures and failing tests first, then detector patches.

**Goal:** Regression suite of original synthetic policies with gold heading titles; fix `HeadingDetector` only where that suite fails.

**Architecture:** `.txt` + sidecar `.expected.json` under `document_pipeline/tests/fixtures/policies/`. Tests assert exact ordered titles from `HeadingDetector.detect`. `SectionExtractor` titled sections must match the same list. Country-list collapse stays.

**Tech Stack:** pytest, existing `HeadingDetector` / `SectionExtractor`.

## Global Constraints

- Original synthetic text only (no copyrighted Snap/GitHub policies).
- Exact ordered heading titles (not snapshots of current detector output).
- Do not auto-delete Qdrant; do not add SQLite or HTML parser.
- Keep `test_country_list_section.py` and existing heading unit tests green.

## Files

- Create: `document_pipeline/tests/fixtures/policies/{github_style,snap_style,numbered_statute,faq,uppercase_articles,mixed_policy}.{txt,expected.json}`
- Create: `document_pipeline/tests/test_policy_fixtures.py`
- Modify: `document_pipeline/src/document_pipeline/sectioning/heading_detector.py` only as tests require

## Likely detector gaps

- STANDALONE treats start-of-document as not blank-before (`previous_line is None`).
- STANDALONE requires a blank line after; scraped policies often put body on the next line.
- Do not weaken list-run collapse (`_LIST_ITEM_MAX_WORDS == 2`).
