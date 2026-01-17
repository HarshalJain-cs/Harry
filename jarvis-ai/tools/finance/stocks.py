"""
JARVIS Stock Tracker - Stock market data and alerts
====================================================

Provides stock quotes, history, and price alerts using yfinance.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class StockQuote:
    """Stock quote data."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    name: str
    timestamp: str


@dataclass
class PriceAlert:
    """Price alert definition."""
    id: str
    symbol: str
    condition: str  # 'above' or 'below'
    target_price: float
    created_at: str
    triggered: bool = False
    triggered_at: Optional[str] = None


class StockTracker:
    """
    Stock market tracker.
    
    Provides real-time quotes, historical data, and price alerts.
    
    Usage:
        tracker = StockTracker()
        quote = tracker.get_quote("AAPL")
        tracker.set_alert("AAPL", "above", 200.0)
    """
    
    def __init__(self, db_path: str = "./storage/finance.db"):
        """
        Initialize stock tracker.
        
        Args:
            db_path: Path to SQLite database
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError(
                "yfinance not installed. Run: pip install yfinance"
            )
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        
        # Watchlist
        self.watchlist: List[str] = []
        self._load_watchlist()
        
        # Cache for quotes
        self._quote_cache: Dict[str, tuple] = {}
        self._cache_duration = 60  # seconds
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price REAL NOT NULL,
                created_at TEXT NOT NULL,
                triggered INTEGER DEFAULT 0,
                triggered_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Get current stock quote.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            StockQuote or None if not found
        """
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._quote_cache:
            cached, timestamp = self._quote_cache[symbol]
            if (datetime.now() - timestamp).seconds < self._cache_duration:
                return cached
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'regularMarketPrice' not in info:
                # Try fast_info for basic data
                fast = ticker.fast_info
                if hasattr(fast, 'last_price'):
                    quote = StockQuote(
                        symbol=symbol,
                        price=fast.last_price or 0,
                        change=0,
                        change_percent=0,
                        volume=int(fast.last_volume or 0),
                        market_cap=fast.market_cap,
                        name=symbol,
                        timestamp=datetime.now().isoformat()
                    )
                    self._quote_cache[symbol] = (quote, datetime.now())
                    return quote
                return None
            
            prev_close = info.get('previousClose', 0)
            current = info.get('regularMarketPrice', 0)
            change = current - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            quote = StockQuote(
                symbol=symbol,
                price=current,
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=info.get('regularMarketVolume', 0),
                market_cap=info.get('marketCap'),
                name=info.get('shortName', symbol),
                timestamp=datetime.now().isoformat()
            )
            
            self._quote_cache[symbol] = (quote, datetime.now())
            return quote
            
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return None
    
    def get_history(
        self,
        symbol: str,
        period: str = "1mo"
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical price data.
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            
        Returns:
            Dict with OHLCV data
        """
        symbol = symbol.upper()
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            return {
                "symbol": symbol,
                "period": period,
                "data": {
                    "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                    "open": hist['Open'].tolist(),
                    "high": hist['High'].tolist(),
                    "low": hist['Low'].tolist(),
                    "close": hist['Close'].tolist(),
                    "volume": hist['Volume'].tolist()
                },
                "summary": {
                    "start_price": round(hist['Close'].iloc[0], 2),
                    "end_price": round(hist['Close'].iloc[-1], 2),
                    "high": round(hist['High'].max(), 2),
                    "low": round(hist['Low'].min(), 2),
                    "avg_volume": int(hist['Volume'].mean()),
                    "change_percent": round(
                        (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) /
                        hist['Close'].iloc[0] * 100, 2
                    )
                }
            }
            
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return None
    
    def set_alert(
        self,
        symbol: str,
        condition: str,
        target_price: float
    ) -> Dict[str, Any]:
        """
        Set a price alert.
        
        Args:
            symbol: Stock ticker symbol
            condition: 'above' or 'below'
            target_price: Target price
            
        Returns:
            Alert info
        """
        symbol = symbol.upper()
        condition = condition.lower()
        
        if condition not in ['above', 'below']:
            return {"success": False, "error": "Condition must be 'above' or 'below'"}
        
        import uuid
        alert_id = str(uuid.uuid4())[:8]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (id, symbol, condition, target_price, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (alert_id, symbol, condition, target_price, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "alert_id": alert_id,
            "symbol": symbol,
            "condition": condition,
            "target_price": target_price
        }
    
    def get_alerts(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all alerts, optionally filtered by symbol."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute(
                'SELECT * FROM alerts WHERE symbol = ? AND triggered = 0',
                (symbol.upper(),)
            )
        else:
            cursor.execute('SELECT * FROM alerts WHERE triggered = 0')
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "id": row[0],
                "symbol": row[1],
                "condition": row[2],
                "target_price": row[3],
                "created_at": row[4]
            })
        
        conn.close()
        return alerts
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check all alerts against current prices.
        
        Returns:
            List of triggered alerts
        """
        triggered = []
        alerts = self.get_alerts()
        
        for alert in alerts:
            quote = self.get_quote(alert["symbol"])
            if not quote:
                continue
            
            is_triggered = False
            if alert["condition"] == "above" and quote.price >= alert["target_price"]:
                is_triggered = True
            elif alert["condition"] == "below" and quote.price <= alert["target_price"]:
                is_triggered = True
            
            if is_triggered:
                # Mark as triggered
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE alerts SET triggered = 1, triggered_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), alert["id"]))
                conn.commit()
                conn.close()
                
                triggered.append({
                    **alert,
                    "current_price": quote.price,
                    "triggered_at": datetime.now().isoformat()
                })
        
        return triggered
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alerts WHERE id = ?', (alert_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    # Watchlist methods
    def add_to_watchlist(self, symbol: str) -> bool:
        """Add symbol to watchlist."""
        symbol = symbol.upper()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO watchlist (symbol, added_at) VALUES (?, ?)',
                (symbol, datetime.now().isoformat())
            )
            conn.commit()
            if symbol not in self.watchlist:
                self.watchlist.append(symbol)
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def remove_from_watchlist(self, symbol: str) -> bool:
        """Remove symbol from watchlist."""
        symbol = symbol.upper()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
        
        return deleted
    
    def get_watchlist_quotes(self) -> List[StockQuote]:
        """Get quotes for all watchlist symbols."""
        quotes = []
        for symbol in self.watchlist:
            quote = self.get_quote(symbol)
            if quote:
                quotes.append(quote)
        return quotes
    
    def _load_watchlist(self):
        """Load watchlist from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT symbol FROM watchlist')
        self.watchlist = [row[0] for row in cursor.fetchall()]
        conn.close()


# Singleton instance
_tracker: Optional[StockTracker] = None


def get_stock_tracker() -> StockTracker:
    """Get or create global stock tracker."""
    global _tracker
    if _tracker is None:
        _tracker = StockTracker()
    return _tracker


# Tool functions
def get_stock_price(symbol: str) -> str:
    """Get current stock price."""
    tracker = get_stock_tracker()
    quote = tracker.get_quote(symbol)
    
    if quote:
        direction = "📈" if quote.change >= 0 else "📉"
        return (
            f"{quote.name} ({quote.symbol}): ${quote.price:.2f} "
            f"{direction} {quote.change:+.2f} ({quote.change_percent:+.2f}%)"
        )
    return f"Could not find quote for {symbol}"


def set_stock_alert(symbol: str, condition: str, target: float) -> str:
    """Set a stock price alert."""
    tracker = get_stock_tracker()
    result = tracker.set_alert(symbol, condition, target)
    
    if result["success"]:
        return f"Alert set: {symbol} goes {condition} ${target}"
    return f"Error: {result.get('error', 'Unknown error')}"
