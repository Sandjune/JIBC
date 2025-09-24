
# JIBC Workshops Navigator (updated)
# - Shows PDF as images (best effort via PyMuPDF). Fallback: embedded viewer.
# - Adds section navigation for DISCOVERY, DESIGN, REQUIREMENTS, INTEGRATION, ROADMAP, FINALIZATION.
# - Displays content extracted from the Word guidebook for the selected section.
#
# Files expected (adjust paths as needed):
#   PDF:   /mnt/data/JIBC_Workshops_Facilitator_Dashboard_Phased_Timeline.pdf
#   DOCX:  /mnt/data/JIBC_Workshop_Facilitation_Guidebook_Full.docx

import os
import io
from typing import Dict, List, Tuple
from docx import Document as DocxDocument

import streamlit as st
from streamlit.components.v1 import html

# Optional imports for PDF->image and DOCX parsing
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None


PDF_PATH = "/mnt/data/JIBC_Workshops_Facilitator_Dashboard_Phased_Timeline.pdf"
DOCX_PATH = "/mnt/data/JIBC_Workshop_Facilitation_Guidebook_Full.docx"

SECTIONS = ["DISCOVERY", "DESIGN", "REQUIREMENTS", "INTEGRATION", "ROADMAP", "FINALIZATION"]


def pdf_to_images(pdf_path: str) -> List[bytes]:
    """Convert a PDF to a list of PNG images (bytes). Returns [] if not possible."""
    if fitz is None:
        return []
    if not os.path.exists(pdf_path):
        return []
    try:
        doc = fitz.open(pdf_path)
        images = []
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            # 2x zoom for readability
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
        return images
    except Exception as e:
        return []


def embed_pdf_viewer(pdf_path: str, height: int = 820):
    """Fallback embedded PDF if we can't render to images."""
    if not os.path.exists(pdf_path):
        st.warning(f"PDF not found at {pdf_path}")
        return
    # Display using an iframe/embed; Streamlit will serve the local path in sandbox
    pdf_url = f"{pdf_path}"
    html_code = f"""
    <div style='border:1px solid #ddd;border-radius:8px;overflow:hidden;'>
      <embed src='{pdf_url}' type='application/pdf' width='100%' height='{height}px' />
    </div>
    """
    html(html_code, height=height + 10)


def extract_sections_from_docx(docx_path: str) -> Dict[str, str]:
    """Parse the Word doc and extract text under the six top-level sections.
    We match by heading text that *contains* the section name (case-insensitive).
    Returns mapping: SECTION -> combined markdown text.
    """
    result = {s: [] for s in SECTIONS}
    if DocxDocument is None or not os.path.exists(docx_path):
        return {s: f"*(No content parsed. Ensure {docx_path} exists and python-docx is available.)*" for s in SECTIONS}

    doc = DocxDocument(docx_path)

    # We'll sweep through paragraphs and collect content under best-match headings.
    current_section = None
    for para in doc.paragraphs:
        text = (para.text or '').strip()
        if not text:
            continue
        style_name = getattr(para.style, "name", "")
        text_upper = text.upper()

        # Try to detect a heading that belongs to one of our sections
        if "HEADING" in style_name.upper():
            for sec in SECTIONS:
                if sec in text_upper:
                    current_section = sec
                    # Add a visible heading in output
                    result[sec].append(f"\n### {text}\n")
                    break
            else:
                # Some heading that's not one of our six -> allow text to continue under current_section.
                pass
        else:
            # Regular paragraph
            if current_section:
                result[current_section].append(text)

    # Join paragraphs; basic markdown bullet heuristics
    result = {k: "\n\n".join(v) if v else "*(No section content found)*" for k, v in result.items()}
    return result


def show_sidebar_navigation():
    st.sidebar.title("Workshops Navigator")
    st.sidebar.markdown("Select a phase to view its content.")
    for sec in SECTIONS:
        if st.sidebar.button(sec, use_container_width=True, key=f"nav_{sec}"):
            st.session_state.current_section = sec
    st.sidebar.markdown("---")

    # Back to PDF button
    if st.sidebar.button("Show Dashboard PDF", use_container_width=True, key="show_pdf"):
        st.session_state.current_section = None


def show_pdf_as_images_or_embed():
    st.subheader("Facilitator’s Dashboard")
    st.caption("Rendered as image(s) for quick viewing. If images are unavailable, the PDF viewer is embedded below.")
    images = pdf_to_images(PDF_PATH)
    if images:
        for i, img_bytes in enumerate(images, 1):
            st.image(img_bytes, caption=f"Dashboard Page {i}", use_container_width=True)
    else:
        embed_pdf_viewer(PDF_PATH, height=860)


def main():
    st.set_page_config(page_title="JIBC Workshops Navigator", page_icon="🗂️", layout="wide", initial_sidebar_state="expanded")
    if "current_section" not in st.session_state:
        st.session_state.current_section = None

    show_sidebar_navigation()

    st.title("JIBC Workshops – Phased Navigator")
    st.write("This app displays the phased dashboard PDF and lets you jump to content sections from the full facilitation guidebook.")

    # Parse Word doc sections
    sections_map = extract_sections_from_docx(DOCX_PATH)

    if st.session_state.current_section is None:
        show_pdf_as_images_or_embed()
    else:
        sec = st.session_state.current_section
        st.subheader(f"{sec} — Facilitation Guidebook Extract")
        content = sections_map.get(sec, "*(No content found for this section.)*")
        st.markdown(content)
        st.info("Use the sidebar to switch sections or click 'Show Dashboard PDF' to return to the image.")


if __name__ == "__main__":
    main()
