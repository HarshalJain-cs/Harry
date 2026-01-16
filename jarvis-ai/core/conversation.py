"""
JARVIS Conversation Context - Track conversation for natural follow-ups.

Enables:
- Reference resolution ("it", "that", "there")
- Context-aware responses
- Multi-turn conversation tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


@dataclass
class ConversationTurn:
    """A single turn in conversation."""
    user_input: str
    intent: str
    entities: Dict[str, Any]
    response: str
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationContext:
    """
    Track conversation for natural follow-ups.
    
    Features:
    - Maintains recent conversation history
    - Resolves references like "it", "that", "there"
    - Auto-expires after timeout
    - Provides context summary for LLM
    """

    def __init__(self, max_turns: int = 10, context_timeout: int = 300):
        """
        Initialize conversation context.
        
        Args:
            max_turns: Maximum conversation turns to remember
            context_timeout: Seconds before context expires (default: 5 minutes)
        """
        self.turns: List[ConversationTurn] = []
        self.max_turns = max_turns
        self.context_timeout = context_timeout
        self.current_topic: Optional[str] = None
        self.referenced_entities: Dict[str, Any] = {}

    def add_turn(self, turn: ConversationTurn):
        """
        Add a conversation turn.
        
        Args:
            turn: The conversation turn to add
        """
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

        # Update referenced entities from this turn
        self.referenced_entities.update(turn.entities)
        self.current_topic = turn.intent

    def add(
        self,
        user_input: str,
        intent: str,
        entities: Dict[str, Any],
        response: str,
    ):
        """
        Convenience method to add a turn.
        
        Args:
            user_input: What the user said
            intent: Parsed intent
            entities: Extracted entities
            response: JARVIS response
        """
        turn = ConversationTurn(
            user_input=user_input,
            intent=intent,
            entities=entities,
            response=response,
        )
        self.add_turn(turn)

    def resolve_reference(self, text: str) -> str:
        """
        Resolve pronouns and references like 'it', 'that', 'there'.
        
        Args:
            text: Input text with potential references
            
        Returns:
            Text with references resolved to actual values
        """
        if not self.is_context_valid():
            return text

        # Reference mappings
        references = {
            "it": self._get_last_object(),
            "that": self._get_last_object(),
            "this": self._get_last_object(),
            "there": self.referenced_entities.get("location"),
            "him": self.referenced_entities.get("person"),
            "her": self.referenced_entities.get("person"),
            "them": self.referenced_entities.get("people"),
        }

        resolved = text
        text_lower = text.lower()

        for ref, value in references.items():
            if value and ref in text_lower:
                # Replace only standalone words, not parts of words
                import re
                pattern = r'\b' + ref + r'\b'
                resolved = re.sub(pattern, str(value), resolved, flags=re.IGNORECASE)

        return resolved

    def _get_last_object(self) -> Optional[str]:
        """Get the last mentioned object/app/file."""
        # Priority order for what "it" likely refers to
        priority_keys = ["app", "application", "file", "url", "query", "task", "item"]
        
        for key in priority_keys:
            if key in self.referenced_entities:
                return self.referenced_entities[key]
        
        # Return first available entity if no priority match
        for key, value in self.referenced_entities.items():
            if isinstance(value, str) and value:
                return value
        
        return None

    def is_context_valid(self) -> bool:
        """Check if context is still valid (not timed out)."""
        if not self.turns:
            return False
        
        last_turn = self.turns[-1]
        age = datetime.now() - last_turn.timestamp
        return age < timedelta(seconds=self.context_timeout)

    def get_context_summary(self) -> str:
        """
        Get summary for LLM context.
        
        Returns:
            Formatted string of recent conversation
        """
        if not self.turns:
            return ""

        recent = self.turns[-3:]  # Last 3 turns
        lines = ["Recent conversation:"]
        
        for turn in recent:
            lines.append(f"User: {turn.user_input}")
            # Truncate long responses
            response = turn.response[:100] + "..." if len(turn.response) > 100 else turn.response
            lines.append(f"JARVIS: {response}")
        
        return "\n".join(lines)

    def get_last_intent(self) -> Optional[str]:
        """Get the intent from the last turn."""
        if self.turns:
            return self.turns[-1].intent
        return None

    def get_last_entities(self) -> Dict[str, Any]:
        """Get entities from the last turn."""
        if self.turns:
            return self.turns[-1].entities
        return {}

    def clear(self):
        """Clear conversation context."""
        self.turns.clear()
        self.referenced_entities.clear()
        self.current_topic = None


# Global conversation context
_conversation_context: Optional[ConversationContext] = None


def get_conversation_context() -> ConversationContext:
    """Get or create the global conversation context."""
    global _conversation_context
    if _conversation_context is None:
        _conversation_context = ConversationContext()
    return _conversation_context


if __name__ == "__main__":
    # Test conversation context
    print("Testing Conversation Context...")
    
    ctx = ConversationContext()
    
    # Simulate conversation
    ctx.add(
        user_input="open chrome",
        intent="open_app",
        entities={"app": "chrome"},
        response="Opening Chrome...",
    )
    
    print(f"Last intent: {ctx.get_last_intent()}")
    print(f"Referenced entities: {ctx.referenced_entities}")
    
    # Test reference resolution
    test_input = "close it"
    resolved = ctx.resolve_reference(test_input)
    print(f"'{test_input}' -> '{resolved}'")
    
    # Add another turn
    ctx.add(
        user_input="search for python tutorials",
        intent="web_search",
        entities={"query": "python tutorials"},
        response="Searching for python tutorials...",
    )
    
    print(f"\nContext summary:\n{ctx.get_context_summary()}")
    print(f"\nContext valid: {ctx.is_context_valid()}")
    
    print("\nConversation context test complete!")
