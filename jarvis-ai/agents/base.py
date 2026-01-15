"""
JARVIS Agent Base - Core agent abstractions.

Provides base classes for building autonomous agents that can
reason, plan, and execute multi-step tasks.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStep:
    """A single step in agent execution."""
    id: str
    action: str
    params: Dict[str, Any]
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    result: Optional[Any] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool
    output: Any
    steps: List[AgentStep] = field(default_factory=list)
    total_time: float = 0.0
    error: Optional[str] = None


class AgentMemory:
    """
    Short-term memory for agent context.
    
    Stores recent actions, observations, and context for
    the current task execution.
    """
    
    def __init__(self, max_items: int = 50):
        self.max_items = max_items
        self.items: List[Dict] = []
        self.context: Dict[str, Any] = {}
    
    def add(self, item_type: str, content: Any, metadata: Dict = None):
        """Add an item to memory."""
        self.items.append({
            "type": item_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })
        
        # Trim if needed
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]
    
    def get_recent(self, count: int = 10, item_type: str = None) -> List[Dict]:
        """Get recent items from memory."""
        items = self.items
        if item_type:
            items = [i for i in items if i["type"] == item_type]
        return items[-count:]
    
    def set_context(self, key: str, value: Any):
        """Set context variable."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context variable."""
        return self.context.get(key, default)
    
    def to_text(self, count: int = 10) -> str:
        """Convert recent memory to text for LLM context."""
        recent = self.get_recent(count)
        lines = []
        for item in recent:
            lines.append(f"[{item['type']}] {item['content']}")
        return "\n".join(lines)
    
    def clear(self):
        """Clear memory."""
        self.items.clear()
        self.context.clear()


class Agent(ABC):
    """
    Base class for autonomous agents.
    
    Agents can:
    - Receive a goal/task
    - Plan steps to achieve it
    - Execute steps using tools
    - Adapt based on results
    - Report completion or failure
    """
    
    def __init__(
        self,
        name: str,
        llm_model: str = "phi3:mini",
        max_steps: int = 20,
        verbose: bool = False,
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent identifier
            llm_model: LLM model to use
            max_steps: Maximum steps before stopping
            verbose: Print debug info
        """
        self.name = name
        self.llm_model = llm_model
        self.max_steps = max_steps
        self.verbose = verbose
        
        self.state = AgentState.IDLE
        self.memory = AgentMemory()
        self.steps: List[AgentStep] = []
        self.llm = None
        self.tools = None
    
    def _init_components(self):
        """Initialize LLM and tools lazily."""
        if self.llm is None:
            from ai.llm import LLMClient
            self.llm = LLMClient(model=self.llm_model)
        
        if self.tools is None:
            from tools.registry import get_registry
            self.tools = get_registry()
    
    def log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(f"[{self.name}] {message}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type."""
        pass
    
    @abstractmethod
    def run(self, task: str, context: Dict = None) -> AgentResult:
        """
        Run the agent on a task.
        
        Args:
            task: The goal or task to accomplish
            context: Additional context
            
        Returns:
            AgentResult with success status and output
        """
        pass
    
    def think(self, prompt: str) -> str:
        """Use LLM to reason about the task."""
        self._init_components()
        self.state = AgentState.THINKING
        
        response = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7,
        )
        
        return response.content
    
    def decide_action(self, observation: str) -> Optional[Dict]:
        """
        Decide the next action based on observation.
        
        Returns dict with:
        - action: tool name or "complete" or "fail"
        - params: parameters for the tool
        - reasoning: why this action
        """
        self._init_components()
        
        # Get available tools
        tool_list = [
            f"- {name}: {tool.description}"
            for name, tool in self.tools.tools.items()
        ][:30]  # Limit
        
        prompt = f"""Current observation:
{observation}

Recent memory:
{self.memory.to_text(5)}

Available tools:
{chr(10).join(tool_list)}

What should I do next? Respond with JSON:
{{"action": "tool_name or 'complete' or 'fail'", "params": {{}}, "reasoning": "why"}}"""
        
        response = self.think(prompt)
        
        try:
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return None
    
    def execute_action(self, action: str, params: Dict) -> AgentStep:
        """Execute an action and return the step result."""
        self._init_components()
        self.state = AgentState.EXECUTING
        
        step = AgentStep(
            id=f"step_{len(self.steps)}",
            action=action,
            params=params,
            reasoning="",
        )
        
        try:
            result = self.tools.execute(action, params)
            step.result = result.output if result else None
            step.success = result.success if result else False
            step.error = result.error if result and not result.success else None
        except Exception as e:
            step.success = False
            step.error = str(e)
        
        self.steps.append(step)
        self.memory.add("action", f"{action}: {step.result if step.success else step.error}")
        
        return step
    
    def reset(self):
        """Reset agent state."""
        self.state = AgentState.IDLE
        self.memory.clear()
        self.steps.clear()


