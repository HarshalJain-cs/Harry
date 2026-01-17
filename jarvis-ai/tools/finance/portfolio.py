"""
JARVIS Portfolio Tracker - Investment portfolio management
==========================================================

Track positions, calculate gains/losses, and analyze performance.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class Position:
    """Investment position."""
    symbol: str
    quantity: float
    avg_cost: float
    added_at: str
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost


@dataclass
class PositionValue:
    """Position with current value."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    cost_basis: float
    market_value: float
    gain_loss: float
    gain_loss_percent: float


class Portfolio:
    """
    Investment portfolio tracker.
    
    Tracks holdings, calculates performance, and provides analysis.
    
    Usage:
        portfolio = Portfolio()
        portfolio.add_position("AAPL", 10, 150.0)
        value = portfolio.get_value()
    """
    
    def __init__(self, db_path: str = "./storage/finance.db"):
        """
        Initialize portfolio.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                quantity REAL NOT NULL,
                avg_cost REAL NOT NULL,
                added_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_position(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Add or update a position.
        
        Args:
            symbol: Stock ticker symbol
            quantity: Number of shares
            price: Purchase price per share
            
        Returns:
            Position info
        """
        symbol = symbol.upper()
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if position exists
        cursor.execute('SELECT quantity, avg_cost FROM positions WHERE symbol = ?', (symbol,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing position (average cost)
            old_qty, old_cost = existing
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_cost) + (quantity * price)) / new_qty
            
            cursor.execute('''
                UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ?
                WHERE symbol = ?
            ''', (new_qty, new_avg, now, symbol))
        else:
            # Create new position
            cursor.execute('''
                INSERT INTO positions (symbol, quantity, avg_cost, added_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, quantity, price, now, now))
        
        # Log transaction
        cursor.execute('''
            INSERT INTO transactions (symbol, transaction_type, quantity, price, timestamp)
            VALUES (?, 'buy', ?, ?, ?)
        ''', (symbol, quantity, price, now))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "total_cost": quantity * price
        }
    
    def remove_position(
        self,
        symbol: str,
        quantity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Remove or reduce a position.
        
        Args:
            symbol: Stock ticker symbol
            quantity: Shares to sell (None = all)
            
        Returns:
            Result info
        """
        symbol = symbol.upper()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT quantity, avg_cost FROM positions WHERE symbol = ?', (symbol,))
        existing = cursor.fetchone()
        
        if not existing:
            conn.close()
            return {"success": False, "error": f"No position in {symbol}"}
        
        current_qty, avg_cost = existing
        sell_qty = quantity if quantity else current_qty
        
        if sell_qty > current_qty:
            conn.close()
            return {"success": False, "error": f"Cannot sell {sell_qty}, only have {current_qty}"}
        
        now = datetime.now().isoformat()
        
        if sell_qty >= current_qty:
            # Remove entire position
            cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
        else:
            # Reduce position
            new_qty = current_qty - sell_qty
            cursor.execute('''
                UPDATE positions SET quantity = ?, updated_at = ?
                WHERE symbol = ?
            ''', (new_qty, now, symbol))
        
        # Log transaction
        cursor.execute('''
            INSERT INTO transactions (symbol, transaction_type, quantity, price, timestamp)
            VALUES (?, 'sell', ?, ?, ?)
        ''', (symbol, sell_qty, avg_cost, now))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "symbol": symbol,
            "quantity_sold": sell_qty,
            "remaining": current_qty - sell_qty
        }
    
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT symbol, quantity, avg_cost, added_at FROM positions')
        
        positions = [
            Position(
                symbol=row[0],
                quantity=row[1],
                avg_cost=row[2],
                added_at=row[3]
            )
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return positions
    
    def get_value(self) -> Dict[str, Any]:
        """
        Get total portfolio value with gains/losses.
        
        Returns:
            Portfolio value summary
        """
        positions = self.get_positions()
        
        if not positions:
            return {
                "total_value": 0,
                "total_cost": 0,
                "total_gain_loss": 0,
                "total_gain_loss_percent": 0,
                "positions": []
            }
        
        position_values = []
        total_value = 0
        total_cost = 0
        
        for pos in positions:
            current_price = self._get_price(pos.symbol)
            
            if current_price:
                market_value = pos.quantity * current_price
                gain_loss = market_value - pos.cost_basis
                gain_loss_pct = (gain_loss / pos.cost_basis * 100) if pos.cost_basis > 0 else 0
                
                position_values.append(PositionValue(
                    symbol=pos.symbol,
                    quantity=pos.quantity,
                    avg_cost=pos.avg_cost,
                    current_price=current_price,
                    cost_basis=round(pos.cost_basis, 2),
                    market_value=round(market_value, 2),
                    gain_loss=round(gain_loss, 2),
                    gain_loss_percent=round(gain_loss_pct, 2)
                ))
                
                total_value += market_value
                total_cost += pos.cost_basis
        
        total_gain_loss = total_value - total_cost
        total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_gain_loss": round(total_gain_loss, 2),
            "total_gain_loss_percent": round(total_gain_loss_pct, 2),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": p.avg_cost,
                    "current_price": p.current_price,
                    "market_value": p.market_value,
                    "gain_loss": p.gain_loss,
                    "gain_loss_percent": p.gain_loss_percent
                }
                for p in position_values
            ]
        }
    
    def get_performance(self, period: str = "1mo") -> Dict[str, Any]:
        """
        Get portfolio performance over time.
        
        Args:
            period: Time period for analysis
            
        Returns:
            Performance metrics
        """
        # Get current value breakdown
        value_data = self.get_value()
        
        # Calculate allocation
        total = value_data["total_value"]
        allocation = {}
        
        for pos in value_data["positions"]:
            allocation[pos["symbol"]] = round(
                (pos["market_value"] / total * 100) if total > 0 else 0, 2
            )
        
        # Get best and worst performers
        positions = value_data["positions"]
        if positions:
            best = max(positions, key=lambda p: p["gain_loss_percent"])
            worst = min(positions, key=lambda p: p["gain_loss_percent"])
        else:
            best = worst = None
        
        return {
            "period": period,
            "total_value": value_data["total_value"],
            "total_gain_loss": value_data["total_gain_loss"],
            "total_gain_loss_percent": value_data["total_gain_loss_percent"],
            "allocation": allocation,
            "best_performer": {
                "symbol": best["symbol"],
                "gain_loss_percent": best["gain_loss_percent"]
            } if best else None,
            "worst_performer": {
                "symbol": worst["symbol"],
                "gain_loss_percent": worst["gain_loss_percent"]
            } if worst else None,
            "num_positions": len(positions)
        }
    
    def get_transactions(
        self,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get transaction history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT symbol, transaction_type, quantity, price, timestamp
                FROM transactions
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol.upper(), limit))
        else:
            cursor.execute('''
                SELECT symbol, transaction_type, quantity, price, timestamp
                FROM transactions
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        transactions = [
            {
                "symbol": row[0],
                "type": row[1],
                "quantity": row[2],
                "price": row[3],
                "timestamp": row[4],
                "total": round(row[2] * row[3], 2)
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return transactions
    
    def _get_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return info.last_price if hasattr(info, 'last_price') else None
        except Exception:
            return None


# Singleton instance
_portfolio: Optional[Portfolio] = None


def get_portfolio() -> Portfolio:
    """Get or create global portfolio."""
    global _portfolio
    if _portfolio is None:
        _portfolio = Portfolio()
    return _portfolio
