
# JIBC Workshops Navigator (updated v2)
# - Shows PDF as images (best effort via PyMuPDF). Fallback: embedded viewer.
# - Adds left navigation for DISCOVERY, DESIGN, REQUIREMENTS, INTEGRATION, ROADMAP, FINALIZATION.
# - Robust DOCX parsing with forgiving heading detection + fallback scanning.
#
# Files expected (adjust as needed or upload in the UI):
#   PDF:  /mnt/data/JIBC_Workshops_Facilitator_Dashboard_Phased_Timeline.pdf
#   DOCX: /mnt/data/JIBC_Workshop_Facilitation_Guidebook_Full.docx

import os
import io
import re
from typing import Dict, List, Optional

import streamlit as st
from streamlit.components.v1 import html

# Optional imports for PDF->image and DOCX parsing
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from docx import Document as DocxDocument
    from docx.text.paragraph import Paragraph as DocxParagraph
except Exception:
    DocxDocument = None
    DocxParagraph = None

DEFAULT_PDF = "/mnt/data/JIBC_Workshops_Facilitator_Dashboard_Phased_Timeline.pdf"
DEFAULT_DOCX = "/mnt/data/JIBC_Workshop_Facilitation_Guidebook_Full.docx"

SECTIONS = ["DISCOVERY", "DESIGN", "REQUIREMENTS", "INTEGRATION", "ROADMAP", "FINALIZATION"]

PHASE_PATTERNS = {
    "DISCOVERY": re.compile(r"\bdiscovery\b", re.I),
    "DESIGN": re.compile(r"\bdesign\b", re.I),
    "REQUIREMENTS": re.compile(r"\brequirement(s)?\b", re.I),
    "INTEGRATION": re.compile(r"\bintegration(s)?\b", re.I),
    "ROADMAP": re.compile(r"\broadmap\b", re.I),
    "FINALIZATION": re.compile(r"\bfinali[sz]ation|final readout|approval\b", re.I),
}


def pdf_to_images(pdf_path: str) -> List[bytes]:
    """Convert a PDF to a list of PNG images (bytes). Returns [] if not possible."""
    if fitz is None or not os.path.exists(pdf_path):
        return []
    try:
        doc = fitz.open(pdf_path)
        images = []
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            zoom = 2.0  # bump for readability
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
        return images
    except Exception:
        return []


def embed_pdf_viewer(pdf_path: str, height: int = 820):
    """Fallback embedded PDF if we can't render to images."""
    if not os.path.exists(pdf_path):
        st.warning(f"PDF not found at {pdf_path}")
        return
    html_code = f"""
    <div style='border:1px solid #ddd;border-radius:8px;overflow:hidden;'>
      <embed src='{pdf_path}' type='application/pdf' width='100%' height='{height}px' />
    </div>
    """
    html(html_code, height=height + 10)


def _append_line(buckets: Dict[str, List[str]], current: Optional[str], text: str):
    if not current:
        return
    if text.strip():
        buckets[current].append(text.strip())


def extract_sections_from_docx(docx_path: str) -> Dict[str, str]:
    """
    Parse the Word doc and extract text under the six top-level sections.
    Strategy:
      1) Prefer Heading-style paragraphs; if heading contains a phase word (anywhere), switch target bucket.
      2) If headings are inconsistent, also scan any paragraph for phase keywords and treat as a heading.
      3) Keep appending paragraphs to the current section until we switch.
    Returns mapping: SECTION -> combined markdown text (or a helpful message).
    """
    out = {s: [] for s in SECTIONS}
    if DocxDocument is None:
        return {s: f"*(python-docx not available — install with `pip install python-docx`)*" for s in SECTIONS}
    if not os.path.exists(docx_path):
        return {s: f"*(DOCX not found at {docx_path})*" for s in SECTIONS}

    doc = DocxDocument(docx_path)
    current_section: Optional[str] = None

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue

        style_name = getattr(getattr(para, "style", None), "name", "") or ""
        text_upper = text.upper()

        # 1) Heading-based detection
        is_heading = "HEADING" in style_name.upper()
        if is_heading:
            matched = False
            for sec, pattern in PHASE_PATTERNS.items():
                if pattern.search(text):
                    current_section = sec
                    out[sec].append(f"### {text}")
                    matched = True
                    break
            if matched:
                continue  # we set current_section and added this heading; move to next paragraph

        # 2) Non-heading paragraph that *looks* like a section change
        for sec, pattern in PHASE_PATTERNS.items():
            if pattern.search(text) and text.isupper() or pattern.search(text) and len(text.split()) <= 6:
                current_section = sec
                out[sec].append(f"### {text}")
                break
        else:
            # 3) Regular content: append under the current section if set
            _append_line(out, current_section, text)

    # Finalize join
    return {k: ("\n\n".join(v) if v else "*(No section content found — check headings/keywords in the DOCX)*") for k, v in out.items()}


