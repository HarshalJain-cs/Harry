"""
JARVIS Integration Tests
========================

Tests for external integrations (with mocking).
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


class TestNotionClient:
    """Tests for Notion integration."""
    
    @pytest.fixture
    def notion_client(self):
        """Create a mocked Notion client."""
        from integrations.notion import NotionClient
        client = NotionClient(api_key="test_key")
        return client
    
    def test_client_initialization(self, notion_client):
        """Test client initializes."""
        assert notion_client is not None
        assert hasattr(notion_client, 'api_key') or hasattr(notion_client, '_api_key')
    
    @patch('requests.post')
    def test_create_page(self, mock_post, notion_client):
        """Test creating a Notion page."""
        mock_post.return_value.json.return_value = {"id": "page_id"}
        mock_post.return_value.status_code = 200
        
        result = notion_client.create_page(
            database_id="db_123",
            properties={"Name": "Test Page"}
        )
        assert result is not None
    
    @patch('requests.get')
    def test_query_database(self, mock_get, notion_client):
        """Test querying a database."""
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.status_code = 200
        
        results = notion_client.query_database("db_123")
        assert isinstance(results, (list, dict))


class TestSlackClient:
    """Tests for Slack integration."""
    
    @pytest.fixture
    def slack_client(self):
        """Create a mocked Slack client."""
        from integrations.slack import SlackClient
        client = SlackClient(bot_token="xoxb-test")
        return client
    
    def test_client_initialization(self, slack_client):
        """Test client initializes."""
        assert slack_client is not None
    
    @patch('requests.post')
    def test_send_message(self, mock_post, slack_client):
        """Test sending a message."""
        mock_post.return_value.json.return_value = {"ok": True}
        mock_post.return_value.status_code = 200
        
        result = slack_client.send_message(
            channel="#general",
            text="Test message"
        )
        assert result is not None
    
    @patch('requests.get')
    def test_list_channels(self, mock_get, slack_client):
        """Test listing channels."""
        mock_get.return_value.json.return_value = {
            "ok": True,
            "channels": [{"id": "C123", "name": "general"}]
        }
        mock_get.return_value.status_code = 200
        
        channels = slack_client.list_channels()
        assert isinstance(channels, list)


class TestCalendarIntegration:
    """Tests for calendar integration."""
    
    @pytest.fixture
    def calendar_client(self):
        """Create a calendar client."""
        from integrations.calendar import CalendarManager
        return CalendarManager()
    
    def test_client_initialization(self, calendar_client):
        """Test client initializes."""
        assert calendar_client is not None
    
    def test_create_event(self, calendar_client):
        """Test creating an event."""
        with patch.object(calendar_client, '_api_call', return_value={"id": "event_1"}):
            result = calendar_client.create_event(
                title="Test Event",
                start_time="2026-01-20T10:00:00",
                end_time="2026-01-20T11:00:00"
            )
            assert result is not None
    
    def test_get_upcoming_events(self, calendar_client):
        """Test getting upcoming events."""
        with patch.object(calendar_client, '_api_call', return_value={"events": []}):
            events = calendar_client.get_upcoming_events(days=7)
            assert isinstance(events, (list, dict))


class TestWebhooks:
    """Tests for webhook functionality."""
    
    @pytest.fixture
    def webhook_manager(self):
        """Create a webhook manager."""
        from integrations.webhooks import WebhookManager
        return WebhookManager()
    
    def test_register_webhook(self, webhook_manager):
        """Test registering a webhook."""
        result = webhook_manager.register(
            name="test_webhook",
            url="https://example.com/webhook",
            events=["command.executed"]
        )
        assert result is not None
    
    def test_list_webhooks(self, webhook_manager):
        """Test listing webhooks."""
        webhooks = webhook_manager.list()
        assert isinstance(webhooks, list)
    
    @patch('requests.post')
    def test_trigger_webhook(self, mock_post, webhook_manager):
        """Test triggering a webhook."""
        mock_post.return_value.status_code = 200
        
        # Register first
        webhook_manager.register(
            name="test",
            url="https://example.com/hook",
            events=["test.event"]
        )
        
        # Trigger
        result = webhook_manager.trigger(
            event="test.event",
            data={"key": "value"}
        )
        # Should attempt to send


class TestAPIClient:
    """Tests for generic API client."""
    
    @pytest.fixture
    def api_client(self):
        """Create an API client."""
        from integrations.api_client import APIClient
        return APIClient(base_url="https://api.example.com")
    
    def test_client_initialization(self, api_client):
        """Test client initializes."""
        assert api_client is not None
        assert api_client.base_url == "https://api.example.com"
    
    @patch('requests.get')
    def test_get_request(self, mock_get, api_client):
        """Test GET request."""
        mock_get.return_value.json.return_value = {"data": "test"}
        mock_get.return_value.status_code = 200
        
        response = api_client.get("/endpoint")
        assert response is not None
    
    @patch('requests.post')
    def test_post_request(self, mock_post, api_client):
        """Test POST request."""
        mock_post.return_value.json.return_value = {"success": True}
        mock_post.return_value.status_code = 201
        
        response = api_client.post("/endpoint", data={"key": "value"})
        assert response is not None


class TestSmartHome:
    """Tests for smart home integration."""
    
    @pytest.fixture
    def smart_home(self):
        """Create a smart home controller."""
        from integrations.smart_home import SmartHomeController
        return SmartHomeController()
    
    def test_controller_initialization(self, smart_home):
        """Test controller initializes."""
        assert smart_home is not None
    
    def test_list_devices(self, smart_home):
        """Test listing devices."""
        with patch.object(smart_home, '_api_call', return_value={"devices": []}):
            devices = smart_home.list_devices()
            assert isinstance(devices, (list, dict))
    
    def test_control_device(self, smart_home):
        """Test controlling a device."""
        with patch.object(smart_home, '_api_call', return_value={"success": True}):
            result = smart_home.control(
                device_id="light_1",
                action="turn_on"
            )
            assert result is not None
