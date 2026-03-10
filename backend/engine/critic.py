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

    async def evaluate(self, objective: str, results: str, psi: float = 0.0) -> Tuple[bool, float, str]:
        """
        Returns (passed, score, feedback)
        """
        try:
            evaluation = await self.router.critique_result(objective, results)
            score = float(evaluation.get("score", 0.0))
            feedback = evaluation.get("feedback", "No feedback provided.")
            
            # AAP-005: Critic ψ-Weighted Score.
            # High tension (psi) increases the threshold for success.
            dynamic_threshold = self.threshold + (0.15 * psi)
            passed = score >= dynamic_threshold
            
            log_icon = "🟢" if passed else "🔴"
            logger.info(f"{log_icon} Critic Score: {score} (Thresh: {dynamic_threshold:.2f}) | Psi: {psi:.2f}")
            
            return passed, score, feedback
        except Exception as e:
            logger.error(f"Critic evaluation failed: {e}")
            return False, 0.0, "Critic system error."
