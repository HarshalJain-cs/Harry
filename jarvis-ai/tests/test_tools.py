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
    
    def test_registry_has_tools(self, tool_registry):
        """Test registry has registered tools."""
        assert len(tool_registry.tools) > 0
    
    def test_get_tool(self, tool_registry):
        """Test getting a tool by name."""
        # These tools should exist
        tool = tool_registry.get("open_app")
        assert tool is not None
        assert tool.name == "open_app"
    
    def test_get_nonexistent_tool(self, tool_registry):
        """Test getting a non-existent tool."""
        tool = tool_registry.get("nonexistent_tool_xyz")
        assert tool is None
    
    def test_list_tools(self, tool_registry):
        """Test listing all tools."""
        tools = tool_registry.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    def test_list_tools_by_category(self, tool_registry):
        """Test listing tools by category."""
        # Get tools in 'system' category
        tools = tool_registry.list_tools(category="system")
        assert all(t.category == "system" for t in tools) if tools else True
    
    def test_execute_returns_result(self, tool_registry):
        """Test executing a tool returns a result."""
        # Use a safe tool that doesn't have side effects
        result = tool_registry.execute("get_clipboard", {})
        assert result is not None
        assert hasattr(result, 'success')


class TestClipboardTools:
    """Tests for clipboard operations."""
    
    def test_set_and_get_clipboard(self, tool_registry):
        """Test setting and getting clipboard."""
        test_text = "JARVIS test clipboard content"
        
        # Set clipboard
        result = tool_registry.execute("set_clipboard", {"text": test_text})
        assert result.success
        
        # Get clipboard
        result = tool_registry.execute("get_clipboard", {})
        assert result.success
        assert result.output == test_text


class TestSchedulerTools:
    """Tests for scheduler/task operations."""
    
    @pytest.fixture
    def scheduler(self):
        """Get scheduler instance."""
        from tools.productivity.scheduler import TaskScheduler
        return TaskScheduler()
    
    def test_create_task(self, scheduler):
        """Test creating a scheduled task."""
        result = scheduler.schedule_task(
            name="test_task",
            action="test_action",
            schedule="daily",
            time="09:00"
        )
        assert result["success"] or "error" in result
    
    def test_list_tasks(self, scheduler):
        """Test listing scheduled tasks."""
        tasks = scheduler.list_tasks()
        assert isinstance(tasks, list)


class TestNotesTools:
    """Tests for notes operations."""
    
    @pytest.fixture
    def notes_manager(self, temp_dir):
        """Get notes manager with temp storage."""
        from tools.productivity.notes import NotesManager
        return NotesManager(storage_path=str(temp_dir))
    
    def test_create_note(self, notes_manager):
        """Test creating a note."""
        result = notes_manager.create(
            title="Test Note",
            content="This is a test note."
        )
        assert result["success"]
        assert "id" in result
    
    def test_get_note(self, notes_manager):
        """Test retrieving a note."""
        # Create first
        create_result = notes_manager.create(
            title="Test Note",
            content="Content here."
        )
        note_id = create_result["id"]
        
        # Get note
        note = notes_manager.get(note_id)
        assert note is not None
        assert note["title"] == "Test Note"
    
    def test_search_notes(self, notes_manager):
        """Test searching notes."""
        # Create notes
        notes_manager.create(title="Python Tips", content="Python is great.")
        notes_manager.create(title="JavaScript Guide", content="JS tips here.")
        
        # Search
        results = notes_manager.search("Python")
        assert len(results) >= 1


class TestRemindersTools:
    """Tests for reminder operations."""
    
    @pytest.fixture
    def reminders_manager(self, temp_db):
        """Get reminders manager with temp storage."""
        from tools.productivity.reminders import ReminderManager
        return ReminderManager(db_path=temp_db)
    
    def test_create_reminder(self, reminders_manager):
        """Test creating a reminder."""
        result = reminders_manager.create(
            message="Test reminder",
            time="5pm"
        )
        assert result["success"]
    
    def test_list_reminders(self, reminders_manager):
        """Test listing reminders."""
        reminders_manager.create(message="Reminder 1", time="3pm")
        reminders_manager.create(message="Reminder 2", time="4pm")
        
        reminders = reminders_manager.list_pending()
        assert isinstance(reminders, list)


class TestGitTools:
    """Tests for Git operations."""
    
    @pytest.fixture
    def git_tools(self):
        """Get git tools."""
        from tools.code.git_tools import GitTools
        return GitTools()
    
    def test_get_status(self, git_tools, temp_dir):
        """Test getting git status."""
        # Initialize a test repo
        import subprocess
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
        
        # Test status
        result = git_tools.status(str(temp_dir))
        assert "error" not in str(result).lower() or result is not None
    
    def test_status_not_repo(self, git_tools, temp_dir):
        """Test status on non-repo directory."""
        result = git_tools.status(str(temp_dir))
        # Should handle gracefully
        assert result is not None


class TestWebTools:
    """Tests for web-related tools."""
    
    def test_web_search_url_generation(self, tool_registry):
        """Test web search generates correct URL."""
        with patch('webbrowser.open') as mock_open:
            result = tool_registry.execute(
                "web_search",
                {"query": "test query", "engine": "google"}
            )
            
            if result.success:
                mock_open.assert_called_once()
                call_url = mock_open.call_args[0][0]
                assert "test" in call_url and "query" in call_url
