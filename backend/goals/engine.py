
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"

class GoalsEngine:
    """
    ZeroClaw Goals Engine.
    Manages long-running objectives and hierarchical task breakdown.
    """
    def __init__(self):
        self.goals: Dict[str, Dict[str, Any]] = {}

    def create_goal(self, title: str, description: str, priority: int = 5) -> str:
        goal_id = str(uuid.uuid4())
        self.goals[goal_id] = {
            "id": goal_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": GoalStatus.PENDING.value,
            "progress": 0.0,
            "sub_goals": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return goal_id

    def update_goal(self, goal_id: str, status: GoalStatus = None, progress: float = None):
        if goal_id in self.goals:
            if status: self.goals[goal_id]["status"] = status.value
            if progress is not None: self.goals[goal_id]["progress"] = progress
            self.goals[goal_id]["updated_at"] = datetime.now().isoformat()

    def get_active_goals(self) -> List[Dict[str, Any]]:
        return [g for g in self.goals.values() if g["status"] in [GoalStatus.PENDING.value, GoalStatus.ACTIVE.value]]

goal_engine = GoalsEngine()
