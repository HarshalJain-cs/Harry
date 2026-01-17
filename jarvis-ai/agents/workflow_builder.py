"""
JARVIS Workflow Builder - Visual workflow automation
====================================================

Define, validate, and execute complex workflows with error recovery.
"""

import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StepStatus(Enum):
    """Workflow step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ErrorStrategy(Enum):
    """Error handling strategies."""
    STOP = "stop"  # Stop workflow on error
    RETRY = "retry"  # Retry the step
    SKIP = "skip"  # Skip and continue
    FALLBACK = "fallback"  # Execute fallback action


@dataclass
class WorkflowStep:
    """Single workflow step definition."""
    id: str
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Flow control
    on_success: Optional[str] = None  # Next step on success (None = next in sequence)
    on_failure: Optional[str] = None  # Next step on failure (None = use error_strategy)
    condition: Optional[str] = None  # Optional condition expression
    
    # Error handling
    error_strategy: str = "stop"
    max_retries: int = 3
    retry_delay: float = 1.0
    fallback_action: Optional[str] = None
    
    # Timeout
    timeout: Optional[float] = None  # Seconds
    
    # Status (runtime)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    steps_executed: int
    steps_failed: int
    duration: float
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class Workflow:
    """Complete workflow definition."""
    id: str
    name: str
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    
    # Global settings
    stop_on_error: bool = True
    max_steps: int = 100  # Safety limit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "action": s.action,
                    "params": s.params,
                    "on_success": s.on_success,
                    "on_failure": s.on_failure,
                    "condition": s.condition,
                    "error_strategy": s.error_strategy,
                    "max_retries": s.max_retries,
                    "retry_delay": s.retry_delay,
                    "fallback_action": s.fallback_action,
                    "timeout": s.timeout
                }
                for s in self.steps
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stop_on_error": self.stop_on_error,
            "max_steps": self.max_steps
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Create from dictionary."""
        steps = [
            WorkflowStep(
                id=s.get("id", str(uuid.uuid4())[:8]),
                name=s.get("name", s.get("action", "step")),
                action=s["action"],
                params=s.get("params", {}),
                on_success=s.get("on_success"),
                on_failure=s.get("on_failure"),
                condition=s.get("condition"),
                error_strategy=s.get("error_strategy", "stop"),
                max_retries=s.get("max_retries", 3),
                retry_delay=s.get("retry_delay", 1.0),
                fallback_action=s.get("fallback_action"),
                timeout=s.get("timeout")
            )
            for s in data.get("steps", [])
        ]
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unnamed Workflow"),
            description=data.get("description", ""),
            steps=steps,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            stop_on_error=data.get("stop_on_error", True),
            max_steps=data.get("max_steps", 100)
        )


