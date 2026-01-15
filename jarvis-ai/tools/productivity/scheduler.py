"""
JARVIS Task Scheduler - Automated task scheduling.

Provides cron-like scheduling for recurring tasks.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

from tools.registry import tool, ToolResult


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    name: str
    command: str  # JARVIS command to execute
    schedule: str  # cron expression or interval
    schedule_type: str  # cron, interval, once
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0


class TaskScheduler:
    """
    Schedule and automate JARVIS tasks.
    
    Features:
    - Cron-style scheduling
    - Interval-based scheduling
    - One-time scheduled tasks
    - Task history tracking
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/scheduled_tasks.json",
        on_task: Optional[Callable[[str], Any]] = None,
    ):
        """
        Initialize task scheduler.
        
        Args:
            storage_path: Path to store tasks
            on_task: Callback to execute JARVIS commands
        """
        self.storage_path = storage_path
        self.on_task = on_task
        self.tasks: Dict[str, ScheduledTask] = {}
        
        self.scheduler = None
        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
        
        self._load()
    
    def _load(self):
        """Load scheduled tasks from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    if item.get('last_run'):
                        item['last_run'] = datetime.fromisoformat(item['last_run'])
                    if item.get('next_run'):
                        item['next_run'] = datetime.fromisoformat(item['next_run'])
                    
                    task = ScheduledTask(**item)
                    self.tasks[task.id] = task
            except Exception:
                pass
    
    def _save(self):
        """Save tasks to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for t in self.tasks.values():
            item = asdict(t)
            if t.last_run:
                item['last_run'] = t.last_run.isoformat()
            if t.next_run:
                item['next_run'] = t.next_run.isoformat()
            data.append(item)
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_cron_task(
        self,
        name: str,
        command: str,
        cron_expression: str,
    ) -> ScheduledTask:
        """
        Add a cron-scheduled task.
        
        Args:
            name: Task name
            command: JARVIS command to run
            cron_expression: Cron expression (e.g., "0 9 * * *")
        """
        task_id = f"task_{datetime.now().timestamp()}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            command=command,
            schedule=cron_expression,
            schedule_type="cron",
        )
        
        self.tasks[task_id] = task
        self._save()
        
        # Schedule with APScheduler
        if self.scheduler and SCHEDULER_AVAILABLE:
            self._schedule_task(task)
        
        return task
    
    def add_interval_task(
        self,
        name: str,
        command: str,
        interval_seconds: int,
    ) -> ScheduledTask:
        """Add an interval-scheduled task."""
        task_id = f"task_{datetime.now().timestamp()}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            command=command,
            schedule=str(interval_seconds),
            schedule_type="interval",
        )
        
        self.tasks[task_id] = task
        self._save()
        
        if self.scheduler and SCHEDULER_AVAILABLE:
            self._schedule_task(task)
        
        return task
    
    def add_once_task(
        self,
        name: str,
        command: str,
        run_at: datetime,
    ) -> ScheduledTask:
        """Add a one-time scheduled task."""
        task_id = f"task_{datetime.now().timestamp()}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            command=command,
            schedule=run_at.isoformat(),
            schedule_type="once",
            next_run=run_at,
        )
        
        self.tasks[task_id] = task
        self._save()
        
        if self.scheduler and SCHEDULER_AVAILABLE:
            self._schedule_task(task)
        
        return task
    
    def _schedule_task(self, task: ScheduledTask):
        """Schedule task with APScheduler."""
        if not self.scheduler:
            return
        
        def job_func():
            self._run_task(task.id)
        
        if task.schedule_type == "cron":
            trigger = CronTrigger.from_crontab(task.schedule)
            self.scheduler.add_job(job_func, trigger, id=task.id)
        
        elif task.schedule_type == "interval":
            seconds = int(task.schedule)
            trigger = IntervalTrigger(seconds=seconds)
            self.scheduler.add_job(job_func, trigger, id=task.id)
        
        elif task.schedule_type == "once":
            run_time = datetime.fromisoformat(task.schedule)
            self.scheduler.add_job(job_func, 'date', run_date=run_time, id=task.id)
    
    def _run_task(self, task_id: str):
        """Execute a scheduled task."""
        task = self.tasks.get(task_id)
        if not task or not task.enabled:
            return
        
        task.last_run = datetime.now()
        task.run_count += 1
        self._save()
        
        if self.on_task:
            try:
                self.on_task(task.command)
            except Exception as e:
                print(f"Task {task.name} failed: {e}")
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = True
            self._save()
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = False
            self._save()
            if self.scheduler:
                try:
                    self.scheduler.remove_job(task_id)
                except:
                    pass
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save()
            if self.scheduler:
                try:
                    self.scheduler.remove_job(task_id)
                except:
                    pass
            return True
        return False
    
    def list_tasks(self) -> List[ScheduledTask]:
        """List all tasks."""
        return list(self.tasks.values())
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and not self.scheduler.running:
            # Reschedule all enabled tasks
            for task in self.tasks.values():
                if task.enabled:
                    self._schedule_task(task)
            self.scheduler.start()
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()


