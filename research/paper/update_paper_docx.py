from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parent
DOCX_PATH = ROOT / "PolarisLex_IEEE_Paper.docx"
FIGURE_DIR = ROOT / "FIGURES"


def set_columns(section, count: int) -> None:
    sect_pr = section._sectPr
    cols = sect_pr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sect_pr.append(cols)
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), "720")


def add_section_break_before(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    old = p_pr.find(qn("w:sectPr"))
    if old is not None:
        p_pr.remove(old)
    sect_pr = OxmlElement("w:sectPr")
    section_type = OxmlElement("w:type")
    section_type.set(qn("w:val"), "nextPage")
    sect_pr.append(section_type)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), "1")
    cols.set(qn("w:space"), "720")
    sect_pr.append(cols)
    p_pr.append(sect_pr)


def style_caption(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(8)


def main() -> None:
    doc = Document(DOCX_PATH)

    # Keep the title, abstract, and index terms full-width; the body begins in
    # a new one-column section and the final section is the IEEE-style body.
    intro = next((p for p in doc.paragraphs if p.text.strip() == "I. Introduction"), None)
    if intro is None:
        raise RuntimeError("Could not find the Introduction heading")
    add_section_break_before(intro)
    set_columns(doc.sections[0], 1)
    set_columns(doc.sections[-1], 2)

    # Remove a previous generated figure appendix if this script is rerun.
    figure_heading = next((p for p in doc.paragraphs if p.text.strip() == "Figures"), None)
    if figure_heading is not None:
        started = False
        for p in list(doc.paragraphs):
            if p._p is figure_heading._p:
                started = True
            if started:
                p._element.getparent().remove(p._element)

    heading = doc.add_paragraph()
    heading.style = doc.styles["Heading 1"]
    heading.add_run("Figures")

    figures = [
        ("figure1_architecture.png", "Fig. 1. PolarisLex architecture and the measured research path. Dashed services are optional production components and were not used in the pilot evaluation."),
        ("figure2_methodology.png", "Fig. 2. Reproducible pilot methodology: 42 synthetic cases, a 33/9 train-test split, four configurations, and keyword-stub retrieval."),
        ("figure3_configuration_comparison.png", "Fig. 3. Configuration comparison on the nine-case test set. All configurations have zero precision, recall, and F1 and specificity of 1.000; the result is degenerate because no case is predicted covered."),
        ("figure4_confusion_matrix.png", "Fig. 4. Confusion matrix for the covered positive class across the evaluated configurations: TP=0, FN=2, FP=0, and TN=7."),
        ("figure5_feature_impact.png", "Fig. 5. Feature impact summary. Requirement decomposition changes no final statuses; polarity-aware and combined modes change SYN_010 and SYN_027 from partial to violation, without aggregate metric improvement."),
    ]
    for filename, caption in figures:
        image_path = FIGURE_DIR / filename
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        image_paragraph = doc.add_paragraph()
        image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        image_paragraph.add_run().add_picture(str(image_path), width=Inches(3.15))
        caption_paragraph = doc.add_paragraph(caption)
        style_caption(caption_paragraph)

    doc.core_properties.title = "Beyond Keyword Matching: A Preliminary Evaluation of Requirement Decomposition and Polarity Awareness in Indian Privacy-Policy Compliance Analysis"
    doc.core_properties.subject = "PolarisLex preliminary research paper"
    doc.core_properties.author = "PolarisLex Research Project"
    doc.save(DOCX_PATH)
    print(f"Updated {DOCX_PATH}")


if __name__ == "__main__":
    main()
