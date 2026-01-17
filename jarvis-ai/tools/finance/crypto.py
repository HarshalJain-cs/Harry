"""
JARVIS Crypto Tracker - Cryptocurrency tracking
================================================

Track crypto prices and trends using CoinGecko API.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import urllib.request
import urllib.error


@dataclass
class CryptoPrice:
    """Cryptocurrency price data."""
    id: str
    symbol: str
    name: str
    price_usd: float
    change_24h: float
    change_7d: Optional[float]
    market_cap: float
    volume_24h: float
    timestamp: str


class CryptoTracker:
    """
    Cryptocurrency tracker using CoinGecko API (free, no key needed).
    
    Usage:
        tracker = CryptoTracker()
        price = tracker.get_price("bitcoin")
        trending = tracker.get_trending()
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Common coin ID mappings
    COIN_ALIASES = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "ada": "cardano",
        "xrp": "ripple",
        "doge": "dogecoin",
        "dot": "polkadot",
        "matic": "matic-network",
        "link": "chainlink",
        "atom": "cosmos",
        "avax": "avalanche-2",
        "uni": "uniswap",
        "ltc": "litecoin",
        "bnb": "binancecoin"
    }
    
    def __init__(self, db_path: str = "./storage/finance.db"):
        """
        Initialize crypto tracker.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        
        # Cache
        self._price_cache: Dict[str, tuple] = {}
        self._cache_duration = 60  # seconds
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_alerts (
                id TEXT PRIMARY KEY,
                coin_id TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price REAL NOT NULL,
                created_at TEXT NOT NULL,
                triggered INTEGER DEFAULT 0,
                triggered_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_watchlist (
                coin_id TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _api_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make API request to CoinGecko."""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "JARVIS/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"API error: {e}")
            return None
    
    def _resolve_coin_id(self, coin: str) -> str:
        """Resolve coin symbol/name to CoinGecko ID."""
        coin = coin.lower()
        return self.COIN_ALIASES.get(coin, coin)
    
    def get_price(self, coin: str) -> Optional[CryptoPrice]:
        """
        Get current price for a cryptocurrency.
        
        Args:
            coin: Coin ID or symbol (e.g., 'bitcoin' or 'btc')
            
        Returns:
            CryptoPrice or None
        """
        coin_id = self._resolve_coin_id(coin)
        
        # Check cache
        if coin_id in self._price_cache:
            cached, timestamp = self._price_cache[coin_id]
            if (datetime.now() - timestamp).seconds < self._cache_duration:
                return cached
        
        endpoint = f"/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
        data = self._api_request(endpoint)
        
        if not data:
            return None
        
        try:
            market = data.get("market_data", {})
            
            price = CryptoPrice(
                id=data.get("id"),
                symbol=data.get("symbol", "").upper(),
                name=data.get("name"),
                price_usd=market.get("current_price", {}).get("usd", 0),
                change_24h=market.get("price_change_percentage_24h", 0),
                change_7d=market.get("price_change_percentage_7d"),
                market_cap=market.get("market_cap", {}).get("usd", 0),
                volume_24h=market.get("total_volume", {}).get("usd", 0),
                timestamp=datetime.now().isoformat()
            )
            
            self._price_cache[coin_id] = (price, datetime.now())
            return price
            
        except Exception as e:
            print(f"Error parsing data: {e}")
            return None
    
    def get_prices(self, coins: List[str]) -> List[CryptoPrice]:
        """
        Get prices for multiple coins.
        
        Args:
            coins: List of coin IDs/symbols
            
        Returns:
            List of CryptoPrice
        """
        coin_ids = [self._resolve_coin_id(c) for c in coins]
        ids_str = ",".join(coin_ids)
        
        endpoint = f"/coins/markets?vs_currency=usd&ids={ids_str}&order=market_cap_desc"
        data = self._api_request(endpoint)
        
        if not data:
            return []
        
        prices = []
        for coin in data:
            prices.append(CryptoPrice(
                id=coin.get("id"),
                symbol=coin.get("symbol", "").upper(),
                name=coin.get("name"),
                price_usd=coin.get("current_price", 0),
                change_24h=coin.get("price_change_percentage_24h", 0),
                change_7d=coin.get("price_change_percentage_7d"),
                market_cap=coin.get("market_cap", 0),
                volume_24h=coin.get("total_volume", 0),
                timestamp=datetime.now().isoformat()
            ))
        
        return prices
    
    def get_trending(self) -> List[Dict[str, Any]]:
        """
        Get trending cryptocurrencies.
        
        Returns:
            List of trending coins
        """
        data = self._api_request("/search/trending")
        
        if not data:
            return []
        
        trending = []
        for item in data.get("coins", [])[:10]:
            coin = item.get("item", {})
            trending.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc")
            })
        
        return trending
    
    def get_top_coins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top coins by market cap.
        
        Args:
            limit: Number of coins to return
            
        Returns:
            List of top coins
        """
        endpoint = f"/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}"
        data = self._api_request(endpoint)
        
        if not data:
            return []
        
        return [
            {
                "rank": i + 1,
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "price": coin.get("current_price"),
                "change_24h": coin.get("price_change_percentage_24h"),
                "market_cap": coin.get("market_cap")
            }
            for i, coin in enumerate(data)
        ]
    
    def set_alert(
        self,
        coin: str,
        condition: str,
        target_price: float
    ) -> Dict[str, Any]:
        """
        Set a crypto price alert.
        
        Args:
            coin: Coin ID or symbol
            condition: 'above' or 'below'
            target_price: Target USD price
            
        Returns:
            Alert info
        """
        coin_id = self._resolve_coin_id(coin)
        condition = condition.lower()
        
        if condition not in ['above', 'below']:
            return {"success": False, "error": "Condition must be 'above' or 'below'"}
        
        import uuid
        alert_id = str(uuid.uuid4())[:8]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO crypto_alerts (id, coin_id, condition, target_price, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (alert_id, coin_id, condition, target_price, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "alert_id": alert_id,
            "coin": coin_id,
            "condition": condition,
            "target_price": target_price
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM crypto_alerts WHERE triggered = 0')
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "id": row[0],
                "coin_id": row[1],
                "condition": row[2],
                "target_price": row[3],
                "created_at": row[4]
            })
        
        conn.close()
        return alerts
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alerts against current prices."""
        triggered = []
        alerts = self.get_alerts()
        
        for alert in alerts:
            price = self.get_price(alert["coin_id"])
            if not price:
                continue
            
            is_triggered = False
            if alert["condition"] == "above" and price.price_usd >= alert["target_price"]:
                is_triggered = True
            elif alert["condition"] == "below" and price.price_usd <= alert["target_price"]:
                is_triggered = True
            
            if is_triggered:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_alerts SET triggered = 1, triggered_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), alert["id"]))
                conn.commit()
                conn.close()
                
                triggered.append({
                    **alert,
                    "current_price": price.price_usd,
                    "triggered_at": datetime.now().isoformat()
                })
        
        return triggered


# Singleton instance
_tracker: Optional[CryptoTracker] = None


def get_crypto_tracker() -> CryptoTracker:
    """Get or create global crypto tracker."""
    global _tracker
    if _tracker is None:
        _tracker = CryptoTracker()
    return _tracker


# Tool functions
def get_crypto_price(coin: str) -> str:
    """Get cryptocurrency price."""
    tracker = get_crypto_tracker()
    price = tracker.get_price(coin)
    
    if price:
        direction = "📈" if price.change_24h >= 0 else "📉"
        return (
            f"{price.name} ({price.symbol}): ${price.price_usd:,.2f} "
            f"{direction} {price.change_24h:+.2f}% (24h)"
        )
    return f"Could not find price for {coin}"