# Tool registrations
@tool(
    name="schedule_task",
    description="Schedule a recurring JARVIS task",
    category="productivity",
    examples=["schedule backup every day at 9am", "run report every monday"],
)
def schedule_task(
    name: str,
    command: str,
    schedule_type: str = "interval",
    schedule: str = "3600",  # 1 hour default
) -> ToolResult:
    """Schedule a task."""
    try:
        scheduler = TaskScheduler()
        
        if schedule_type == "cron":
            task = scheduler.add_cron_task(name, command, schedule)
        elif schedule_type == "interval":
            task = scheduler.add_interval_task(name, command, int(schedule))
        elif schedule_type == "once":
            run_time = datetime.fromisoformat(schedule)
            task = scheduler.add_once_task(name, command, run_time)
        else:
            return ToolResult(success=False, error=f"Unknown schedule type: {schedule_type}")
        
        return ToolResult(
            success=True,
            output={
                "id": task.id,
                "name": task.name,
                "command": task.command,
                "schedule": task.schedule,
                "type": task.schedule_type,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_scheduled_tasks",
    description="List all scheduled tasks",
    category="productivity",
)
def list_scheduled_tasks() -> ToolResult:
    """List scheduled tasks."""
    try:
        scheduler = TaskScheduler()
        tasks = scheduler.list_tasks()
        
        task_list = [
            {
                "id": t.id,
                "name": t.name,
                "command": t.command[:30],
                "schedule": t.schedule,
                "enabled": t.enabled,
                "run_count": t.run_count,
            }
            for t in tasks
        ]
        
        return ToolResult(success=True, output=task_list)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="cancel_scheduled_task",
    description="Cancel a scheduled task",
    category="productivity",
)
def cancel_scheduled_task(task_id: str) -> ToolResult:
    """Cancel a task."""
    try:
        scheduler = TaskScheduler()
        success = scheduler.delete_task(task_id)
        
        if success:
            return ToolResult(success=True, output="Task cancelled")
        else:
            return ToolResult(success=False, error="Task not found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Task Scheduler...")
    
    if not SCHEDULER_AVAILABLE:
        print("APScheduler not available")
    else:
        scheduler = TaskScheduler(storage_path="./test_tasks.json")
        
        # Add interval task
        task = scheduler.add_interval_task(
            "Test Task",
            "get_time",
            60,
        )
        print(f"Created: {task.name}")
        
        # List tasks
        tasks = scheduler.list_tasks()
        print(f"Tasks: {len(tasks)}")
        
        # Delete task
        scheduler.delete_task(task.id)
        print("Deleted task")
        
        # Cleanup
        if os.path.exists("./test_tasks.json"):
            os.remove("./test_tasks.json")
    
    print("\nTests complete!")
