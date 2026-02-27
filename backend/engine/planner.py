
import json
import logging
from typing import List, Dict, Any, Set
from ..models import DAGTask, TaskStatus
from ..inference.router import ModelRouter

logger = logging.getLogger("Engine.Planner")

class Planner:
    """
    Responsible for converting natural language objectives into 
    executable Directed Acyclic Graphs (DAGs).
    """
    def __init__(self, router: ModelRouter):
        self.router = router

    async def generate_plan(self, objective: str, context: str = "") -> Dict[str, DAGTask]:
        """
        Generates a valid DAG from the objective, influenced by the Soul's context and skills.
        """
        # Augment objective with the Soul's context
        augmented_prompt = f"""
        {context}
        
        OBJECTIVE: "{objective}"
        
        Based on the Identity, Reasoning Style, and Available Skills above, create a plan.
        """
        
        raw_plan = await self.router.get_structured_plan(augmented_prompt)
        steps = raw_plan.get("steps", [])
        
        if not steps:
            raise ValueError("Planner output contained no steps.")

        tasks = self._build_and_validate_dag(steps, objective)
        logger.info(f"Generated Plan with {len(tasks)} steps for objective: '{objective[:50]}...'")
        return tasks

    async def refine_plan(self, objective: str, original_plan: List[Dict], results: str, feedback: str, failed_tasks: List[str]) -> Dict[str, DAGTask]:
        """
        Self-Correction: Asks the LLM to fix the plan based on failure context.
        """
        logger.info("Initiating Plan Refinement Protocol...")
        raw_plan = await self.router.refine_plan(objective, original_plan, results, feedback, failed_tasks)
        steps = raw_plan.get("steps", [])
        
        if not steps:
            raise ValueError("Refinement output contained no steps.")

        return self._build_and_validate_dag(steps, objective)

    def _build_and_validate_dag(self, steps: List[Dict[str, Any]], objective: str) -> Dict[str, DAGTask]:
        """
        Constructs DAGTask objects and enforces acyclic dependency structure.
        """
        tasks: Dict[str, DAGTask] = {}
        
        # 1. Instantiation
        for step in steps:
            t_id = step.get('id')
            if not t_id: continue
            
            tasks[t_id] = DAGTask(
                id=t_id,
                action=step.get('tool', 'unknown'),
                args={
                    "description": step.get('description', ''), 
                    "context": objective
                },
                dependencies=step.get('dependencies', []),
                status=TaskStatus.PENDING
            )

        # 2. Dependency Validation
        for t_id, task in tasks.items():
            for dep in task.dependencies:
                if dep == t_id:
                    raise ValueError(f"Self-dependency detected in task '{t_id}'")
                if dep not in tasks:
                    # Auto-prune phantom dependencies or fail? We fail for safety.
                    raise ValueError(f"Task '{t_id}' depends on non-existent '{dep}'")

        # 3. Cycle Detection
        self._detect_cycles(tasks)
        
        return tasks

    def _detect_cycles(self, tasks: Dict[str, DAGTask]):
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str):
            visited.add(node)
            stack.add(node)
            
            for neighbor in tasks[node].dependencies:
                if neighbor not in visited:
                    if dfs(neighbor): return True
                elif neighbor in stack:
                    return True
            
            stack.remove(node)
            return False

        for node in tasks:
            if node not in visited:
                if dfs(node):
                    raise ValueError("Cycle detected in Execution Plan.")
