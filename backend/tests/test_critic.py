"""
Critic Unit Tests

Tests score evaluation, threshold enforcement, and error handling.
"""
import pytest
from backend.engine.critic import Critic
from unittest.mock import AsyncMock


class TestCritic:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_high_score_passes(self, mock_router):
        """Score >= threshold returns passed=True."""
        mock_router.critique_result = AsyncMock(return_value={"score": 0.95, "feedback": "Excellent"})
        critic = Critic(mock_router, threshold=0.75)
        passed, score, feedback = await critic.evaluate("test objective", "test results")
        assert passed is True
        assert score == 0.95

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_low_score_fails(self, mock_router):
        """Score < threshold returns passed=False."""
        mock_router.critique_result = AsyncMock(return_value={"score": 0.45, "feedback": "Incomplete"})
        critic = Critic(mock_router, threshold=0.75)
        passed, score, feedback = await critic.evaluate("test objective", "test results")
        assert passed is False
        assert score == 0.45

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_threshold_boundary(self, mock_router):
        """Score exactly at threshold passes (>= not >)."""
        mock_router.critique_result = AsyncMock(return_value={"score": 0.75, "feedback": "At threshold"})
        critic = Critic(mock_router, threshold=0.75)
        passed, score, _ = await critic.evaluate("objective", "results")
        assert passed is True
        assert score == 0.75

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_router_failure_returns_safe_defaults(self, failing_router):
        """If the LLM fails, critic returns passed=False with score=0.0 (fail-safe)."""
        critic = Critic(failing_router, threshold=0.75)
        passed, score, feedback = await critic.evaluate("objective", "results")
        assert passed is False
        assert score == 0.0
        assert len(feedback) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_numeric_score_handled_gracefully(self, mock_router):
        """Non-numeric score from LLM falls back to 0.0 without raising."""
        mock_router.critique_result = AsyncMock(return_value={"score": "high", "feedback": "ok"})
        critic = Critic(mock_router, threshold=0.75)
        passed, score, _ = await critic.evaluate("objective", "results")
        assert isinstance(score, float)
