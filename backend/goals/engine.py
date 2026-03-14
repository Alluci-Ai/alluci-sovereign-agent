
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import GoalRecord

logger = logging.getLogger("GoalsEngine")

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
            return goal.id

    async def update_goal(self, goal_id: int, status: str = None, progress: float = None, description: str = None):
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
            return session.exec(stmt).all()

    async def evaluate_progress(self, goal_id: int):
        """
        Skeleton for autonomous goal fulfillment evaluation.
        In the future, this will use the Router to analyze TaskRecord results 
        related to this goal and update 'metric_current'.
        """
        goal = await self.get_goal(goal_id)
        if not goal: return None
        
        logger.info(f"🎯 [GOAL_EVAL]: Evaluating progress for '{goal.title}'")
        # Placeholder for actual LLM-based evaluation
        return goal.metric_current

# Global Singleton
goal_engine = GoalsEngine()
