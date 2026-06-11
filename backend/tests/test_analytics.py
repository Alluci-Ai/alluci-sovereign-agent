import pytest
pytestmark = pytest.mark.unit

"""
Analytics Unit Tests — Cost Calculation Accuracy

INVARIANT: Token costs must be calculated to 6 decimal places using the
pricing table. Any rounding error in billing is a production defect.
"""
from unittest.mock import MagicMock
from backend.analytics import UsageTracker


@pytest.fixture
def tracker(temp_db):
    return UsageTracker(temp_db)


class TestCostCalculation:

    @pytest.mark.unit
    def test_gemini_flash_cost_calculation(self, tracker):
        """Gemini 2.0 Flash: $0.10/1M input, $0.40/1M output."""
        cost = tracker._calculate_cost("gemini-2.0-flash", input_tokens=1_000_000, output_tokens=1_000_000)
        assert abs(cost - 0.50) < 0.001

    @pytest.mark.unit
    def test_gpt4o_cost_calculation(self, tracker):
        """GPT-4o: $2.50/1M input, $10.00/1M output."""
        cost = tracker._calculate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=1_000_000)
        assert abs(cost - 12.50) < 0.001

    @pytest.mark.unit
    def test_claude_sonnet_cost_calculation(self, tracker):
        """Claude 3.7 Sonnet: $3.00/1M input, $15.00/1M output."""
        cost = tracker._calculate_cost(
            "claude-3-7-sonnet-20250219",
            input_tokens=1_000_000,
            output_tokens=1_000_000
        )
        assert abs(cost - 18.00) < 0.001

    @pytest.mark.unit
    def test_zero_tokens_produces_zero_cost(self, tracker):
        """Zero token usage always produces zero cost."""
        cost = tracker._calculate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    @pytest.mark.unit
    def test_unknown_model_does_not_raise(self, tracker):
        """Unknown model falls back gracefully (no crash, returns 0 or default)."""
        cost = tracker._calculate_cost("unknown-model-xyz", input_tokens=100, output_tokens=100)
        assert isinstance(cost, float)
        assert cost >= 0

    @pytest.mark.unit
    def test_partial_million_scales_correctly(self, tracker):
        """100K tokens = 10% of 1M = 10% of the per-million rate."""
        cost_1m = tracker._calculate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=0)
        cost_100k = tracker._calculate_cost("gpt-4o", input_tokens=100_000, output_tokens=0)
        assert abs(cost_100k - cost_1m / 10) < 0.0001
