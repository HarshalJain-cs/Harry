"""
JARVIS Workflow System - Reusable task pipelines.

Define and execute multi-step workflows with templates.
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime


@dataclass
class WorkflowStep:
    """A step in a workflow."""
    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # Python expression
    on_error: str = "stop"  # stop, skip, retry
    max_retries: int = 1
    
    # Runtime state
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """A reusable workflow template."""
    name: str
    description: str
    steps: List[WorkflowStep]
    variables: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    # Runtime state
    status: str = "pending"  # pending, running, completed, failed
    current_step: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class WorkflowEngine:
    """
    Execute and manage workflows.
    
    Features:
    - Workflow templates
    - Variable substitution
    - Conditional execution
    - Error handling
    - Persistence
    """
    
    def __init__(
        self,
        storage_path: str = "./storage/workflows",
    ):
        """
        Initialize workflow engine.
        
        Args:
            storage_path: Directory to store workflows
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.workflows: Dict[str, Workflow] = {}
        self.tools = None
        
        self._load_workflows()
    
    def _get_tools(self):
        """Lazy load tools."""
        if self.tools is None:
            from tools.registry import get_registry
            self.tools = get_registry()
        return self.tools
    
    def _load_workflows(self):
        """Load saved workflows."""
        for filepath in self.storage_path.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                steps = [WorkflowStep(**s) for s in data.pop("steps", [])]
                workflow = Workflow(**data, steps=steps)
                self.workflows[workflow.name] = workflow
            except Exception:
                pass
    
    def _save_workflow(self, workflow: Workflow):
        """Save workflow to disk."""
        filepath = self.storage_path / f"{workflow.name}.json"
        
        data = {
            "name": workflow.name,
            "description": workflow.description,
            "steps": [asdict(s) for s in workflow.steps],
            "variables": workflow.variables,
            "version": workflow.version,
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict],
        variables: Dict = None,
    ) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Unique workflow name
            description: What the workflow does
            steps: List of step definitions
            variables: Default variables
            
        Returns:
            Created Workflow
        """
        workflow_steps = [
            WorkflowStep(
                name=s.get("name", f"step_{i}"),
                action=s["action"],
                params=s.get("params", {}),
                condition=s.get("condition"),
                on_error=s.get("on_error", "stop"),
                max_retries=s.get("max_retries", 1),
            )
            for i, s in enumerate(steps)
        ]
        
        workflow = Workflow(
            name=name,
            description=description,
            steps=workflow_steps,
            variables=variables or {},
        )
        
        self.workflows[name] = workflow
        self._save_workflow(workflow)
        
        return workflow
    
    def run_workflow(
        self,
        name: str,
        variables: Dict = None,
        on_step: Callable[[WorkflowStep], None] = None,
    ) -> Workflow:
        """
        Execute a workflow.
        
        Args:
            name: Workflow name
            variables: Variables to override defaults
            on_step: Callback after each step
            
        Returns:
            Workflow with results
        """
        if name not in self.workflows:
            raise ValueError(f"Workflow not found: {name}")
        
        # Clone workflow for execution
        template = self.workflows[name]
        workflow = Workflow(
            name=template.name,
            description=template.description,
            steps=[WorkflowStep(**asdict(s)) for s in template.steps],
            variables={**template.variables, **(variables or {})},
            version=template.version,
        )
        
        workflow.status = "running"
        workflow.start_time = datetime.now()
        
        tools = self._get_tools()
        
        for i, step in enumerate(workflow.steps):
            workflow.current_step = i
            
            # Check condition
            if step.condition:
                try:
                    # Evaluate condition with variables in scope
                    if not eval(step.condition, {"__builtins__": {}}, workflow.variables):
                        step.status = "skipped"
                        continue
                except:
                    step.status = "skipped"
                    continue
            
            # Substitute variables in params
            params = self._substitute_variables(step.params, workflow.variables)
            
            # Execute with retry
            retries = 0
            while retries <= step.max_retries:
                try:
                    step.status = "running"
                    result = tools.execute(step.action, params)
                    
                    if result.success:
                        step.status = "completed"
                        step.result = result.output
                        
                        # Store result as variable
                        workflow.variables[f"{step.name}_result"] = result.output
                        break
                    else:
                        step.error = result.error
                        retries += 1
                
                except Exception as e:
                    step.error = str(e)
                    retries += 1
            
            if step.status != "completed":
                step.status = "failed"
                
                if step.on_error == "stop":
                    workflow.status = "failed"
                    break
                elif step.on_error == "skip":
                    continue
            
            if on_step:
                on_step(step)
        
        if workflow.status == "running":
            workflow.status = "completed"
        
        workflow.end_time = datetime.now()
        
        return workflow
    
    def _substitute_variables(
        self,
        params: Dict,
        variables: Dict,
    ) -> Dict:
        """Replace {{var}} placeholders with values."""
        result = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                for var_name, var_value in variables.items():
                    value = value.replace(f"{{{{{var_name}}}}}", str(var_value))
            result[key] = value
        
        return result
    
    def list_workflows(self) -> List[str]:
        """List all workflows."""
        return list(self.workflows.keys())
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        if name in self.workflows:
            del self.workflows[name]
            
            filepath = self.storage_path / f"{name}.json"
            if filepath.exists():
                filepath.unlink()
            
            return True
        return False


# Pre-built workflow templates
WORKFLOW_TEMPLATES = {
    "morning_standup": {
        "description": "Morning standup preparation",
        "steps": [
            {"name": "check_email", "action": "check_email", "params": {"limit": 5}},
            {"name": "git_status", "action": "git_status", "params": {}},
            {"name": "list_reminders", "action": "list_reminders", "params": {}},
        ],
    },
    "code_review": {
        "description": "Prepare code for review",
        "steps": [
            {"name": "git_diff", "action": "git_diff", "params": {}},
            {"name": "analyze", "action": "analyze_code", "params": {"file_path": "{{file}}"}},
        ],
    },
    "research_topic": {
        "description": "Research a topic",
        "steps": [
            {"name": "search", "action": "web_search", "params": {"query": "{{topic}}"}},
            {"name": "note", "action": "create_note", "params": {"content": "Research: {{topic}}"}},
        ],
    },
}


from tools.registry import tool, ToolResult


@tool(
    name="run_workflow",
    description="Run a saved workflow",
    category="automation",
    examples=["run morning standup workflow", "execute code review workflow"],
)
def run_workflow(name: str, variables: Dict = None) -> ToolResult:
    """Run a workflow."""
    try:
        engine = WorkflowEngine()
        workflow = engine.run_workflow(name, variables)
        
        completed = sum(1 for s in workflow.steps if s.status == "completed")
        
        return ToolResult(
            success=workflow.status == "completed",
            output={
                "name": workflow.name,
                "status": workflow.status,
                "completed_steps": f"{completed}/{len(workflow.steps)}",
                "duration": str(workflow.end_time - workflow.start_time) if workflow.end_time else None,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="list_workflows",
    description="List available workflows",
    category="automation",
)
def list_workflows() -> ToolResult:
    """List workflows."""
    try:
        engine = WorkflowEngine()
        workflows = []
        
        for name in engine.list_workflows():
            wf = engine.get_workflow(name)
            workflows.append({
                "name": name,
                "description": wf.description,
                "steps": len(wf.steps),
            })
        
        return ToolResult(success=True, output=workflows)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="create_workflow",
    description="Create a new workflow from steps",
    category="automation",
)
def create_workflow(name: str, description: str, steps: List[Dict]) -> ToolResult:
    """Create workflow."""
    try:
        engine = WorkflowEngine()
        workflow = engine.create_workflow(name, description, steps)
        
        return ToolResult(
            success=True,
            output=f"Workflow '{name}' created with {len(workflow.steps)} steps",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Workflow Engine...")
    
    engine = WorkflowEngine(storage_path="./test_workflows")
    
    # Create a simple workflow
    workflow = engine.create_workflow(
        name="test_workflow",
        description="A test workflow",
        steps=[
            {"name": "time", "action": "get_time", "params": {}},
            {"name": "date", "action": "get_date", "params": {}},
        ],
    )
    
    print(f"\nCreated workflow: {workflow.name}")
    print(f"Steps: {len(workflow.steps)}")
    
    # Run workflow
    print("\nRunning workflow...")
    result = engine.run_workflow("test_workflow")
    
    print(f"\nStatus: {result.status}")
    for step in result.steps:
        print(f"  {step.name}: {step.status} - {step.result}")
    
    # Cleanup
    import shutil
    if os.path.exists("./test_workflows"):
        shutil.rmtree("./test_workflows")
    
    print("\nWorkflow test complete!")
