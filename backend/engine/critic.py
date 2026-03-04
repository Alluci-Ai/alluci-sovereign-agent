import logging
from typing import Tuple
from ..inference.router import ModelRouter

logger = logging.getLogger("Engine.Critic")

class Critic:
    """
    Evaluates execution results against the original objective.
    Determines if autonomy loops should continue or halt.
    """
    def __init__(self, router: ModelRouter, threshold: float = 0.75):
        self.router = router
        self.threshold = threshold

    async def evaluate(self, objective: str, results: str) -> Tuple[bool, float, str]:
        """
        Returns (passed, score, feedback)
        """
        try:
            evaluation = await self.router.critique_result(objective, results)
            score = float(evaluation.get("score", 0.0))
            feedback = evaluation.get("feedback", "No feedback provided.")
            
            passed = score >= self.threshold
            
            log_icon = "🟢" if passed else "🔴"
            logger.info(f"{log_icon} Critic Score: {score} | Feedback: {feedback[:100]}...")
            
            return passed, score, feedback
        except Exception as e:
            logger.error(f"Critic evaluation failed: {e}")
            return False, 0.0, "Critic system error."
