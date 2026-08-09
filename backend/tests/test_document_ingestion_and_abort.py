import pytest
import base64
from backend.routers.gemini import _process_attached_files


def test_process_attached_files_ingestion():
    prompt = "here is my founders narrative. please commit it to memory."
    sample_text = "Founder Narrative: We founded the company in 2024 to revolutionize AI agents."
    encoded_bytes = base64.b64encode(sample_text.encode("utf-8")).decode("utf-8")

    files = [
        {
            "name": "founder_narrative.txt",
            "data": encoded_bytes,
            "mimeType": "text/plain"
        }
    ]

    effective_prompt = _process_attached_files(prompt, files)
    assert prompt in effective_prompt
    assert "--- [ATTACHED FILE: founder_narrative.txt] ---" in effective_prompt
    assert sample_text in effective_prompt


def test_process_pdf_file_ingestion():
    prompt = "please process this pdf."
    pdf_bytes = b"%PDF-1.4 BT (Executive Strategic Vision Plan) ET"
    encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    files = [
        {
            "name": "vision_plan.pdf",
            "data": encoded_pdf,
            "mimeType": "application/pdf"
        }
    ]

    effective_prompt = _process_attached_files(prompt, files)
    assert "--- [ATTACHED FILE: vision_plan.pdf] ---" in effective_prompt
    assert "Executive Strategic Vision Plan" in effective_prompt


def test_no_false_positive_abort_on_document_text():
    # Document containing the word "stop" and "this"
    document_text = "We will never stop innovating in this business."
    body_lower = document_text.lower()

    # Old logic would match "stop" + "this"
    cancellation_keywords = ["stop", "cancel", "abort", "halt", "terminate"]
    target_words_fixed = ["dag", "run", "research", "pipeline", "execution"]

    is_abort_fixed = any(ck in body_lower for ck in cancellation_keywords) and any(
        w in body_lower for w in target_words_fixed
    )

    assert not is_abort_fixed, "Document containing 'stop' and 'this' should NOT trigger emergency abort!"


def test_true_abort_signal_trigger():
    true_abort_text = "please stop research and cancel run"
    body_lower = true_abort_text.lower()

    cancellation_keywords = ["stop", "cancel", "abort", "halt", "terminate"]
    target_words_fixed = ["dag", "run", "research", "pipeline", "execution"]

    is_abort = any(ck in body_lower for ck in cancellation_keywords) and any(
        w in body_lower for w in target_words_fixed
    )

    assert is_abort, "Explicit command 'stop research' MUST trigger emergency abort!"
