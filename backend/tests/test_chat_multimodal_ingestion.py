import os
import io
import base64
import pytest
from backend.utils.doc_parser import extract_document_and_figures_from_payload, extract_text_from_file_payload
from backend.routers.gemini import _process_attached_files
from PIL import Image

@pytest.fixture
def sample_pdf_with_figures():
    """Generates a synthetic PDF with text and a figure image using pypdf and PIL."""
    import pypdf
    from pypdf import PdfWriter

    writer = PdfWriter()
    # Create an image
    im = Image.new("RGB", (300, 200), color=(100, 150, 200))
    img_byte_arr = io.BytesIO()
    im.save(img_byte_arr, format="PNG")
    img_data = img_byte_arr.getvalue()

    # Create a page and add image
    page = writer.add_blank_page(width=612, height=792)
    
    # We can write out the PDF bytes
    pdf_out = io.BytesIO()
    writer.write(pdf_out)
    return pdf_out.getvalue()


@pytest.mark.asyncio
async def test_extract_document_and_figures_from_real_hoffman_paper():
    """Tests extracting text and figures from the real Hoffman paper on disk."""
    paper_path = "/Users/alluci/Downloads/Hoffman Papers/Hoffman_Objects of Consciousness.pdf"
    if not os.path.exists(paper_path):
        pytest.skip(f"Paper not found at {paper_path}")

    with open(paper_path, "rb") as f:
        pdf_bytes = f.read()

    b64_data = base64.b64encode(pdf_bytes).decode("utf-8")
    text, figures = extract_document_and_figures_from_payload(
        file_name="Hoffman_Objects of Consciousness.pdf",
        file_data_base64=b64_data,
        file_mime="application/pdf"
    )

    assert len(text) > 5000, "Text extraction failed"
    assert "Conscious" in text or "consciousness" in text
    assert len(figures) == 8, f"Expected 8 substantive technical figures, got {len(figures)}"

    # Check pages 7, 8, 9 figures
    figure_pages = [f["page_number"] for f in figures]
    assert 7 in figure_pages
    assert 8 in figure_pages
    assert 9 in figure_pages

    # Check disk existence
    for fig in figures:
        assert os.path.exists(fig["file_path"]), f"Extracted figure file missing: {fig['file_path']}"

    # Test prompt processing
    test_files = [{
        "name": "Hoffman_Objects of Consciousness.pdf",
        "data": b64_data,
        "mimeType": "application/pdf"
    }]
    augmented_prompt, attached_figures = _process_attached_files(
        prompt="Explain the Conscious Agent kernel loop in Hoffman's paper with diagrams.",
        files=test_files
    )

    assert len(attached_figures) == 8
    assert "--- [ATTACHED TECHNICAL FIGURES & DIAGRAMS (EXTRACTED VISUAL ASSETS)] ---" in augmented_prompt
    assert "/api/v1/artifacts/extracted_figures/hoffman_objects_of_consciousness/" in augmented_prompt
    assert "![Figure" in augmented_prompt
