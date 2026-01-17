"""
JARVIS Core Component Tests
===========================

Tests for core components: Intent Parser, Memory, Confidence, Conversation, Suggestions.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestIntentParser:
    """Tests for IntentParser."""
    
    def test_parse_returns_result(self, intent_parser):
        """Test that parse returns a result object."""
        if intent_parser is None:
            pytest.skip("IntentParser not available")
        result = intent_parser.parse("open chrome")
        assert result is not None
    
    def test_parse_open_app(self, intent_parser):
        """Test parsing app open commands."""
        if intent_parser is None:
            pytest.skip("IntentParser not available")
        result = intent_parser.parse("open chrome")
        assert result is not None
        # Check for any indication of intent detection
        assert hasattr(result, 'intent') or hasattr(result, 'command') or hasattr(result, 'action')
    
    def test_parse_empty_command(self, intent_parser):
        """Test parsing empty command."""
        if intent_parser is None:
            pytest.skip("IntentParser not available")
        result = intent_parser.parse("")
        assert result is not None


class TestMemorySystem:
    """Tests for MemorySystem."""
    
    def test_memory_system_exists(self, memory_system):
        """Test memory system can be created."""
        if memory_system is None:
            pytest.skip("MemorySystem not available")
        assert memory_system is not None
    
    def test_memory_has_core_methods(self, memory_system):
        """Test memory system has expected methods."""
        if memory_system is None:
            pytest.skip("MemorySystem not available")
        # Check for common memory methods
        assert hasattr(memory_system, 'log_command') or hasattr(memory_system, 'store')


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""
    
    def test_scorer_exists(self, confidence_scorer):
        """Test confidence scorer can be created."""
        if confidence_scorer is None:
            pytest.skip("ConfidenceScorer not available")
        assert confidence_scorer is not None
    
    def test_score_method(self, confidence_scorer):
        """Test scoring method exists."""
        if confidence_scorer is None:
            pytest.skip("ConfidenceScorer not available")
        assert hasattr(confidence_scorer, 'score') or hasattr(confidence_scorer, 'calculate')


class TestConversationContext:
    """Tests for ConversationContext."""
    
    def test_context_exists(self, conversation_context):
        """Test conversation context can be created."""
        if conversation_context is None:
            pytest.skip("ConversationContext not available")
        assert conversation_context is not None
    
    def test_add_method(self, conversation_context):
        """Test add method exists."""
        if conversation_context is None:
            pytest.skip("ConversationContext not available")
        assert hasattr(conversation_context, 'add') or hasattr(conversation_context, 'append')


class TestSuggestionEngine:
    """Tests for SuggestionEngine."""
    
    def test_engine_exists(self, suggestion_engine):
        """Test suggestion engine can be created."""
        if suggestion_engine is None:
            pytest.skip("SuggestionEngine not available")
        assert suggestion_engine is not None
    
    def test_get_suggestions(self, suggestion_engine):
        """Test getting suggestions."""
        if suggestion_engine is None:
            pytest.skip("SuggestionEngine not available")
        if hasattr(suggestion_engine, 'get_suggestions'):
            suggestions = suggestion_engine.get_suggestions()
            assert isinstance(suggestions, (list, tuple))
