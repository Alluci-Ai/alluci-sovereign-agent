
import os
import re
import fcntl
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

    async def get_tasks(self, status: str = "all", priority: Optional[str] = None, timeline: Optional[str] = None) -> List[TaskItem]:
        return await asyncio.to_thread(self._get_tasks_sync, status, priority, timeline)

    def _get_tasks_sync(self, status: str = "all", priority: Optional[str] = None, timeline: Optional[str] = None) -> List[TaskItem]:
        if not os.path.exists(self.filepath):
            return []
            
        tasks = []
        with open(self.filepath, 'r') as f:
            try:
                # Shared lock for reading
                fcntl.flock(f, fcntl.LOCK_SH)
                lines = f.readlines()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

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
                    if not task_date or task_date > today: continue
                elif timeline == "WEEK":
                    next_week = today + timedelta(days=7)
                    if not task_date or task_date > next_week: continue
                elif timeline == "OVERDUE":
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
            p_score = priority_weights.get(t.priority, 1)
            d_score = t.due_date if t.due_date else "9999-12-31" 
            return (-p_score, d_score, t.index)

        filtered_tasks.sort(key=sort_key)
        return filtered_tasks

    async def add_task(self, task: TaskUpdate) -> TaskItem:
        return await asyncio.to_thread(self._add_task_sync, task)

    def _add_task_sync(self, task: TaskUpdate) -> TaskItem:
        line_str = self._construct_line(task)
        
        with open(self.filepath, 'a+') as f:
            try:
                # Exclusive lock for writing
                fcntl.flock(f, fcntl.LOCK_EX)
                # Ensure we start on a new line
                f.seek(0, os.SEEK_END)
                if f.tell() > 0:
                    f.seek(f.tell() - 1)
                    if f.read(1) != '\n':
                        f.write('\n')
                f.write(f"{line_str}\n")
                f.flush()
                # Determine index (it's the last line now)
                f.seek(0)
                lines = f.readlines()
                return self._parse_line(len(lines)-1, lines[-1])
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    async def update_task(self, index: int, update: TaskUpdate) -> Optional[TaskItem]:
        return await asyncio.to_thread(self._update_task_sync, index, update)

    def _update_task_sync(self, index: int, update: TaskUpdate) -> Optional[TaskItem]:
        if not os.path.exists(self.filepath):
            return None
            
        with open(self.filepath, 'r+') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                lines = f.readlines()
                
                if index < 0 or index >= len(lines):
                    return None
                    
                if not lines[index].strip().startswith("- ["):
                    raise ValueError("Target line is not a task")
                    
                new_line = self._construct_line(update)
                lines[index] = new_line + "\n"
                
                f.seek(0)
                f.truncate()
                f.writelines(lines)
                f.flush()
                return self._parse_line(index, new_line)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    async def delete_task(self, index: int) -> bool:
        return await asyncio.to_thread(self._delete_task_sync, index)

    def _delete_task_sync(self, index: int) -> bool:
        if not os.path.exists(self.filepath):
            return False
            
        with open(self.filepath, 'r+') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                lines = f.readlines()
                
                if index < 0 or index >= len(lines):
                    return False
                    
                del lines[index]
                
                f.seek(0)
                f.truncate()
                f.writelines(lines)
                f.flush()
                return True
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