def show_sidebar_navigation():
    st.sidebar.title("Workshops Navigator")
    st.sidebar.caption("Click a phase to load content from the guidebook.")
    for sec in SECTIONS:
        if st.sidebar.button(sec, use_container_width=True, key=f"nav_{sec}"):
            st.session_state.current_section = sec
    st.sidebar.markdown("---")
    if st.sidebar.button("Show Dashboard PDF", use_container_width=True, key="show_pdf"):
        st.session_state.current_section = None


def show_pdf(pdf_path: str):
    st.subheader("Facilitator’s Dashboard")
    st.caption("Rendered as image(s). If images are unavailable, the PDF viewer is embedded.")
    images = pdf_to_images(pdf_path)
    if images:
        for i, img_bytes in enumerate(images, 1):
            st.image(img_bytes, caption=f"Dashboard Page {i}", use_container_width=True)
    else:
        embed_pdf_viewer(pdf_path, height=860)


def diagnostics(pdf_path: str, docx_path: str):
    st.sidebar.markdown("### Diagnostics")
    st.sidebar.write(f"**python-docx available:** {'✅' if DocxDocument else '❌'}")
    st.sidebar.write(f"**PyMuPDF (fitz) available:** {'✅' if fitz else '❌'}")
    st.sidebar.write(f"**PDF found:** {'✅' if os.path.exists(pdf_path) else '❌'}")
    st.sidebar.write(f"**DOCX found:** {'✅' if os.path.exists(docx_path) else '❌'}")


def main():
    st.set_page_config(page_title="JIBC Workshops Navigator", page_icon="🗂️", layout="wide", initial_sidebar_state="expanded")
    if "current_section" not in st.session_state:
        st.session_state.current_section = None

    st.title("JIBC Workshops – Phased Navigator")

    # Allow path overrides / uploads
    with st.sidebar.expander("Files", expanded=False):
        pdf_path = st.text_input("PDF path", value=DEFAULT_PDF)
        docx_path = st.text_input("DOCX path", value=DEFAULT_DOCX)
        uploaded_pdf = st.file_uploader("Or upload a PDF", type=["pdf"], key="pdf_up")
        uploaded_docx = st.file_uploader("Or upload a DOCX", type=["docx"], key="docx_up")
        if uploaded_pdf is not None:
            tmp_pdf = "/mnt/data/_uploaded_dashboard.pdf"
            with open(tmp_pdf, "wb") as f:
                f.write(uploaded_pdf.read())
            pdf_path = tmp_pdf
        if uploaded_docx is not None:
            tmp_docx = "/mnt/data/_uploaded_guidebook.docx"
            with open(tmp_docx, "wb") as f:
                f.write(uploaded_docx.read())
            docx_path = tmp_docx

    diagnostics(pdf_path, docx_path)
    show_sidebar_navigation()

    st.write("This app shows the phased dashboard PDF and lets you jump to content sections from the full facilitation guidebook.")
    sections_map = extract_sections_from_docx(docx_path)

    if st.session_state.current_section is None:
        show_pdf(pdf_path)
    else:
        sec = st.session_state.current_section
        st.subheader(f"{sec} — Facilitation Guidebook Extract")
        content = sections_map.get(sec, "*(No content found for this section.)*")
        st.markdown(content)
        st.info("Use the sidebar to switch sections or click 'Show Dashboard PDF' to return to the image.")

if __name__ == "__main__":
    main()
