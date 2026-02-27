
import os
import re
from typing import List, Optional
from datetime import datetime, timedelta
from .models import TaskItem, TaskUpdate, TaskPriority

class TaskManager:
    def __init__(self, filepath: str = "TASKS.md"):
        self.filepath = filepath

    def _parse_line(self, index: int, line: str) -> Optional[TaskItem]:
        line = line.strip()
        if not line.startswith("- ["):
            return None

        # Check completion status
        completed = line.startswith("- [x]")
        
        # Extract Priority
        priority = TaskPriority.MEDIUM
        if "[URGENT]" in line: priority = TaskPriority.URGENT
        elif "[HIGH]" in line: priority = TaskPriority.HIGH
        elif "[LOW]" in line: priority = TaskPriority.LOW
        
        # Extract Due Date
        due_date = None
        due_match = re.search(r'\(due: (\d{4}-\d{2}-\d{2})\)', line)
        if due_match:
            due_date = due_match.group(1)
        
        # Extract Description
        # Remove checkbox
        desc = line[5:].strip()
        # Remove priority tag
        desc = desc.replace(f"[{priority.value}]", "")
        # Remove due date tag
        if due_date:
            desc = desc.replace(f"(due: {due_date})", "")
            
        return TaskItem(
            index=index,
            raw_line=line,
            description=desc.strip(),
            completed=completed,
            priority=priority,
            due_date=due_date
        )

    def _construct_line(self, task: TaskUpdate) -> str:
        box = "- [x]" if task.completed else "- [ ]"
        prio_tag = f"[{task.priority.value}]" if task.priority != TaskPriority.MEDIUM else ""
        date_tag = f"(due: {task.due_date})" if task.due_date else ""
        
        # Clean up double spaces if tags are missing
        line = f"{box} {prio_tag} {task.description} {date_tag}"
        return re.sub(r'\s+', ' ', line).strip()

    def get_tasks(self, status: str = "all", priority: Optional[str] = None, timeline: Optional[str] = None) -> List[TaskItem]:
        if not os.path.exists(self.filepath):
            return []
            
        tasks = []
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                parsed = self._parse_line(i, line)
                if parsed:
                    tasks.append(parsed)

        # --- Filtering Logic ---
        filtered_tasks = []
        today = datetime.now().date()
        
        for t in tasks:
            # 1. Status Filter
            if status == "active" and t.completed:
                continue
            if status == "completed" and not t.completed:
                continue
            
            # 2. Priority Filter
            if priority and priority != "ALL" and t.priority.value != priority:
                continue

            # 3. Timeline Filter
            if timeline and timeline != "ALL":
                task_date = datetime.strptime(t.due_date, "%Y-%m-%d").date() if t.due_date else None
                
                if timeline == "TODAY":
                    # Tasks due today or earlier (if active)
                    if not task_date or task_date > today: continue
                elif timeline == "WEEK":
                    # Tasks due within the next 7 days
                    next_week = today + timedelta(days=7)
                    if not task_date or task_date > next_week: continue
                elif timeline == "OVERDUE":
                    # Active tasks with past due date
                    if t.completed or not task_date or task_date >= today: continue

            filtered_tasks.append(t)

        # --- Sorting Logic ---
        priority_weights = {
            TaskPriority.URGENT: 3,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 1,
            TaskPriority.LOW: 0
        }

        def sort_key(t: TaskItem):
            # Sort by Priority Descending, then Due Date Ascending (earliest first)
            p_score = priority_weights.get(t.priority, 1)
            # Use specific high string for None dates to push them to end in ascending sort
            d_score = t.due_date if t.due_date else "9999-12-31" 
            return (-p_score, d_score, t.index)

        filtered_tasks.sort(key=sort_key)
        
        return filtered_tasks

    def add_task(self, task: TaskUpdate) -> TaskItem:
        line_str = self._construct_line(task)
        
        # Append to file
        with open(self.filepath, 'a') as f:
            # Ensure we start on a new line if file is not empty and doesn't end with newline
            f.write(f"\n{line_str}")
            
        # Return the created item
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
            return self._parse_line(len(lines)-1, lines[-1])

    def update_task(self, index: int, update: TaskUpdate) -> Optional[TaskItem]:
        if not os.path.exists(self.filepath):
            return None
            
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
            
        if index < 0 or index >= len(lines):
            return None
            
        # Verify it's a task line
        if not lines[index].strip().startswith("- ["):
            raise ValueError("Target line is not a task")
            
        new_line = self._construct_line(update)
        lines[index] = new_line + "\n"
        
        with open(self.filepath, 'w') as f:
            f.writelines(lines)
            
        return self._parse_line(index, new_line)

    def delete_task(self, index: int) -> bool:
        if not os.path.exists(self.filepath):
            return False
            
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
            
        if index < 0 or index >= len(lines):
            return False
            
        del lines[index]
        
        with open(self.filepath, 'w') as f:
            f.writelines(lines)
            
        return True
