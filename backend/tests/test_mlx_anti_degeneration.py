import pytest
pytestmark = pytest.mark.unit

from backend.inference.mlx_engine import detect_degenerative_loop
from mlx_lm.sample_utils import make_sampler, make_logits_processors


def test_detect_degenerative_loop_single_word():
    """Verifies that 1-gram repetitions >= 5 times trip the circuit breaker."""
    # Healthy stream
    tokens = ["The", "theorem", "establishes", "that", "the", "manifold", "is", "smooth."]
    assert detect_degenerative_loop(tokens) is None

    # Degenerative loop on 'result'
    loop_tokens = ["The", "proof", "shows", "result", "result", "result", "result", "result"]
    assert detect_degenerative_loop(loop_tokens) == "result"


def test_detect_degenerative_loop_2gram_phrase():
    """Verifies that 2-gram phrase repetitions >= 3 times trip the circuit breaker."""
    loop_tokens = ["We", "observe", "as", "well", "as", "well", "as", "well"]
    detected = detect_degenerative_loop(loop_tokens)
    assert detected == "as well"


def test_detect_degenerative_loop_3gram_phrase():
    """Verifies that 3-gram phrase repetitions >= 3 times trip the circuit breaker."""
    loop_tokens = ["state", "is", "defined", "state", "is", "defined", "state", "is", "defined"]
    detected = detect_degenerative_loop(loop_tokens)
    assert detected == "state is defined"


def test_detect_degenerative_loop_4gram_phrase():
    """Verifies that 4-gram phrase repetitions >= 3 times trip the circuit breaker."""
    loop_tokens = [
        "in", "terms", "of", "entropy",
        "in", "terms", "of", "entropy",
        "in", "terms", "of", "entropy"
    ]
    detected = detect_degenerative_loop(loop_tokens)
    assert detected == "in terms of entropy"


def test_detect_degenerative_loop_clean_academic_text():
    """Verifies that rich, authentic academic text does not trigger false positive circuit trips."""
    academic_text = (
        "The California Institute for Machine Consciousness formulates formal mathematical "
        "frameworks grounded in the Free Energy Principle, Markov kernels, and active inference. "
        "The conscious agent network establishes compatibility conditions where perceptions of one "
        "agent become the actions of another, ensuring simplicial boundary operator nilpotence."
    ).split()
    
    # Check across rolling sliding windows
    for i in range(5, len(academic_text)):
        window = academic_text[:i]
        assert detect_degenerative_loop(window) is None


def test_mlx_sampling_utilities_instantiation():
    """Verifies that make_sampler and make_logits_processors compile cleanly with top_p and repetition penalty."""
    sampler = make_sampler(temp=0.7, top_p=0.92, min_p=0.05)
    assert callable(sampler)

    processors = make_logits_processors(repetition_penalty=1.08, repetition_context_size=64)
    assert isinstance(processors, list)
    assert len(processors) >= 1
    assert callable(processors[0])
