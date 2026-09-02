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
    
    # LaTeX structural tokens should not be substantive
    assert not is_substantive_word("\\text{")
    assert not is_substantive_word("text")
    assert not is_substantive_word("\\quad")
    assert not is_substantive_word("qquad")
    assert not is_substantive_word("frac")
    assert not is_substantive_word("cdot")
    assert not is_substantive_word("pmatrix")
    
    # Real semantic words should be substantive
    assert is_substantive_word("Conscious")
    assert is_substantive_word("Agent")
    assert is_substantive_word("Matrix")
    assert is_substantive_word("mathematical")


def test_latex_equation_alignment_spaces_never_trigger_loop_detection():
    # The exact sequence from Hoffman Markov kernel equation
    latex_tokens = [
        "L(e,\\mathcal{E}\\times\\mathcal{E})", "&=", "\\prod_{i=1}^{2n}(P_i(g_{2i-1},X_i)\\cdot",
        "D_i(X_{2i-2},G_{2i-1})\\cdot", "A_{2i-1}(g_{2i-2},X_{2i})\\nonumber\\\\",
        "&\\text{", "}", "\\text{", "}", "\\text{", "}", "\\text{", "}", "\\text{", "}", "\\text{", "}", "\\text{", "}"
    ]
    
    detected = detect_degenerative_loop(latex_tokens)
    assert detected is None, f"Expected no loop detection on LaTeX alignment spaces, but got '{detected}'"


def test_zero_matrices_never_trigger_loop_detection():
    matrix_tokens = [
        "\\begin{pmatrix}",
        "0", "&", "0", "&", "0", "&", "0", "\\\\",
        "0", "&", "0", "&", "0", "&", "0", "\\\\",
        "0", "&", "0", "&", "0", "&", "0",
        "\\end{pmatrix}"
    ]
    
    detected = detect_degenerative_loop(matrix_tokens)
    assert detected is None, f"Expected no loop detection on matrix zeros, but got '{detected}'"


def test_markdown_tables_never_trigger_loop_detection():
    table_tokens = [
        "Epistemic", "Status", "|", "Definition/Component", "Type", "|", "Justification/Source", "Citation",
        "\n", "|", "---", "|", "---", "|", "---", "|",
        "\n", "Literal", "|", "Mathematical", "Formalism", "|", "Page", "7", "Equation", "1",
        "\n", "Inferred", "|", "Markovian", "Kernel", "|", "Page", "8", "Section", "3"
    ]
    
    detected = detect_degenerative_loop(table_tokens)
    assert detected is None, f"Expected no loop detection on markdown table, but got '{detected}'"


def test_genuine_multi_word_autoregressive_collapse_detected():
    # Genuine degenerative repetition of multi-word phrase
    bad_tokens = [
        "conscious", "agent", "dynamics",
        "conscious", "agent", "dynamics",
        "conscious", "agent", "dynamics",
        "conscious", "agent", "dynamics",
        "conscious", "agent", "dynamics",
        "conscious", "agent", "dynamics"
    ]
    
    detected = detect_degenerative_loop(bad_tokens)
    assert detected is not None, "Expected loop breaker to catch genuine repetitive limit-cycle"
