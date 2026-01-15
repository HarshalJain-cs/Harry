"""
JARVIS Agent - Main orchestrator for the AI assistant.

Coordinates all components: wake word, STT, TTS, intent parsing,
confidence scoring, tool execution, and memory.
"""

import os
import sys
import time
import signal
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.wake_word import WakeWordDetector
from ai.stt import SpeechToText, AudioRecorder
from ai.tts import TextToSpeech, VoiceCharacter
from ai.llm import LLMClient
from core.intent_parser import IntentParser
from core.confidence import ConfidenceScorer, ExecutionMode
from core.memory import MemorySystem
from tools.registry import get_registry, ToolResult
from config.settings import get_settings


class AgentState(Enum):
    """Agent operational states."""
    IDLE = "idle"              # Waiting for wake word
    LISTENING = "listening"    # Recording user command
    PROCESSING = "processing"  # Parsing and deciding
    EXECUTING = "executing"    # Running action
    SPEAKING = "speaking"      # TTS response
    ERROR = "error"            # Error state


@dataclass
class CommandResult:
    """Result of processing a command."""
    command: str
    intent: str
    entities: dict
    confidence: float
    action_taken: str
    success: bool
    response: str


class JarvisAgent:
    """
    Main JARVIS agent orchestrator.
    
    Flow:
    1. Listen for wake word ("Jarvis")
    2. Record user command
    3. Transcribe with Whisper
    4. Parse intent with LLM
    5. Score confidence
    6. Execute or confirm based on score
    7. Respond with TTS
    8. Log to memory
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize JARVIS agent with all components."""
        print("Initializing JARVIS...")
        
        # Load settings
        self.settings = get_settings()
        
        # Initialize components
        self._init_components()
        
        # State
        self.state = AgentState.IDLE
        self.running = True
        self.current_voice = VoiceCharacter.ARIA
        
        # Callbacks
        self.on_wake: Optional[Callable] = None
        self.on_command: Optional[Callable[[str], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
        
        print("JARVIS initialized successfully!")
    
    def _init_components(self):
        """Initialize all sub-components."""
        # AI Components
        self.wake_detector = WakeWordDetector(
            keyword=self.settings.voice.wake_word
        )
        self.stt = SpeechToText(model_size=self.settings.voice.stt_model)
        self.tts = TextToSpeech(VoiceCharacter.ARIA)
        self.llm = LLMClient(model=self.settings.llm.model)
        self.recorder = AudioRecorder()
        
        # Core Components
        self.intent_parser = IntentParser(model=self.settings.llm.model)
        self.confidence_scorer = ConfidenceScorer()
        self.memory = MemorySystem()
        
        # Tools
        self.tools = get_registry()
    
    def run(self):
        """Main agent loop."""
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.speak(f"Hello! I am JARVIS. Say '{self.settings.voice.wake_word}' to activate me.")
        
        while self.running:
            try:
                self._main_loop()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                self.state = AgentState.ERROR
                time.sleep(1)
        
        self.shutdown()
    
    def _main_loop(self):
        """Single iteration of the main loop."""
        # State: IDLE - waiting for wake word
        self.state = AgentState.IDLE
        print(f"\n[{self.state.value}] Listening for '{self.settings.voice.wake_word}'...")
        
        # Wait for wake word
        if not self.wake_detector.listen(timeout=1.0):
            return  # No wake word detected, loop again
        
        print("[WAKE] Wake word detected!")
        if self.on_wake:
            self.on_wake()
        
        # Acknowledge wake
        self.speak("Yes?", block=True)
        
        # State: LISTENING - record command
        self.state = AgentState.LISTENING
        print(f"[{self.state.value}] Recording command...")
        
        audio = self.recorder.record(duration=self.settings.voice.listen_timeout)
        
        # State: PROCESSING - transcribe and parse
        self.state = AgentState.PROCESSING
        print(f"[{self.state.value}] Processing...")
        
        # Transcribe
        transcription = self.stt.transcribe(audio)
        command = transcription.text
        print(f"Command: '{command}'")
        
        if self.on_command:
            self.on_command(command)
        
        if not command.strip():
            self.speak("I didn't catch that. Please try again.")
            return
        
        # Parse intent
        parsed = self.intent_parser.parse(command)
        print(f"Intent: {parsed.intent}, Confidence: {parsed.confidence:.2f}")
        
        # Get tool and score confidence
        tool_name = self.intent_parser.get_tool_for_intent(parsed.intent)
        tool = self.tools.get(tool_name) if tool_name else None
        risk = tool.risk_level.value if tool else "low"
        
        conf_result = self.confidence_scorer.score(parsed.confidence, risk)
        
        # Decide action based on confidence
        result = self._handle_intent(parsed, conf_result, tool_name)
        
        # Log to memory
        self.memory.log_command(
            command=command,
            intent=parsed.intent,
            entities=parsed.entities,
            success=result.success,
            execution_time=0.0,
        )
        
        # Respond
        self.speak(result.response)
        
        if self.on_response:
            self.on_response(result.response)
    
    def _handle_intent(
        self,
        parsed,
        conf_result,
        tool_name: Optional[str],
    ) -> CommandResult:
        """Handle parsed intent based on confidence."""
        
        # REFUSE - confidence too low
        if conf_result.mode == ExecutionMode.REFUSE:
            return CommandResult(
                command=parsed.raw_command,
                intent=parsed.intent,
                entities=parsed.entities,
                confidence=conf_result.score,
                action_taken="refused",
                success=False,
                response="I'm not confident enough about what you want. Could you please clarify?",
            )
        
        # CONFIRM - medium confidence
        if conf_result.mode == ExecutionMode.CONFIRM:
            # For now, ask for confirmation (in future, could wait for "yes")
            action_desc = self._describe_action(parsed)
            return CommandResult(
                command=parsed.raw_command,
                intent=parsed.intent,
                entities=parsed.entities,
                confidence=conf_result.score,
                action_taken="awaiting_confirmation",
                success=True,
                response=f"Just to confirm - should I {action_desc}?",
            )
        
        # EXECUTE - high confidence
        self.state = AgentState.EXECUTING
        
        if not tool_name or not self.tools.get(tool_name):
            # Handle question or unknown intent
            if parsed.intent == "question":
                return self._handle_question(parsed)
            
            return CommandResult(
                command=parsed.raw_command,
                intent=parsed.intent,
                entities=parsed.entities,
                confidence=conf_result.score,
                action_taken="no_tool",
                success=False,
                response=f"I don't know how to {parsed.intent} yet.",
            )
        
        # Execute tool
        try:
            tool_result = self.tools.execute(tool_name, parsed.entities)
            
            if tool_result.success:
                response = self._generate_success_response(parsed, tool_result)
                return CommandResult(
                    command=parsed.raw_command,
                    intent=parsed.intent,
                    entities=parsed.entities,
                    confidence=conf_result.score,
                    action_taken=tool_name,
                    success=True,
                    response=response,
                )
            else:
                return CommandResult(
                    command=parsed.raw_command,
                    intent=parsed.intent,
                    entities=parsed.entities,
                    confidence=conf_result.score,
                    action_taken=tool_name,
                    success=False,
                    response=f"Sorry, I couldn't complete that. {tool_result.error or ''}",
                )
        
        except Exception as e:
            return CommandResult(
                command=parsed.raw_command,
                intent=parsed.intent,
                entities=parsed.entities,
                confidence=conf_result.score,
                action_taken=tool_name,
                success=False,
                response=f"An error occurred: {str(e)}",
            )
    
    def _handle_question(self, parsed) -> CommandResult:
        """Handle question intents using LLM."""
        response = self.llm.generate(
            prompt=parsed.raw_command,
            system_prompt="You are JARVIS, a helpful AI assistant. Give concise, helpful answers.",
            max_tokens=200,
        )
        
        return CommandResult(
            command=parsed.raw_command,
            intent="question",
            entities=parsed.entities,
            confidence=parsed.confidence,
            action_taken="llm_response",
            success=True,
            response=response.content,
        )
    
    def _describe_action(self, parsed) -> str:
        """Create human-readable action description."""
        intent = parsed.intent
        entities = parsed.entities
        
        if intent == "open_app":
            return f"open {entities.get('app', 'that application')}"
        elif intent == "web_search":
            return f"search for {entities.get('query', 'that')}"
        elif intent == "close_app":
            return f"close {entities.get('target', 'this window')}"
        elif intent == "type_text":
            text = entities.get('text', '')
            return f"type '{text[:20]}{'...' if len(text) > 20 else ''}'"
        else:
            return f"do {intent}"
    
    def _generate_success_response(self, parsed, result: ToolResult) -> str:
        """Generate success response based on action."""
        intent = parsed.intent
        
        if intent == "open_app":
            return f"Opened {parsed.entities.get('app', 'the application')}."
        elif intent == "web_search":
            return f"Searching for {parsed.entities.get('query', 'that')}."
        elif intent == "close_app":
            return "Done."
        elif intent == "type_text":
            return "Typed."
        else:
            return "Done."
    
    def speak(self, text: str, block: bool = True):
        """Speak text using TTS."""
        self.state = AgentState.SPEAKING
        print(f"[JARVIS] {text}")
        self.tts.speak(text, voice=self.current_voice, block=block)
    
    def process_text_command(self, command: str) -> CommandResult:
        """Process a text command (no voice)."""
        parsed = self.intent_parser.parse(command)
        
        tool_name = self.intent_parser.get_tool_for_intent(parsed.intent)
        tool = self.tools.get(tool_name) if tool_name else None
        risk = tool.risk_level.value if tool else "low"
        
        conf_result = self.confidence_scorer.score(parsed.confidence, risk)
        
        return self._handle_intent(parsed, conf_result, tool_name)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self.running = False
    
    def shutdown(self):
        """Clean shutdown of all components."""
        print("JARVIS shutting down...")
        self.running = False
        
        self.wake_detector.cleanup()
        self.memory.close()
        
        print("Goodbye!")


if __name__ == "__main__":
    # Run JARVIS agent
    agent = JarvisAgent()
    agent.run()
