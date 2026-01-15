"""
JARVIS Executor Agent - Plan execution with error handling.

Executes plans created by the Planner Agent with retry logic.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time

from .base import Agent, AgentResult, AgentStep, AgentState
from .planner import Plan, PlanStep


@dataclass
class ExecutionReport:
    """Report of plan execution."""
    plan_goal: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    results: Dict[int, Any]
    total_time: float


class ExecutorAgent(Agent):
    """
    Agent that executes plans step-by-step.
    
    Features:
    - Dependency-aware execution
    - Retry on failure
    - Error recovery
    - Progress tracking
    """
    
    SYSTEM_PROMPT = """You are an execution agent that carries out planned tasks.

When a step fails, you can:
1. Retry with different parameters
2. Skip and continue
3. Report failure

Always try to complete as much of the plan as possible.
Respond with JSON for decisions:
{"decision": "retry|skip|fail", "reasoning": "why", "new_params": {}}"""
    
    def __init__(
        self,
        name: str = "executor",
        max_retries: int = 2,
        **kwargs,
    ):
        super().__init__(name, **kwargs)
        self.max_retries = max_retries
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def execute_plan(self, plan: Plan) -> ExecutionReport:
        """
        Execute a plan step by step.
        
        Args:
            plan: Plan to execute
            
        Returns:
            ExecutionReport with results
        """
        self._init_components()
        
        start_time = time.time()
        results = {}
        completed = 0
        failed = 0
        
        # Track completed step IDs
        completed_ids = set()
        
        self.log(f"Executing plan: {plan.goal}")
        self.log(f"Total steps: {len(plan.steps)}")
        
        for step in plan.steps:
            # Check dependencies
            missing_deps = [d for d in step.dependencies if d not in completed_ids]
            if missing_deps:
                self.log(f"Skipping step {step.id}: missing dependencies {missing_deps}")
                step.status = "skipped"
                continue
            
            # Execute step
            self.log(f"Executing step {step.id}: {step.description}")
            step.status = "running"
            
            success = False
            retries = 0
            current_params = step.params.copy()
            
            while not success and retries <= self.max_retries:
                try:
                    result = self.tools.execute(step.action, current_params)
                    
                    if result.success:
                        success = True
                        results[step.id] = result.output
                        step.status = "completed"
                        completed_ids.add(step.id)
                        completed += 1
                        self.log(f"Step {step.id} completed")
                    else:
                        retries += 1
                        self.log(f"Step {step.id} failed: {result.error}")
                        
                        # Try to recover
                        if retries <= self.max_retries:
                            recovery = self._handle_failure(step, result.error)
                            if recovery.get("decision") == "retry":
                                current_params = recovery.get("new_params", current_params)
                            elif recovery.get("decision") == "skip":
                                break
                
                except Exception as e:
                    retries += 1
                    self.log(f"Step {step.id} exception: {e}")
            
            if not success:
                step.status = "failed"
                failed += 1
                results[step.id] = {"error": "Max retries exceeded"}
        
        return ExecutionReport(
            plan_goal=plan.goal,
            total_steps=len(plan.steps),
            completed_steps=completed,
            failed_steps=failed,
            results=results,
            total_time=time.time() - start_time,
        )
    
    def _handle_failure(self, step: PlanStep, error: str) -> Dict:
        """Decide how to handle a step failure."""
        try:
            prompt = f"""Step failed:
Action: {step.action}
Params: {step.params}
Error: {error}

Should I retry, skip, or fail? If retry, suggest new params."""
            
            response = self.think(prompt)
            
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"decision": "skip", "reasoning": "Could not determine recovery"}
    
    def run(self, task: str, context: Dict = None) -> AgentResult:
        """
        Run executor on a task (creates plan first if needed).
        
        Args:
            task: Goal or plan
            context: May contain 'plan' key with Plan object
        """
        start_time = time.time()
        
        # Get or create plan
        if context and "plan" in context:
            plan = context["plan"]
        else:
            from .planner import PlannerAgent
            planner = PlannerAgent(name="auto_planner", llm_model=self.llm_model)
            plan_result = planner.run(task)
            plan = plan_result.output
        
        # Execute plan
        report = self.execute_plan(plan)
        
        success = report.failed_steps == 0
        
        return AgentResult(
            success=success,
            output=report,
            steps=self.steps,
            total_time=time.time() - start_time,
            error=None if success else f"{report.failed_steps} steps failed",
        )


if __name__ == "__main__":
    print("Testing Executor Agent...")
    
    from .planner import Plan, PlanStep
    
    # Create a simple test plan
    plan = Plan(
        goal="Test execution",
        steps=[
            PlanStep(
                id=1,
                description="Get current time",
                action="get_time",
                params={},
            ),
            PlanStep(
                id=2,
                description="Get system info",
                action="get_system_info",
                params={},
                dependencies=[1],
            ),
        ],
    )
    
    executor = ExecutorAgent(name="executor", verbose=True)
    
    print(f"\nExecuting plan: {plan.goal}")
    print(f"Steps: {len(plan.steps)}")
    
    try:
        report = executor.execute_plan(plan)
        
        print(f"\n--- Execution Report ---")
        print(f"Goal: {report.plan_goal}")
        print(f"Completed: {report.completed_steps}/{report.total_steps}")
        print(f"Failed: {report.failed_steps}")
        print(f"Time: {report.total_time:.2f}s")
        
        for step_id, result in report.results.items():
            print(f"\nStep {step_id}: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nExecutor test complete!")
