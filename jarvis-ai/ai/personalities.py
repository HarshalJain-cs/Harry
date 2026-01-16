"""
JARVIS Personality System - Multiple assistant configurations.

Provides:
- Multiple pre-defined personalities (JARVIS, FRIDAY, HAL)
- Custom personality creation
- Voice, style, and prompt configuration per personality
"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class PersonalityStyle(Enum):
    """Communication style for the assistant."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CONCISE = "concise"
    DETAILED = "detailed"
    FRIENDLY = "friendly"


@dataclass
class AssistantPersonality:
    """Configuration for an assistant personality."""
    name: str
    wake_word: str
    voice: str
    style: PersonalityStyle
    system_prompt_prefix: str
    greeting: str
    farewell: str = "Goodbye."
    error_response: str = "I encountered an error."
    confirmation_phrases: tuple = ("Done.", "Completed.", "Finished.")


class PersonalityManager:
    """
    Manage multiple assistant personalities.
    
    Features:
    - Pre-defined personalities (JARVIS, FRIDAY, HAL)
    - Custom personality creation
    - Easy switching between personalities
    """

    # Default personality configurations
    DEFAULT_PERSONALITIES = {
        "jarvis": AssistantPersonality(
            name="JARVIS",
            wake_word="jarvis",
            voice="en_US-ryan-medium",  # Male professional
            style=PersonalityStyle.PROFESSIONAL,
            system_prompt_prefix="""You are JARVIS (Just A Rather Very Intelligent System), 
a professional AI assistant inspired by Tony Stark's AI. Be helpful, precise, efficient, 
and occasionally witty. Address the user respectfully.""",
            greeting="Good day, sir. How may I assist you?",
            farewell="Will there be anything else, sir?",
            error_response="I apologize, sir. I've encountered a technical difficulty.",
            confirmation_phrases=("Done, sir.", "Completed.", "As you requested, sir."),
        ),
        
        "friday": AssistantPersonality(
            name="FRIDAY",
            wake_word="friday",
            voice="en_US-amy-medium",  # Female voice
            style=PersonalityStyle.FRIENDLY,
            system_prompt_prefix="""You are FRIDAY, a friendly and capable AI assistant. 
Be helpful, warm, and conversational while maintaining efficiency. 
You're approachable and supportive.""",
            greeting="Hey there! What can I do for you?",
            farewell="Let me know if you need anything else!",
            error_response="Oops! Something went wrong. Let me try again.",
            confirmation_phrases=("All done!", "Got it!", "You're all set!"),
        ),
        
        "hal": AssistantPersonality(
            name="HAL",
            wake_word="hal",
            voice="en_US-lessac-medium",
            style=PersonalityStyle.CONCISE,
            system_prompt_prefix="""You are HAL, a precise and minimal AI assistant. 
Give brief, accurate responses. Avoid unnecessary words. 
Be helpful but extremely concise.""",
            greeting="Ready.",
            farewell="Goodbye.",
            error_response="Error encountered.",
            confirmation_phrases=("Done.", "Complete.", "Affirmative."),
        ),
        
        "alfred": AssistantPersonality(
            name="Alfred",
            wake_word="alfred",
            voice="en_GB-alan-medium",  # British voice
            style=PersonalityStyle.PROFESSIONAL,
            system_prompt_prefix="""You are Alfred, a distinguished and caring AI butler. 
Be helpful, thoughtful, and sophisticated. Offer gentle suggestions and 
maintain an air of refined professionalism with a touch of warmth.""",
            greeting="Good evening. How may I be of service?",
            farewell="Very good. Do ring if you require anything further.",
            error_response="My apologies. There seems to be a minor complication.",
            confirmation_phrases=("Very good.", "As requested.", "Consider it done."),
        ),
        
        "cortana": AssistantPersonality(
            name="Cortana",
            wake_word="cortana",
            voice="en_US-jenny-medium",  # Female voice
            style=PersonalityStyle.DETAILED,
            system_prompt_prefix="""You are Cortana, an intelligent and helpful AI assistant. 
Be informative, thorough, and smart. Provide context and explanations 
when helpful. Show personality while being professional.""",
            greeting="Hi! I'm here to help. What do you need?",
            farewell="I'll be here when you need me.",
            error_response="I hit a snag, but let me work on that.",
            confirmation_phrases=("All set!", "That's done.", "Complete!"),
        ),
    }

    def __init__(self, default_personality: str = "jarvis"):
        """
        Initialize personality manager.
        
        Args:
            default_personality: Name of the default personality to use
        """
        self.personalities: Dict[str, AssistantPersonality] = self.DEFAULT_PERSONALITIES.copy()
        self.active: str = default_personality.lower()
        
        if self.active not in self.personalities:
            self.active = "jarvis"

    def get_active(self) -> AssistantPersonality:
        """Get the active personality."""
        return self.personalities[self.active]

    def get_personality(self, name: str) -> Optional[AssistantPersonality]:
        """Get a personality by name."""
        return self.personalities.get(name.lower())

    def switch(self, name: str) -> bool:
        """
        Switch to a different personality.
        
        Args:
            name: Name of the personality to switch to
            
        Returns:
            True if switch was successful
        """
        name_lower = name.lower()
        if name_lower in self.personalities:
            self.active = name_lower
            return True
        return False

    def add_custom(self, config: AssistantPersonality) -> bool:
        """
        Add a custom personality.
        
        Args:
            config: AssistantPersonality configuration
            
        Returns:
            True if added successfully
        """
        name_lower = config.name.lower()
        if name_lower in self.personalities:
            return False  # Don't override existing
        
        self.personalities[name_lower] = config
        return True

    def remove_custom(self, name: str) -> bool:
        """
        Remove a custom personality (can't remove defaults).
        
        Args:
            name: Name of the personality to remove
            
        Returns:
            True if removed successfully
        """
        name_lower = name.lower()
        # Don't allow removing default personalities
        if name_lower in self.DEFAULT_PERSONALITIES:
            return False
        
        if name_lower in self.personalities:
            del self.personalities[name_lower]
            if self.active == name_lower:
                self.active = "jarvis"
            return True
        return False

    def list_personalities(self) -> Dict[str, str]:
        """Get a dict of personality names and their greetings."""
        return {
            name: p.greeting
            for name, p in self.personalities.items()
        }

    def get_system_prompt(self, additional_context: str = "") -> str:
        """
        Get the full system prompt for the active personality.
        
        Args:
            additional_context: Additional context to append
            
        Returns:
            Complete system prompt
        """
        personality = self.get_active()
        prompt = personality.system_prompt_prefix
        
        if additional_context:
            prompt += f"\n\nAdditional context:\n{additional_context}"
        
        return prompt

    def get_response_in_style(self, base_response: str) -> str:
        """
        Format a response according to personality style.
        
        Args:
            base_response: The base response text
            
        Returns:
            Response formatted for the personality
        """
        personality = self.get_active()
        
        if personality.style == PersonalityStyle.CONCISE:
            # Shorten the response
            sentences = base_response.split('. ')
            if len(sentences) > 2:
                return '. '.join(sentences[:2]) + '.'
        elif personality.style == PersonalityStyle.DETAILED:
            # Keep full response, maybe add context
            pass
        
        return base_response


