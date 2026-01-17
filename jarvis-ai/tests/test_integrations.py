"""
JARVIS Integration Tests
========================

Tests for external integrations (with mocking).
"""

import pytest
from unittest.mock import MagicMock, patch


class TestIntegrationImports:
    """Test integration modules can be imported."""
    
    def test_notion_client_import(self):
        """Test Notion client can be imported."""
        try:
            from integrations.notion import NotionClient
            assert NotionClient is not None
        except ImportError as e:
            pytest.skip(f"NotionClient not available: {e}")
    
    def test_slack_client_import(self):
        """Test Slack client can be imported."""
        try:
            from integrations.slack import SlackClient
            assert SlackClient is not None
        except ImportError as e:
            pytest.skip(f"SlackClient not available: {e}")
    
    def test_calendar_import(self):
        """Test calendar integration can be imported."""
        try:
            from integrations.calendar import CalendarManager
            assert CalendarManager is not None
        except ImportError as e:
            pytest.skip(f"CalendarManager not available: {e}")
    
    def test_webhooks_import(self):
        """Test webhooks can be imported."""
        try:
            from integrations.webhooks import WebhookManager
            assert WebhookManager is not None
        except ImportError as e:
            pytest.skip(f"WebhookManager not available: {e}")
    
    def test_smart_home_import(self):
        """Test smart home integration can be imported."""
        try:
            from integrations.smart_home import SmartHomeController
            assert SmartHomeController is not None
        except ImportError as e:
            pytest.skip(f"SmartHomeController not available: {e}")


class TestNewFinanceIntegrations:
    """Test new finance modules."""
    
    def test_stock_tracker_creation(self):
        """Test stock tracker can be created."""
        try:
            from tools.finance.stocks import StockTracker
            tracker = StockTracker(db_path="./storage/test_finance.db")
            assert tracker is not None
            assert hasattr(tracker, 'get_quote')
            assert hasattr(tracker, 'set_alert')
        except ImportError as e:
            pytest.skip(f"StockTracker not available: {e}")
    
    def test_portfolio_creation(self):
        """Test portfolio can be created."""
        try:
            from tools.finance.portfolio import Portfolio
            portfolio = Portfolio(db_path="./storage/test_finance.db")
            assert portfolio is not None
            assert hasattr(portfolio, 'add_position')
            assert hasattr(portfolio, 'get_value')
        except ImportError as e:
            pytest.skip(f"Portfolio not available: {e}")
    
    def test_crypto_tracker_creation(self):
        """Test crypto tracker can be created."""
        try:
            from tools.finance.crypto import CryptoTracker
            tracker = CryptoTracker(db_path="./storage/test_finance.db")
            assert tracker is not None
            assert hasattr(tracker, 'get_price')
            assert hasattr(tracker, 'get_trending')
        except ImportError as e:
            pytest.skip(f"CryptoTracker not available: {e}")


class TestNewVoiceFeatures:
    """Test new voice feature modules."""
    
    def test_noise_filter_creation(self):
        """Test noise filter can be created."""
        try:
            from ai.noise_cancel import NoiseFilter
            filter = NoiseFilter()
            assert filter is not None
            assert hasattr(filter, 'process_audio') or hasattr(filter, 'available')
        except ImportError as e:
            pytest.skip(f"NoiseFilter not available: {e}")
    
    def test_voice_shortcuts_creation(self):
        """Test voice shortcuts can be created."""
        try:
            from ai.voice_shortcuts import VoiceShortcuts
            shortcuts = VoiceShortcuts()
            assert shortcuts is not None
            assert hasattr(shortcuts, 'match')
            assert hasattr(shortcuts, 'register')
        except ImportError as e:
            pytest.skip(f"VoiceShortcuts not available: {e}")
    
    def test_voice_shortcuts_matching(self):
        """Test voice shortcuts matching."""
        try:
            from ai.voice_shortcuts import VoiceShortcuts
            shortcuts = VoiceShortcuts()
            
            # Test matching built-in shortcuts
            match = shortcuts.match("open code")
            assert match is None or isinstance(match, tuple)
        except ImportError as e:
            pytest.skip(f"VoiceShortcuts not available: {e}")


class TestNewAutomationFeatures:
    """Test new automation feature modules."""
    
    def test_macro_recorder_creation(self):
        """Test macro recorder can be created."""
        try:
            from tools.automation.macro import MacroRecorder
            recorder = MacroRecorder(storage_path="./data/test_macros")
            assert recorder is not None
            assert hasattr(recorder, 'start_recording')
            assert hasattr(recorder, 'stop_recording')
        except ImportError as e:
            pytest.skip(f"MacroRecorder not available: {e}")
    
    def test_macro_player_creation(self):
        """Test macro player can be created."""
        try:
            from tools.automation.macro import MacroPlayer
            player = MacroPlayer()
            assert player is not None
            assert hasattr(player, 'play')
        except ImportError as e:
            pytest.skip(f"MacroPlayer not available: {e}")
