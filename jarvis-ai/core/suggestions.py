"""
JARVIS Smart Suggestions - Proactive suggestions based on user patterns.

Provides:
- Time-based suggestions (morning routines, work hours)
- Sequence-based suggestions (app usage patterns)
- Pattern learning from user actions
"""

from typing import List, Dict, Optional
from datetime import datetime, time
from dataclasses import dataclass, field


@dataclass
class Suggestion:
    """A proactive suggestion."""
    action: str
    description: str
    confidence: float
    reason: str
    params: Dict = field(default_factory=dict)


class SuggestionEngine:
    """
    Generate smart suggestions based on patterns.
    
    Features:
    - Time-based suggestions (morning, work hours, evening)
    - App sequence suggestions (after Chrome, often use VS Code)
    - Learning from user patterns
    """

    # Common app sequences (default patterns)
    DEFAULT_SEQUENCES = {
        "chrome": ["vscode", "terminal", "notepad"],
        "outlook": ["teams", "calendar", "excel"],
        "vscode": ["terminal", "chrome", "github"],
        "slack": ["chrome", "notion"],
        "spotify": [],  # Usually standalone
    }

    def __init__(self, memory_system=None):
        """
        Initialize suggestion engine.
        
        Args:
            memory_system: Optional MemorySystem for accessing command history
        """
        self.memory = memory_system
        self.time_patterns: Dict[str, List[str]] = {}
        self.app_sequences: Dict[str, List[str]] = self.DEFAULT_SEQUENCES.copy()
        self.last_app: Optional[str] = None

    def get_suggestions(self, context: Dict = None) -> List[Suggestion]:
        """
        Get contextual suggestions.
        
        Args:
            context: Optional context dict with keys like 'last_app', 'current_time'
            
        Returns:
            List of top suggestions sorted by confidence
        """
        suggestions = []
        context = context or {}

        # Time-based suggestions
        time_suggestions = self._time_based_suggestions()
        suggestions.extend(time_suggestions)

        # Sequence-based suggestions (after last app)
        if context.get("last_app"):
            self.last_app = context["last_app"]
        
        if self.last_app:
            seq_suggestions = self._sequence_suggestions(self.last_app)
            suggestions.extend(seq_suggestions)

        # Pattern-based suggestions from history
        if self.memory:
            pattern_suggestions = self._pattern_suggestions()
            suggestions.extend(pattern_suggestions)

        # Sort by confidence and return top 3
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:3]

    def _time_based_suggestions(self) -> List[Suggestion]:
        """Suggestions based on time of day patterns."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday

        suggestions = []

        # Morning routine (6-9 AM on weekdays)
        if 6 <= hour < 9 and weekday < 5:
            suggestions.append(Suggestion(
                action="open_app",
                description="Start your morning apps?",
                confidence=0.7,
                reason="Morning routine time",
                params={"app": "outlook"}
            ))
            suggestions.append(Suggestion(
                action="open_app",
                description="Check your calendar?",
                confidence=0.65,
                reason="Start of day planning",
                params={"app": "calendar"}
            ))

        # Work hours (9 AM - 5 PM on weekdays)
        elif 9 <= hour < 17 and weekday < 5:
            # Suggest based on most common actions
            if self.memory:
                try:
                    stats = self.memory.get_command_stats()
                    top_intents = stats.get("top_intents", {})
                    if top_intents:
                        most_common = list(top_intents.keys())[0]
                        suggestions.append(Suggestion(
                            action=most_common,
                            description=f"Your most used: {most_common.replace('_', ' ')}",
                            confidence=0.5,
                            reason="Based on your usage patterns"
                        ))
                except:
                    pass

        # Lunch time (12-1 PM)
        elif 12 <= hour < 13:
            suggestions.append(Suggestion(
                action="web_search",
                description="Take a lunch break?",
                confidence=0.4,
                reason="It's lunch time",
                params={"query": "nearby restaurants"}
            ))

        # Evening (5-8 PM)
        elif 17 <= hour < 20:
            suggestions.append(Suggestion(
                action="open_app",
                description="Wind down with some music?",
                confidence=0.5,
                reason="End of work day",
                params={"app": "spotify"}
            ))

        # Night (after 10 PM)
        elif hour >= 22:
            suggestions.append(Suggestion(
                action="system",
                description="Time to rest? Enable night mode?",
                confidence=0.4,
                reason="It's getting late"
            ))

        return suggestions

    def _sequence_suggestions(self, last_app: str) -> List[Suggestion]:
        """Suggestions based on app usage sequences."""
        suggestions = []
        last_app_lower = last_app.lower()

        # Find matching sequence
        next_apps = self.app_sequences.get(last_app_lower, [])
        
        for i, next_app in enumerate(next_apps[:2]):  # Top 2
            confidence = 0.6 - (i * 0.1)  # Decrease confidence for later items
            suggestions.append(Suggestion(
                action="open_app",
                description=f"Open {next_app.title()}?",
                confidence=confidence,
                reason=f"Often used after {last_app.title()}",
                params={"app": next_app}
            ))

        return suggestions

    def _pattern_suggestions(self) -> List[Suggestion]:
        """Suggestions based on learned patterns from history."""
        suggestions = []
        
        if not self.memory:
            return suggestions

        try:
            # Get recent commands to find patterns
            recent = self.memory.get_recent_commands(20)
            
            # Find frequently used commands
            intent_counts: Dict[str, int] = {}
            for cmd in recent:
                intent = cmd.get("intent")
                if intent:
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Suggest most frequent intent
            if intent_counts:
                top_intent = max(intent_counts, key=intent_counts.get)
                count = intent_counts[top_intent]
                if count >= 3:  # Only suggest if used at least 3 times recently
                    suggestions.append(Suggestion(
                        action=top_intent,
                        description=f"Frequently used: {top_intent.replace('_', ' ')}",
                        confidence=min(0.7, count * 0.1),
                        reason=f"Used {count} times recently"
                    ))
        except:
            pass

        return suggestions

    def learn_pattern(self, action: str, context: Dict = None):
        """
        Learn from user actions to improve suggestions.
        
        Args:
            action: The action that was taken
            context: Context including timestamp, last_app, etc.
        """
        context = context or {}
        timestamp = context.get("timestamp", datetime.now())
        hour = timestamp.hour
        
        # Learn time patterns
        hour_key = f"hour_{hour}"
        if hour_key not in self.time_patterns:
            self.time_patterns[hour_key] = []
        self.time_patterns[hour_key].append(action)

        # Learn app sequences
        if self.last_app and "app" in context:
            current_app = context["app"].lower()
            last_app_lower = self.last_app.lower()
            
            if last_app_lower not in self.app_sequences:
                self.app_sequences[last_app_lower] = []
            
            if current_app not in self.app_sequences[last_app_lower]:
                self.app_sequences[last_app_lower].append(current_app)
        
        # Update last app
        if "app" in context:
            self.last_app = context["app"]

    def set_last_app(self, app_name: str):
        """Update the last used app."""
        self.last_app = app_name


# Global suggestion engine
_suggestion_engine: Optional[SuggestionEngine] = None


def get_suggestion_engine(memory_system=None) -> SuggestionEngine:
    """Get or create the global suggestion engine."""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine(memory_system)
    return _suggestion_engine


if __name__ == "__main__":
    # Test suggestion engine
    print("Testing Suggestion Engine...")
    
    engine = SuggestionEngine()
    
    # Get time-based suggestions
    print("\nTime-based suggestions:")
    suggestions = engine.get_suggestions()
    for s in suggestions:
        print(f"  [{s.confidence:.1f}] {s.description} - {s.reason}")
    
    # Simulate app usage
    engine.set_last_app("chrome")
    print("\nAfter using Chrome:")
    suggestions = engine.get_suggestions({"last_app": "chrome"})
    for s in suggestions:
        print(f"  [{s.confidence:.1f}] {s.description} - {s.reason}")
    
    # Learn a pattern
    engine.learn_pattern("open_app", {"app": "vscode"})
    print("\nLearned pattern: chrome -> vscode")
    
    print("\nSuggestion engine test complete!")
