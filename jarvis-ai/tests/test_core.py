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
        result = intent_parser.parse("open chrome")
        assert result is not None
        assert hasattr(result, 'intent') or hasattr(result, 'command')
    
    def test_parse_open_app(self, intent_parser):
        """Test parsing app open commands."""
        # Mock the LLM response for deterministic testing
        intent_parser.llm.generate.return_value = MagicMock(
            content='{"intent": "open_app", "entities": {"app": "chrome"}}'
        )
        
        result = intent_parser.parse("open chrome")
        assert result.intent == "open_app"
        assert "app" in result.entities
    
    def test_parse_web_search(self, intent_parser):
        """Test parsing web search commands."""
        intent_parser.llm.generate.return_value = MagicMock(
            content='{"intent": "web_search", "entities": {"query": "python tutorials"}}'
        )
        
        result = intent_parser.parse("search for python tutorials")
        assert result.intent == "web_search"
        assert result.entities.get("query") == "python tutorials"
    
    def test_parse_empty_command(self, intent_parser):
        """Test parsing empty command."""
        result = intent_parser.parse("")
        assert result is not None


class TestMemorySystem:
    """Tests for MemorySystem."""
    
    def test_log_command(self, memory_system):
        """Test logging a command."""
        memory_system.log_command(
            command="open chrome",
            intent="open_app",
            entities={"app": "chrome"},
            success=True,
            execution_time=0.1
        )
        
        commands = memory_system.get_recent_commands(1)
        assert len(commands) == 1
        assert commands[0]["command"] == "open chrome"
    
    def test_get_recent_commands(self, memory_system):
        """Test retrieving recent commands."""
        # Log multiple commands
        for i in range(5):
            memory_system.log_command(
                command=f"test command {i}",
                intent="test_intent",
                entities={},
                success=True,
                execution_time=0.1
            )
        
        commands = memory_system.get_recent_commands(3)
        assert len(commands) == 3
    
    def test_store_preference(self, memory_system):
        """Test storing a preference."""
        memory_system.store_preference("theme", "dark")
        value = memory_system.get_preference("theme")
        assert value == "dark"
    
    def test_store_fact(self, memory_system):
        """Test storing a fact."""
        memory_system.store_fact("user_name", "John")
        fact = memory_system.get_facts().get("user_name")
        assert fact == "John"


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""
    
    def test_score_high_confidence(self, confidence_scorer):
        """Test high confidence returns auto mode."""
        result = confidence_scorer.score(0.95, "low")
        assert result.score >= 0.9
        assert result.mode.value == "auto"
    
    def test_score_medium_confidence(self, confidence_scorer):
        """Test medium confidence returns confirm mode."""
        result = confidence_scorer.score(0.7, "medium")
        assert result.mode.value == "confirm"
    
    def test_score_low_confidence(self, confidence_scorer):
        """Test low confidence returns ask mode."""
        result = confidence_scorer.score(0.4, "high")
        assert result.mode.value == "ask"
    
    def test_score_adjusts_for_risk(self, confidence_scorer):
        """Test score adjusts based on risk level."""
        high_risk = confidence_scorer.score(0.8, "high")
        low_risk = confidence_scorer.score(0.8, "low")
        
        # High risk should be more cautious
        assert high_risk.score <= low_risk.score


class TestConversationContext:
    """Tests for ConversationContext."""
    
    def test_add_and_retrieve(self, conversation_context):
        """Test adding and retrieving context."""
        conversation_context.add(
            command="open chrome",
            intent="open_app",
            entities={"app": "chrome"},
            response="Opening Chrome"
        )
        
        history = conversation_context.get_history()
        assert len(history) > 0
        assert history[-1]["command"] == "open chrome"
    
    def test_resolve_reference_it(self, conversation_context):
        """Test resolving 'it' reference."""
        conversation_context.add(
            command="open chrome",
            intent="open_app",
            entities={"app": "chrome"},
            response="Opening Chrome"
        )
        
        resolved = conversation_context.resolve_reference("close it")
        assert "chrome" in resolved.lower() or "it" not in resolved.lower()
    
    def test_resolve_reference_that(self, conversation_context):
        """Test resolving 'that' reference."""
        conversation_context.add(
            command="search for python",
            intent="web_search",
            entities={"query": "python"},
            response="Searching for python"
        )
        
        resolved = conversation_context.resolve_reference("save that")
        assert resolved is not None
    
    def test_context_limit(self, conversation_context):
        """Test context doesn't grow unbounded."""
        for i in range(100):
            conversation_context.add(
                command=f"command {i}",
                intent="test",
                entities={},
                response=f"response {i}"
            )
        
        history = conversation_context.get_history()
        assert len(history) <= 50  # Should be limited


class TestSuggestionEngine:
    """Tests for SuggestionEngine."""
    
    def test_get_suggestions(self, suggestion_engine):
        """Test getting suggestions."""
        suggestions = suggestion_engine.get_suggestions()
        assert isinstance(suggestions, list)
    
    def test_suggestions_based_on_time(self, suggestion_engine):
        """Test time-based suggestions."""
        with patch('core.suggestions.datetime') as mock_dt:
            # Mock morning time
            mock_dt.now.return_value.hour = 9
            suggestions = suggestion_engine.get_suggestions()
            # Should return relevant suggestions
            assert isinstance(suggestions, list)
    
    def test_suggestions_limit(self, suggestion_engine):
        """Test suggestions are limited in number."""
        suggestions = suggestion_engine.get_suggestions(limit=3)
        assert len(suggestions) <= 3