class SimpleReActAgent(Agent):
    """
    Simple ReAct (Reasoning + Acting) agent.
    
    Uses thought-action-observation loop to accomplish tasks.
    """
    
    SYSTEM_PROMPT = """You are a helpful AI agent that accomplishes tasks by reasoning and taking actions.

For each step:
1. THINK: Analyze the current situation
2. ACT: Choose the best action
3. OBSERVE: Look at the result

Always respond with valid JSON:
{"thought": "your reasoning", "action": "tool_name", "params": {"key": "value"}}

Use action "complete" when done, "fail" if stuck.
Keep actions simple and focused."""
    
    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT
    
    def run(self, task: str, context: Dict = None) -> AgentResult:
        """Run the ReAct loop."""
        import time
        start_time = time.time()
        
        self._init_components()
        self.reset()
        
        self.memory.set_context("task", task)
        self.memory.add("task", task)
        
        self.log(f"Starting task: {task}")
        
        observation = f"Task: {task}"
        if context:
            observation += f"\nContext: {context}"
        
        for i in range(self.max_steps):
            self.log(f"Step {i+1}/{self.max_steps}")
            
            # Decide action
            decision = self.decide_action(observation)
            
            if not decision:
                self.log("Could not decide action")
                continue
            
            action = decision.get("action", "")
            params = decision.get("params", {})
            reasoning = decision.get("thought", decision.get("reasoning", ""))
            
            self.log(f"Action: {action} | Reasoning: {reasoning[:50]}...")
            
            # Check for completion
            if action == "complete":
                self.state = AgentState.COMPLETED
                return AgentResult(
                    success=True,
                    output=reasoning,
                    steps=self.steps,
                    total_time=time.time() - start_time,
                )
            
            if action == "fail":
                self.state = AgentState.FAILED
                return AgentResult(
                    success=False,
                    output=None,
                    steps=self.steps,
                    total_time=time.time() - start_time,
                    error=reasoning,
                )
            
            # Execute action
            step = self.execute_action(action, params)
            step.reasoning = reasoning
            
            # Update observation
            if step.success:
                observation = f"Action '{action}' succeeded: {step.result}"
            else:
                observation = f"Action '{action}' failed: {step.error}"
            
            self.memory.add("observation", observation)
        
        # Max steps reached
        self.state = AgentState.FAILED
        return AgentResult(
            success=False,
            output=None,
            steps=self.steps,
            total_time=time.time() - start_time,
            error=f"Max steps ({self.max_steps}) reached",
        )


if __name__ == "__main__":
    print("Testing Agent Base...")
    
    # Test memory
    memory = AgentMemory()
    memory.add("thought", "I need to open Chrome")
    memory.add("action", "open_app: chrome")
    memory.add("observation", "Chrome opened successfully")
    
    print("\nMemory contents:")
    for item in memory.get_recent(5):
        print(f"  [{item['type']}] {item['content']}")
    
    print(f"\nMemory as text:\n{memory.to_text()}")
    
    print("\nAgent base test complete!")
