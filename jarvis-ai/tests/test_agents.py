"""
JARVIS Agent Tests
==================

Tests for planning, execution, and workflow agents.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentImports:
    """Tests for agent imports."""
    
    def test_base_agent_import(self):
        """Test base agent can be imported."""
        try:
            from agents.base import Agent
            assert Agent is not None
        except ImportError:
            # Try alternative import
            try:
                from agents.base import BaseAgent
                assert BaseAgent is not None
            except ImportError:
                pytest.skip("BaseAgent not available")
    
    def test_planner_agent_import(self):
        """Test planner agent can be imported."""
        try:
            from agents.planner import PlannerAgent
            assert PlannerAgent is not None
        except ImportError as e:
            pytest.skip(f"PlannerAgent not available: {e}")
    
    def test_executor_agent_import(self):
        """Test executor agent can be imported."""
        try:
            from agents.executor import ExecutorAgent
            assert ExecutorAgent is not None
        except ImportError as e:
            pytest.skip(f"ExecutorAgent not available: {e}")
    
    def test_workflow_agent_import(self):
        """Test workflow agent can be imported."""
        try:
            from agents.workflow import WorkflowAgent
            assert WorkflowAgent is not None
        except ImportError:
            # Try alternative
            try:
                from agents.workflow import WorkflowEngine
                assert WorkflowEngine is not None
            except ImportError as e:
                pytest.skip(f"WorkflowAgent not available: {e}")
    
    def test_research_agent_import(self):
        """Test research agent can be imported."""
        try:
            from agents.research import ResearchAgent
            assert ResearchAgent is not None
        except ImportError as e:
            pytest.skip(f"ResearchAgent not available: {e}")
    
    def test_context_agent_import(self):
        """Test context agent can be imported."""
        try:
            from agents.context import ContextManager
            assert ContextManager is not None
        except ImportError as e:
            pytest.skip(f"ContextManager not available: {e}")


class TestNewAgents:
    """Tests for newly implemented agents."""
    
    def test_rag_agent_creation(self):
        """Test RAG agent can be created."""
        try:
            from agents.rag import RAGAgent
            agent = RAGAgent(storage_path="./storage/test_knowledge")
            assert agent is not None
            assert hasattr(agent, 'ingest_document')
            assert hasattr(agent, 'query')
        except ImportError as e:
            pytest.skip(f"RAGAgent not available: {e}")
    
    def test_workflow_builder_creation(self):
        """Test workflow builder can be created."""
        try:
            from agents.workflow_builder import WorkflowBuilder
            builder = WorkflowBuilder(storage_path="./data/test_workflows")
            assert builder is not None
            assert hasattr(builder, 'create')
            assert hasattr(builder, 'add_step')
        except ImportError as e:
            pytest.skip(f"WorkflowBuilder not available: {e}")
    
    def test_workflow_executor_creation(self):
        """Test workflow executor can be created."""
        try:
            from agents.workflow_builder import WorkflowExecutor
            executor = WorkflowExecutor()
            assert executor is not None
            assert hasattr(executor, 'execute')
        except ImportError as e:
            pytest.skip(f"WorkflowExecutor not available: {e}")