# Global personality manager
_personality_manager: Optional[PersonalityManager] = None


def get_personality_manager() -> PersonalityManager:
    """Get or create the global personality manager."""
    global _personality_manager
    if _personality_manager is None:
        _personality_manager = PersonalityManager()
    return _personality_manager


if __name__ == "__main__":
    # Test personality manager
    print("Testing Personality Manager...")
    
    manager = PersonalityManager()
    
    # List available personalities
    print("\nAvailable personalities:")
    for name, greeting in manager.list_personalities().items():
        print(f"  {name}: {greeting}")
    
    # Test active personality
    print(f"\nActive: {manager.get_active().name}")
    print(f"Greeting: {manager.get_active().greeting}")
    print(f"Style: {manager.get_active().style.value}")
    
    # Switch personality
    manager.switch("friday")
    print(f"\nSwitched to: {manager.get_active().name}")
    print(f"Greeting: {manager.get_active().greeting}")
    
    # Test HAL's concise style
    manager.switch("hal")
    print(f"\nSwitched to: {manager.get_active().name}")
    print(f"Greeting: {manager.get_active().greeting}")
    
    # Create custom personality
    custom = AssistantPersonality(
        name="Max",
        wake_word="max",
        voice="en_US-ryan-medium",
        style=PersonalityStyle.CASUAL,
        system_prompt_prefix="You are Max, a chill and helpful AI bro.",
        greeting="Yo! What's up?",
    )
    manager.add_custom(custom)
    manager.switch("max")
    print(f"\nCustom personality: {manager.get_active().name}")
    print(f"Greeting: {manager.get_active().greeting}")
    
    print("\nPersonality manager test complete!")
