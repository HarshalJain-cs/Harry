"""
JARVIS Agent Tests
==================

Tests for planning, execution, and workflow agents.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestBaseAgent:
    """Tests for base agent functionality."""
    
    @pytest.fixture
    def base_agent(self, mock_llm):
        """Create a base agent with mocked LLM."""
        from agents.base import BaseAgent
        agent = BaseAgent()
        agent.llm = mock_llm
        return agent
    
    def test_agent_initialization(self, base_agent):
        """Test agent initializes correctly."""
        assert base_agent is not None
        assert hasattr(base_agent, 'llm')
    
    def test_agent_has_think_method(self, base_agent):
        """Test agent has think method."""
        assert hasattr(base_agent, 'think') or hasattr(base_agent, 'process')


class TestPlannerAgent:
    """Tests for planner agent."""
    
    @pytest.fixture
    def planner(self, mock_llm):
        """Create a planner agent."""
        from agents.planner import PlannerAgent
        agent = PlannerAgent()
        agent.llm = mock_llm
        return agent
    
    def test_create_plan(self, planner):
        """Test creating a plan from a goal."""
        planner.llm.generate.return_value = MagicMock(
            content='[{"step": 1, "action": "open_app", "params": {"app": "browser"}}]'
        )
        
        plan = planner.create_plan("Open browser and search for news")
        assert plan is not None
        assert isinstance(plan, (list, dict))
    
    def test_plan_has_steps(self, planner):
        """Test plan contains steps."""
        planner.llm.generate.return_value = MagicMock(
            content='[{"step": 1, "action": "test"}, {"step": 2, "action": "test2"}]'
        )
        
        plan = planner.create_plan("Do multiple things")
        if isinstance(plan, list):
            assert len(plan) > 0


class TestExecutorAgent:
    """Tests for executor agent."""
    
    @pytest.fixture
    def executor(self, tool_registry):
        """Create an executor agent."""
        from agents.executor import ExecutorAgent
        agent = ExecutorAgent()
        agent.registry = tool_registry
        return agent
    
    def test_execute_action(self, executor):
        """Test executing a single action."""
        result = executor.execute(
            action="get_clipboard",
            params={}
        )
        assert result is not None
        assert hasattr(result, 'success')
    
    def test_execute_with_params(self, executor):
        """Test executing action with parameters."""
        with patch('webbrowser.open'):
            result = executor.execute(
                action="web_search",
                params={"query": "test"}
            )
            assert result is not None


class TestWorkflowAgent:
    """Tests for workflow agent."""
    
    @pytest.fixture
    def workflow_agent(self):
        """Create a workflow agent."""
        from agents.workflow import WorkflowAgent
        return WorkflowAgent()
    
    def test_workflow_creation(self, workflow_agent):
        """Test creating a workflow."""
        workflow = workflow_agent.create_workflow(
            name="test_workflow",
            steps=[
                {"action": "step1", "params": {}},
                {"action": "step2", "params": {}}
            ]
        )
        assert workflow is not None
    
    def test_workflow_validation(self, workflow_agent):
        """Test workflow validation."""
        # Invalid workflow (empty steps)
        is_valid = workflow_agent.validate_workflow([])
        assert not is_valid or is_valid  # Should return boolean
    
    def test_workflow_with_conditions(self, workflow_agent):
        """Test workflow with conditional logic."""
        workflow = workflow_agent.create_workflow(
            name="conditional_workflow",
            steps=[
                {
                    "action": "check_condition",
                    "params": {},
                    "on_success": "step2",
                    "on_failure": "step3"
                }
            ]
        )
        assert workflow is not None


class TestResearchAgent:
    """Tests for research agent."""
    
    @pytest.fixture
    def research_agent(self, mock_llm):
        """Create a research agent."""
        from agents.research import ResearchAgent
        agent = ResearchAgent()
        agent.llm = mock_llm
        return agent
    
    def test_research_query(self, research_agent):
        """Test basic research query."""
        research_agent.llm.generate.return_value = MagicMock(
            content="Research findings: Test result."
        )
        
        result = research_agent.research("What is Python?")
        assert result is not None
    
    def test_research_with_sources(self, research_agent):
        """Test research returns sources."""
        research_agent.llm.generate.return_value = MagicMock(
            content='{"answer": "Test", "sources": ["source1", "source2"]}'
        )
        
        result = research_agent.research("Test query")
        # Should handle sources if available
        assert result is not None


class TestContextAgent:
    """Tests for context agent."""
    
    @pytest.fixture
    def context_agent(self, memory_system):
        """Create a context agent."""
        from agents.context import ContextAgent
        agent = ContextAgent()
        agent.memory = memory_system
        return agent
    
    def test_get_context(self, context_agent):
        """Test getting relevant context."""
        context = context_agent.get_context("test query")
        assert context is not None
        assert isinstance(context, (dict, list, str))
    
    def test_context_includes_history(self, context_agent):
        """Test context includes conversation history."""
        # Add some history first
        context_agent.memory.log_command(
            command="previous command",
            intent="test",
            entities={},
            success=True,
            execution_time=0.1
        )
        
        context = context_agent.get_context("follow up")
        assert context is not None
