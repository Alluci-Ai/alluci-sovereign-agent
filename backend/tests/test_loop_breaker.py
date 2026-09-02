import pytest
from backend.inference.mlx_engine import detect_degenerative_loop, is_substantive_word

def test_is_substantive_word():
    # Markdown formatting, table delimiters, and punctuation should not be substantive
    assert not is_substantive_word("|")
    assert not is_substantive_word("---")
    assert not is_substantive_word("|---|")
    assert not is_substantive_word(":")
    assert not is_substantive_word("-")
    assert not is_substantive_word("*")
    assert not is_substantive_word("123")
    
    # Real words should be substantive
    assert is_substantive_word("Conscious")
    assert is_substantive_word("Agent")
    assert is_substantive_word("Matrix")
    assert is_substantive_word("mathematical")


def test_markdown_tables_never_trigger_loop_detection():
    # Standard multi-column markdown table header and divider
    table_tokens = [
        "Epistemic", "Status", "|", "Definition/Component", "Type", "|", "Justification/Source", "Citation",
        "\n", "|", "---", "|", "---", "|", "---", "|",
        "\n", "Literal", "|", "Mathematical", "Formalism", "|", "Page", "7", "Equation", "1",
        "\n", "Inferred", "|", "Markovian", "Kernel", "|", "Page", "8", "Section", "3"
    ]
    
    detected = detect_degenerative_loop(table_tokens)
    assert detected is None, f"Expected no loop detection on markdown table, but got '{detected}'"


def test_markdown_lists_and_dividers_never_trigger_loop_detection():
    list_tokens = [
        "-", "First", "foundational", "axiom",
        "-", "Second", "foundational", "axiom",
        "-", "Third", "foundational", "axiom",
        "-", "Fourth", "foundational", "axiom",
        "-", "Fifth", "foundational", "axiom"
    ]
    
    detected = detect_degenerative_loop(list_tokens)
    assert detected is None, f"Expected no loop detection on list, but got '{detected}'"


def test_genuine_autoregressive_collapse_detected():
    # Genuine degenerative repetition of multi-word phrase
    bad_tokens = [
        "the", "conscious", "agent", "kernel",
        "the", "conscious", "agent", "kernel",
        "the", "conscious", "agent", "kernel",
        "the", "conscious", "agent", "kernel",
        "the", "conscious", "agent", "kernel",
        "the", "conscious", "agent", "kernel"
    ]
    
    detected = detect_degenerative_loop(bad_tokens)
    assert detected is not None, "Expected loop breaker to catch genuine repetitive limit-cycle"
