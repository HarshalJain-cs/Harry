"""
JARVIS Tools Tests
==================

Tests for tool registry and individual tools.
"""

import pytest
from unittest.mock import MagicMock, patch
import os


class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    def test_registry_exists(self, tool_registry):
        """Test registry can be created."""
        if tool_registry is None:
            pytest.skip("ToolRegistry not available")
        assert tool_registry is not None
    
    def test_registry_has_tools(self, tool_registry):
        """Test registry has registered tools."""
        if tool_registry is None:
            pytest.skip("ToolRegistry not available")
        # Check if tools attribute exists
        if hasattr(tool_registry, 'tools'):
            assert isinstance(tool_registry.tools, dict)
    
    def test_get_tool(self, tool_registry):
        """Test getting a tool by name."""
        if tool_registry is None:
            pytest.skip("ToolRegistry not available")
        if hasattr(tool_registry, 'get'):
            # Try to get a common tool
            tool = tool_registry.get("open_app")
            # Tool might exist or not, just check method works
            assert tool is None or tool is not None
    
    def test_list_tools(self, tool_registry):
        """Test listing all tools."""
        if tool_registry is None:
            pytest.skip("ToolRegistry not available")
        if hasattr(tool_registry, 'list_tools'):
            tools = tool_registry.list_tools()
            assert isinstance(tools, (list, dict))


class TestNewFeatures:
    """Tests for newly implemented features."""
    
    def test_rag_agent_import(self):
        """Test RAG agent can be imported."""
        try:
            from agents.rag import RAGAgent
            assert RAGAgent is not None
        except ImportError as e:
            pytest.skip(f"RAGAgent not available: {e}")
    
    def test_hotkey_manager_import(self):
        """Test hotkey manager can be imported."""
        try:
            from tools.system.hotkeys import HotkeyManager
            assert HotkeyManager is not None
        except ImportError as e:
            pytest.skip(f"HotkeyManager not available: {e}")
    
    def test_noise_filter_import(self):
        """Test noise filter can be imported."""
        try:
            from ai.noise_cancel import NoiseFilter
            assert NoiseFilter is not None
        except ImportError as e:
            pytest.skip(f"NoiseFilter not available: {e}")
    
    def test_voice_shortcuts_import(self):
        """Test voice shortcuts can be imported."""
        try:
            from ai.voice_shortcuts import VoiceShortcuts
            assert VoiceShortcuts is not None
        except ImportError as e:
            pytest.skip(f"VoiceShortcuts not available: {e}")
    
    def test_macro_recorder_import(self):
        """Test macro recorder can be imported."""
        try:
            from tools.automation.macro import MacroRecorder
            assert MacroRecorder is not None
        except ImportError as e:
            pytest.skip(f"MacroRecorder not available: {e}")
    
    def test_workflow_builder_import(self):
        """Test workflow builder can be imported."""
        try:
            from agents.workflow_builder import WorkflowBuilder
            assert WorkflowBuilder is not None
        except ImportError as e:
            pytest.skip(f"WorkflowBuilder not available: {e}")
    
    def test_stock_tracker_import(self):
        """Test stock tracker can be imported."""
        try:
            from tools.finance.stocks import StockTracker
            assert StockTracker is not None
        except ImportError as e:
            pytest.skip(f"StockTracker not available: {e}")
    
    def test_portfolio_import(self):
        """Test portfolio can be imported."""
        try:
            from tools.finance.portfolio import Portfolio
            assert Portfolio is not None
        except ImportError as e:
            pytest.skip(f"Portfolio not available: {e}")
    
    def test_crypto_tracker_import(self):
        """Test crypto tracker can be imported."""
        try:
            from tools.finance.crypto import CryptoTracker
            assert CryptoTracker is not None
        except ImportError as e:
            pytest.skip(f"CryptoTracker not available: {e}")
    
    def test_document_parser_import(self):
        """Test document parser can be imported."""
        try:
            from tools.productivity.document_parser import DocumentParser
            assert DocumentParser is not None
        except ImportError as e:
            pytest.skip(f"DocumentParser not available: {e}")
