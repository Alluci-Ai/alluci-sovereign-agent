
from ..logging_config import get_logger
from typing import List, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import GoalRecord

logger = get_logger("GoalsEngine")

class GoalsEngine:
    """
    Sovereign Goals Engine.
    Manages long-running objectives and hierarchical task breakdown with DB persistence.
    """
    def __init__(self, engine=None):
        self.engine = engine or db_engine

    async def create_goal(self, title: str, description: str, priority: str = "MEDIUM", target: float = 100.0) -> int:
        with Session(self.engine) as session:
            goal = GoalRecord(
                title=title,
                description=description,
                priority=priority,
                status="active",
                metric_target=target,
                metric_current=0.0
            )
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal.id  # type: ignore

    async def update_goal(self, goal_id: int, status: str = None, progress: float = None, description: str = None):  # type: ignore
        with Session(self.engine) as session:
            goal = session.get(GoalRecord, goal_id)
            if goal:
                if status: goal.status = status
                if progress is not None: goal.metric_current = progress
                if description: goal.description = description
                goal.updated_at = datetime.now(timezone.utc)
                
                # Auto-complete if target met
                if goal.metric_target and goal.metric_current >= goal.metric_target:
                    goal.status = "achieved"
                    
                session.add(goal)
                session.commit()
                return True
        return False

    async def get_goal(self, goal_id: int) -> Optional[GoalRecord]:
        with Session(self.engine) as session:
            return session.get(GoalRecord, goal_id)

    async def delete_goal(self, goal_id: int) -> bool:
        with Session(self.engine) as session:
            goal = session.get(GoalRecord, goal_id)
            if goal:
                session.delete(goal)
                session.commit()
                return True
        return False

    async def list_goals(self, status: Optional[str] = None) -> List[GoalRecord]:
        with Session(self.engine) as session:
            stmt = select(GoalRecord)
            if status:
                stmt = stmt.where(GoalRecord.status == status)
            return session.exec(stmt).all()  # type: ignore

    async def evaluate_progress(self, goal_id: int):
        """
        Calculates goal progress using the LLM to analyze completed task evidence.
        Sets 'metric_current' based on the percentage of objective completion.
        """
        from ..inference.router import ModelRouter
        from ..config import settings
        from ..models import TaskRecord

        goal = await self.get_goal(goal_id)
        if not goal:
            return None

        logger.info(f"🎯 [GOAL_EVAL]: Evaluating progress for '{goal.title}'")

        # 1. Gather evidence (all tasks for this goal)
        with Session(self.engine) as session:
            tasks = session.exec(select(TaskRecord).where(TaskRecord.goal_id == goal_id)).all()  # type: ignore

        if not tasks:
            logger.info("[GOAL_EVAL]: No tasks found for this goal.")
            return goal.metric_current

        # 2. Format evidence for the LLM
        evidence = "\n".join([
            f"- Task: {t.title}\n  Result: {t.result or 'In progress'}\n  Status: {t.status}"  # type: ignore
            for t in tasks
        ])

        prompt = f"""
        SYSTEM: You are the Sovereign Goal Auditor.
        OBJECTIVE: "{goal.title}"
        DESCRIPTION: "{goal.description}"
        
        TASK EVIDENCE:
        {evidence}
        
        INSTRUCTION:
        Based on the results of the tasks above, what percentage of the overall goal objective is complete?
        Consider if the tasks successfully fulfilled the requirements described in the goal.
        
        OUTPUT: 
        Return ONLY a JSON object with the "percentage" (float 0.0-100.0) and "reasoning" (string).
        """

        # 3. Request LLM evaluation
        try:
            router = ModelRouter(settings)
            res = await router.get_response(prompt, complexity="MEDIUM")
            import json
            import re
            
            # Extract JSON from potential Markdown formatting
            json_match = re.search(r'\{.*\}', res, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                percentage = float(data.get("percentage", goal.metric_current))
                
                # 4. Persist updated progress
                await self.update_goal(goal_id, progress=percentage)
                logger.info(f"🎯 [GOAL_EVAL]: Updated progress for '{goal.title}' to {percentage}%")
                return percentage
        except Exception as e:
            logger.error(f"[GOAL_EVAL]: LLM evaluation failed: {e}", exc_info=True)
            return goal.metric_current

        return goal.metric_current

# Global Singleton
goal_engine = GoalsEngine()
