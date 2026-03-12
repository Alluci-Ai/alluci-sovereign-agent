
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

    async def create_goal(self, title: str, description: str, priority: str = "MEDIUM") -> int:
        with Session(self.engine) as session:
            goal = GoalRecord(
                title=title,
                description=description,
                priority=priority,
                status="active"
            )
            session.add(goal)
            session.commit()
            session.refresh(goal)
            return goal.id

    async def update_goal(self, goal_id: int, status: str = None, progress: float = None):
        with Session(self.engine) as session:
            goal = session.get(GoalRecord, goal_id)
            if goal:
                if status: goal.status = status
                if progress is not None: goal.metric_current = progress
                goal.updated_at = datetime.now(timezone.utc)
                session.add(goal)
                session.commit()
                return True
        return False

    async def get_active_goals(self) -> List[GoalRecord]:
        with Session(self.engine) as session:
            stmt = select(GoalRecord).where(GoalRecord.status == "active")
            return session.exec(stmt).all()

    def list_goals(self, status: Optional[str] = None) -> List[GoalRecord]:
        with Session(self.engine) as session:
            stmt = select(GoalRecord)
            if status:
                stmt = stmt.where(GoalRecord.status == status)
            return session.exec(stmt).all()

# Global Singleton
goal_engine = GoalsEngine()
