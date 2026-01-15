"""
JARVIS Planner Agent - Strategic task planning.

Creates structured plans for complex multi-step tasks.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import json

from .base import Agent, AgentResult, AgentState


@dataclass
class PlanStep:
    """A step in a plan."""
    id: int
    description: str
    action: str
    params: Dict[str, Any]
    dependencies: List[int] = field(default_factory=list)
    estimated_time: str = "1 min"
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class Plan:
    """A structured plan for a task."""
    goal: str
    steps: List[PlanStep]
    total_estimated_time: str = ""
    created_at: str = ""


class PlannerAgent(Agent):
    """
    Agent that creates structured plans for complex tasks.
    
    Given a high-level goal, it:
    1. Breaks down into steps
    2. Identifies dependencies
    3. Estimates time
    4. Outputs executable plan
    """
    
    SYSTEM_PROMPT = """You are a planning agent that breaks down complex tasks into clear steps.

Given a goal, create a plan with:
1. Clear, atomic steps
2. Specific tool actions for each step
3. Dependencies between steps
4. Time estimates

Respond with JSON:
{
    "goal": "the goal",
    "steps": [
        {
            "id": 1,
            "description": "What to do",
            "action": "tool_name",
            "params": {"key": "value"},
            "dependencies": [],
            "estimated_time": "1 min"
        }
    ]
}

Available tools include: open_app, web_search, run_python, git_status, 
read_file, write_file, screenshot, etc.

Keep plans practical and achievable."""
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def create_plan(self, goal: str, context: Dict = None) -> Plan:
        """
        Create a plan for achieving a goal.
        
        Args:
            goal: The goal to plan for
            context: Additional context
            
        Returns:
            Plan with steps
        """
        self._init_components()
        
        prompt = f"Create a plan to: {goal}"
        if context:
            prompt += f"\n\nContext: {json.dumps(context)}"
        
        response = self.think(prompt)
        
        try:
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                steps = []
                for step_data in data.get("steps", []):
                    steps.append(PlanStep(
                        id=step_data.get("id", len(steps)),
                        description=step_data.get("description", ""),
                        action=step_data.get("action", ""),
                        params=step_data.get("params", {}),
                        dependencies=step_data.get("dependencies", []),
                        estimated_time=step_data.get("estimated_time", "1 min"),
                    ))
                
                return Plan(
                    goal=goal,
                    steps=steps,
                )
        except Exception as e:
            self.log(f"Plan parsing error: {e}")
        
        # Fallback: simple single-step plan
        return Plan(
            goal=goal,
            steps=[PlanStep(
                id=1,
                description=goal,
                action="web_search",
                params={"query": goal},
            )],
        )
    
    def run(self, task: str, context: Dict = None) -> AgentResult:
        """Run the planner to create a plan."""
        import time
        start_time = time.time()
        
        plan = self.create_plan(task, context)
        
        return AgentResult(
            success=True,
            output=plan,
            steps=[],
            total_time=time.time() - start_time,
        )
    
    def refine_plan(self, plan: Plan, feedback: str) -> Plan:
        """
        Refine a plan based on feedback.
        
        Args:
            plan: Original plan
            feedback: What to change
            
        Returns:
            Refined plan
        """
        self._init_components()
        
        current_steps = [
            f"{s.id}. {s.description} ({s.action})"
            for s in plan.steps
        ]
        
        prompt = f"""Current plan for "{plan.goal}":
{chr(10).join(current_steps)}

Feedback: {feedback}

Create an improved plan based on this feedback."""
        
        return self.create_plan(plan.goal + f" (Refined: {feedback})")


if __name__ == "__main__":
    print("Testing Planner Agent...")
    
    planner = PlannerAgent(name="planner", verbose=True)
    
    # Test planning
    goal = "Research Python testing frameworks and create a summary"
    
    print(f"\nGoal: {goal}")
    print("\nCreating plan...")
    
    try:
        result = planner.run(goal)
        plan = result.output
        
        print(f"\nPlan for: {plan.goal}")
        print(f"Steps: {len(plan.steps)}")
        
        for step in plan.steps:
            deps = f" (after {step.dependencies})" if step.dependencies else ""
            print(f"  {step.id}. {step.description} [{step.action}]{deps}")
    except Exception as e:
        print(f"Error (LLM may not be available): {e}")
    
    print("\nPlanner test complete!")
