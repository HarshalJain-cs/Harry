"""
JARVIS Test Suite - Pytest Configuration and Fixtures
=====================================================

Provides shared fixtures for all test modules.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============ Mock Fixtures ============

@pytest.fixture
def mock_llm():
    """Mock LLM client for testing without Ollama."""
    mock = MagicMock()
    mock.generate.return_value = MagicMock(
        content="Test response",
        model="test-model",
        tokens_used=10
    )
    mock.chat.return_value = MagicMock(
        content="Test chat response",
        model="test-model"
    )
    return mock


@pytest.fixture
def mock_tts():
    """Mock TTS engine."""
    mock = MagicMock()
    mock.speak.return_value = True
    mock.speak_async.return_value = AsyncMock()
    return mock


@pytest.fixture
def mock_stt():
    """Mock STT engine."""
    mock = MagicMock()
    mock.transcribe.return_value = "test transcription"
    mock.listen.return_value = b"audio_data"
    return mock


# ============ Database Fixtures ============

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def temp_chroma():
    """Create a temporary ChromaDB directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============ Component Fixtures ============

@pytest.fixture
def memory_system(temp_db, temp_chroma):
    """Create a memory system with temporary storage."""
    try:
        from core.memory import MemorySystem
        memory = MemorySystem(
            db_path=temp_db,
            chroma_path=temp_chroma
        )
        yield memory
        memory.close()
    except ImportError:
        pytest.skip("MemorySystem not available")


@pytest.fixture
def intent_parser(mock_llm):
    """Create an intent parser with mocked LLM."""
    try:
        from core.intent_parser import IntentParser
        parser = IntentParser()
        parser.llm = mock_llm
        return parser
    except ImportError:
        pytest.skip("IntentParser not available")
    except RuntimeError as e:
        pytest.skip(f"IntentParser runtime error: {e}")
    except Exception as e:
        pytest.skip(f"IntentParser error: {e}")


@pytest.fixture
def confidence_scorer():
    """Create a confidence scorer."""
    try:
        from core.confidence import ConfidenceScorer
        return ConfidenceScorer()
    except ImportError:
        pytest.skip("ConfidenceScorer not available")
    except Exception as e:
        pytest.skip(f"ConfidenceScorer error: {e}")


@pytest.fixture
def conversation_context():
    """Create a conversation context tracker."""
    try:
        from core.conversation import ConversationContext
        return ConversationContext()
    except ImportError:
        pytest.skip("ConversationContext not available")
    except Exception as e:
        pytest.skip(f"ConversationContext error: {e}")


@pytest.fixture
def suggestion_engine():
    """Create a suggestion engine."""
    try:
        from core.suggestions import get_suggestion_engine
        return get_suggestion_engine()
    except ImportError:
        try:
            from core.suggestions import SuggestionEngine
            return SuggestionEngine()
        except ImportError:
            pytest.skip("SuggestionEngine not available")
    except Exception as e:
        pytest.skip(f"SuggestionEngine error: {e}")


@pytest.fixture
def tool_registry():
    """Get a fresh tool registry."""
    try:
        from tools.registry import get_registry
        return get_registry()
    except ImportError:
        try:
            from tools.registry import ToolRegistry
            return ToolRegistry()
        except ImportError:
            pytest.skip("ToolRegistry not available")


# ============ Sample Data Fixtures ============

@pytest.fixture
def sample_commands():
    """Sample commands for testing."""
    return [
        ("open chrome", "open_app", {"app": "chrome"}),
        ("search for python tutorials", "web_search", {"query": "python tutorials"}),
        ("set a reminder for 5pm", "set_reminder", {"time": "5pm"}),
        ("what time is it", "get_time", {}),
        ("take a screenshot", "screenshot", {}),
    ]


@pytest.fixture
def sample_documents(temp_dir):
    """Create sample documents for testing."""
    docs = {}
    
    # TXT file
    txt_path = temp_dir / "test.txt"
    txt_path.write_text("This is a test document.\nIt has multiple lines.\nTest content here.")
    docs["txt"] = txt_path
    
    # MD file
    md_path = temp_dir / "test.md"
    md_path.write_text("# Test Document\n\nThis is **markdown** content.\n\n- Item 1\n- Item 2")
    docs["md"] = md_path
    
    # JSON file
    json_path = temp_dir / "test.json"
    json_path.write_text('{"key": "value", "number": 42}')
    docs["json"] = json_path
    
    return docs


@pytest.fixture
def sample_audio():
    """Path to sample audio file (if exists)."""
    audio_path = PROJECT_ROOT / "tests" / "fixtures" / "sample.wav"
    if not audio_path.exists():
        return None
    return audio_path


# ============ Async Fixtures ============

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