class WorkflowBuilder:
    """
    Builder for creating and managing workflows.
    
    Usage:
        builder = WorkflowBuilder()
        wf = builder.create("my_workflow")
        builder.add_step(wf, "open_browser", "open_app", {"app": "chrome"})
        builder.add_step(wf, "search", "web_search", {"query": "test"})
        builder.save(wf)
    """
    
    def __init__(self, storage_path: str = "./data/workflows"):
        """
        Initialize workflow builder.
        
        Args:
            storage_path: Directory for workflow storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Action registry
        self._actions: Dict[str, Callable] = {}
    
    def register_action(self, name: str, handler: Callable):
        """Register an action handler."""
        self._actions[name] = handler
    
    def create(self, name: str, description: str = "") -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            
        Returns:
            New workflow
        """
        return Workflow(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            steps=[],
            created_at=datetime.now().isoformat()
        )
    
    def add_step(
        self,
        workflow: Workflow,
        name: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> WorkflowStep:
        """
        Add a step to workflow.
        
        Args:
            workflow: Target workflow
            name: Step name
            action: Action to execute
            params: Action parameters
            **kwargs: Additional step options
            
        Returns:
            Created step
        """
        step = WorkflowStep(
            id=str(uuid.uuid4())[:8],
            name=name,
            action=action,
            params=params or {},
            on_success=kwargs.get("on_success"),
            on_failure=kwargs.get("on_failure"),
            condition=kwargs.get("condition"),
            error_strategy=kwargs.get("error_strategy", "stop"),
            max_retries=kwargs.get("max_retries", 3),
            timeout=kwargs.get("timeout")
        )
        
        workflow.steps.append(step)
        return step
    
    def remove_step(self, workflow: Workflow, step_id: str) -> bool:
        """Remove a step from workflow."""
        for i, step in enumerate(workflow.steps):
            if step.id == step_id:
                workflow.steps.pop(i)
                return True
        return False
    
    def connect(
        self,
        workflow: Workflow,
        from_step: str,
        to_step: str,
        condition: str = "success"
    ):
        """
        Connect two steps.
        
        Args:
            workflow: Target workflow
            from_step: Source step ID
            to_step: Target step ID
            condition: "success" or "failure"
        """
        for step in workflow.steps:
            if step.id == from_step or step.name == from_step:
                if condition == "success":
                    step.on_success = to_step
                else:
                    step.on_failure = to_step
                break
    
    def validate(self, workflow: Workflow) -> List[str]:
        """
        Validate workflow.
        
        Args:
            workflow: Workflow to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not workflow.name:
            errors.append("Workflow name is required")
        
        if not workflow.steps:
            errors.append("Workflow has no steps")
        
        step_ids = set()
        for step in workflow.steps:
            if step.id in step_ids:
                errors.append(f"Duplicate step ID: {step.id}")
            step_ids.add(step.id)
            
            if not step.action:
                errors.append(f"Step '{step.name}' has no action")
            
            # Check references
            if step.on_success and step.on_success not in step_ids:
                # Check if it's a step name
                found = any(s.name == step.on_success for s in workflow.steps)
                if not found:
                    errors.append(f"Step '{step.name}' references unknown step: {step.on_success}")
            
            if step.on_failure and step.on_failure not in step_ids:
                found = any(s.name == step.on_failure for s in workflow.steps)
                if not found:
                    errors.append(f"Step '{step.name}' references unknown step: {step.on_failure}")
        
        return errors
    
    def save(self, workflow: Workflow) -> bool:
        """
        Save workflow to file.
        
        Args:
            workflow: Workflow to save
            
        Returns:
            True if saved
        """
        workflow.updated_at = datetime.now().isoformat()
        filepath = self.storage_path / f"{workflow.id}.json"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(workflow.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving workflow: {e}")
            return False
    
    def load(self, workflow_id: str) -> Optional[Workflow]:
        """
        Load workflow from file.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Loaded workflow or None
        """
        filepath = self.storage_path / f"{workflow_id}.json"
        
        if not filepath.exists():
            # Try by name
            for f in self.storage_path.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                    if data.get("name") == workflow_id:
                        return Workflow.from_dict(data)
                except Exception:
                    pass
            return None
        
        try:
            with open(filepath) as f:
                data = json.load(f)
            return Workflow.from_dict(data)
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return None
    
    def list_workflows(self) -> List[Dict[str, str]]:
        """List all saved workflows."""
        workflows = []
        
        for f in self.storage_path.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                workflows.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "description": data.get("description", ""),
                    "steps": len(data.get("steps", []))
                })
            except Exception:
                pass
        
        return workflows
    
    def delete(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        filepath = self.storage_path / f"{workflow_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False


class WorkflowExecutor:
    """
    Executes workflows with error handling.
    
    Usage:
        executor = WorkflowExecutor(tool_registry)
        result = executor.execute(workflow)
    """
    
    def __init__(self, tool_registry=None):
        """
        Initialize executor.
        
        Args:
            tool_registry: Tool registry for executing actions
        """
        self._registry = tool_registry
        self._running = False
        self._stop_requested = False
    
    def set_registry(self, registry):
        """Set tool registry."""
        self._registry = registry
    
    def execute(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            context: Initial context variables
            
        Returns:
            Execution result
        """
        import time
        
        if self._running:
            return WorkflowResult(
                success=False,
                steps_executed=0,
                steps_failed=0,
                duration=0,
                errors=["Another workflow is running"]
            )
        
        self._running = True
        self._stop_requested = False
        
        start_time = time.time()
        context = context or {}
        results = {}
        errors = []
        steps_executed = 0
        steps_failed = 0
        
        # Build step index
        step_index = {s.id: s for s in workflow.steps}
        step_index.update({s.name: s for s in workflow.steps})
        
        # Start with first step
        current_step = workflow.steps[0] if workflow.steps else None
        
        try:
            while current_step and steps_executed < workflow.max_steps:
                if self._stop_requested:
                    errors.append("Workflow stopped by user")
                    break
                
                steps_executed += 1
                current_step.status = StepStatus.RUNNING.value
                
                # Check condition
                if current_step.condition:
                    if not self._evaluate_condition(current_step.condition, context):
                        current_step.status = StepStatus.SKIPPED.value
                        current_step = self._get_next_step(current_step, step_index, True)
                        continue
                
                # Execute step
                success, result, error = self._execute_step(current_step, context)
                
                if success:
                    current_step.status = StepStatus.SUCCESS.value
                    current_step.result = result
                    results[current_step.id] = result
                    context[current_step.name] = result
                    current_step = self._get_next_step(current_step, step_index, True)
                else:
                    steps_failed += 1
                    current_step.status = StepStatus.FAILED.value
                    current_step.error = error
                    errors.append(f"{current_step.name}: {error}")
                    
                    if workflow.stop_on_error and current_step.error_strategy == "stop":
                        break
                    
                    current_step = self._get_next_step(current_step, step_index, False)
        
        finally:
            self._running = False
        
        duration = time.time() - start_time
        
        return WorkflowResult(
            success=steps_failed == 0,
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            duration=duration,
            results=results,
            errors=errors
        )
    
    def stop(self):
        """Request workflow stop."""
        self._stop_requested = True
    
    @property
    def is_running(self) -> bool:
        """Check if workflow is running."""
        return self._running
    
    def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> tuple:
        """Execute a single step with retry logic."""
        import time
        
        retries = 0
        last_error = None
        
        while retries <= step.max_retries:
            try:
                # Substitute context variables in params
                params = self._substitute_params(step.params, context)
                
                # Execute action
                if self._registry:
                    result = self._registry.execute(step.action, params)
                    if result.success:
                        return True, result.output, None
                    else:
                        raise Exception(result.error or "Action failed")
                else:
                    # No registry, just return params
                    return True, params, None
                    
            except Exception as e:
                last_error = str(e)
                retries += 1
                
                if retries <= step.max_retries and step.error_strategy == "retry":
                    step.status = StepStatus.RETRYING.value
                    time.sleep(step.retry_delay)
                else:
                    break
        
        # Handle fallback
        if step.fallback_action and step.error_strategy == "fallback":
            try:
                if self._registry:
                    result = self._registry.execute(step.fallback_action, {})
                    return True, result.output, None
            except Exception:
                pass
        
        return False, None, last_error
    
    def _substitute_params(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Substitute context variables in parameters."""
        result = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference
                var_name = value[1:]
                result[key] = context.get(var_name, value)
            elif isinstance(value, dict):
                result[key] = self._substitute_params(value, context)
            else:
                result[key] = value
        
        return result
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression."""
        try:
            # Simple variable check
            if condition.startswith("$"):
                var_name = condition[1:]
                return bool(context.get(var_name))
            
            # Expression evaluation (limited for safety)
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return True
    
    def _get_next_step(
        self,
        current: WorkflowStep,
        step_index: Dict[str, WorkflowStep],
        success: bool
    ) -> Optional[WorkflowStep]:
        """Get next step based on success/failure."""
        next_ref = current.on_success if success else current.on_failure
        
        if next_ref:
            return step_index.get(next_ref)
        
        # Default: next in sequence
        if success:
            # Find current position and return next
            for i, step in enumerate(list(step_index.values())):
                if step.id == current.id:
                    steps_list = list(step_index.values())
                    if i + 1 < len(steps_list):
                        return steps_list[i + 1]
        
        return None


# Singleton instances
_builder: Optional[WorkflowBuilder] = None
_executor: Optional[WorkflowExecutor] = None


def get_workflow_builder() -> WorkflowBuilder:
    """Get or create global workflow builder."""
    global _builder
    if _builder is None:
        _builder = WorkflowBuilder()
    return _builder


def get_workflow_executor() -> WorkflowExecutor:
    """Get or create global workflow executor."""
    global _executor
    if _executor is None:
        _executor = WorkflowExecutor()
    return _executor
