
from ..logging_config import get_logger
from typing import List, Dict, Any, Set
from ..models import DAGTask, TaskStatus
from ..inference.router import ModelRouter

logger = get_logger("Engine.Planner")

class Planner:
    """
    Responsible for converting natural language objectives into 
    executable Directed Acyclic Graphs (DAGs).
    """
    def __init__(self, router: ModelRouter):
        self.router = router

    async def generate_plan(self, objective: str, context: str = "", tools: list | None = None, psi: float = 0.0, agent_id: str = "executive", mode: str = "standard") -> Dict[str, DAGTask]:
        """
        Generates a valid DAG from the objective, influenced by the Soul's context and skills.
        """
        if mode == "research_recon":
            steps = [
                {
                    "id": "task_research_1",
                    "tool": "deep_research_query_expansion",
                    "description": "Reconnaissance Phase 0: Expand queries and gather URLs for deep research",
                    "dependencies": [],
                    "assignee": agent_id
                }
            ]
        elif mode == "research" or mode == "research_execute":
            steps = [
                {
                    "id": "task_research_1",
                    "tool": "deep_research_query_expansion",
                    "description": "Expand queries and gather URLs for deep research",
                    "dependencies": [],
                    "assignee": agent_id
                },
                {
                    "id": "task_research_2",
                    "tool": "deep_research_harvest",
                    "description": "Harvest data from the expanded URLs",
                    "dependencies": ["task_research_1"],
                    "assignee": agent_id
                },
                {
                    "id": "task_research_3",
                    "tool": "deep_research_evaluate",
                    "description": "Evaluate harvested data and synthesize report",
                    "dependencies": ["task_research_2"],
                    "assignee": agent_id
                },
                {
                    "id": "task_research_4",
                    "tool": "deep_research_report_chat",
                    "description": "Condense the final report and send to chat UI",
                    "dependencies": ["task_research_3"],
                    "assignee": agent_id
                }
            ]
        else:
            # Augment objective with the Soul's context and affective state
            prompt_with_psi = f"AFFECTIVE TENSION (psi): {psi:.2f}\n\nOBJECTIVE: \"{objective}\"\n\nBased on the Identity and current Affective Tension, create a plan."
            
            raw_plan = await self.router.get_structured_plan(prompt_with_psi, system_instruction=context, tools=tools, agent_id=agent_id)
            steps = raw_plan.get("steps", [])
            
            if not steps:
                raise ValueError("Planner output contained no steps.")

        tasks = self._build_and_validate_dag(steps, objective)
        logger.info(f"Generated Plan with {len(tasks)} steps for objective: '{objective[:50]}...'")
        return tasks

    async def refine_plan(self, objective: str, original_plan: List[Dict], results: str, feedback: str, failed_tasks: List[str], agent_id: str = "executive", mode: str = "standard") -> Dict[str, DAGTask]:
        """
        Self-Correction: Asks the LLM to fix the plan based on failure context.
        """
        logger.info("Initiating Plan Refinement Protocol...")
        if mode == "research" or "research" in objective.lower():
            logger.info("Preserving research pipeline structure during refinement fallback.")
            return await self.generate_plan(objective, agent_id=agent_id, mode="research")
        try:
            raw_plan = await self.router.refine_plan(objective, original_plan, results, feedback, failed_tasks, agent_id=agent_id)
            steps = raw_plan.get("steps", [])
            if not steps:
                if "research" in objective.lower():
                    return await self.generate_plan(objective, agent_id=agent_id, mode="research")
                raise ValueError("Refinement output contained no steps.")
            return self._build_and_validate_dag(steps, objective)
        except Exception as e:
            logger.warning(f"Refinement error: {e}. Falling back to research pipeline generator.")
            if "research" in objective.lower():
                return await self.generate_plan(objective, agent_id=agent_id, mode="research")
            raise

    def _build_and_validate_dag(self, steps: List[Dict[str, Any]], objective: str) -> Dict[str, DAGTask]:
        """
        Constructs DAGTask objects and enforces acyclic dependency structure.
        """
        tasks: Dict[str, DAGTask] = {}
        
        # 1. Instantiation
        for step in steps:
            t_id = step.get('id')
            if not t_id:
                continue
            
            tasks[t_id] = DAGTask(
                id=t_id,
                action=step.get('tool', 'unknown'),
                description=step.get('description', ''),
                args={
                    **step,
                    "description": step.get('description', ''), 
                    "context": objective
                },
                dependencies=step.get('dependencies', []),
                status=TaskStatus.PENDING,
                assignee=step.get('assignee', 'executive')
            )

        # 2. Dependency Validation
        for t_id, task in tasks.items():
            for dep in task.dependencies:
                if dep == t_id:
                    raise ValueError(f"Self-dependency detected in task '{t_id}'")
                if dep not in tasks:
                    # Auto-prune phantom dependencies or fail? We fail for safety.
                    raise ValueError(f"Task '{t_id}' depends on non-existent '{dep}'")

        # 3. S-CoT Topological Nilpotence & Cycle Detection (Beta_1 = 0)
        self._detect_cycles_and_scot_nilpotence(tasks)
        
        return tasks

    def _detect_cycles_and_scot_nilpotence(self, tasks: Dict[str, DAGTask]):
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str):
            visited.add(node)
            stack.add(node)
            
            for neighbor in tasks[node].dependencies:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in stack:
                    return True
            
            stack.remove(node)
            return False

        for node in tasks:
            if node not in visited:
                if dfs(node):
                    raise ValueError("Cycle detected in Execution Plan (Topological 1-Hole beta_1 > 0).")

        # 4. S-CoT Simplicial Triad Verification across dependency chains
        try:
            from ..topology.j_space_simulator import SimplicialChainOfThought
            scot = SimplicialChainOfThought(strict_mode=True)
            for t_id, task in tasks.items():
                if task.dependencies:
                    dep_descs = [
                        tasks[d].description or (tasks[d].args.get("description") if isinstance(tasks[d].args, dict) else "") or f"Task {tasks[d].id}: {tasks[d].action}"
                        for d in task.dependencies if d in tasks
                    ]
                    dep_desc = " ".join([d for d in dep_descs if d])
                    task_desc = task.description or (task.args.get("description") if isinstance(task.args, dict) else "") or f"Task {task.id}: {task.action}"
                    task_action = getattr(task, "tool", None) or getattr(task, "action", "Direct Action")
                    is_valid, msg = scot.verify_reasoning_step(
                        premise_a=dep_desc or "Initial State",
                        premise_b=task_action or "Direct Action",
                        conclusion=task_desc,
                        is_code_or_tool_dag=True
                    )
                    if not is_valid:
                        logger.warning(f"[S-CoT] Nilpotence notice on task '{t_id}': {msg}")
        except Exception as scot_err:
            logger.debug(f"[S-CoT] Verification skipped: {scot_err}")
