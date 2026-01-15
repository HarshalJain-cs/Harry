"""
JARVIS Database Tools - SQL query assistance and database management.

Provides natural language to SQL conversion and database operations.
"""

import os
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class TableInfo:
    """Database table information."""
    name: str
    columns: List[Dict[str, str]]
    row_count: int


@dataclass
class QueryResult:
    """Result of a database query."""
    success: bool
    columns: List[str]
    rows: List[Tuple]
    row_count: int
    error: Optional[str] = None


class DatabaseManager:
    """
    Database manager for SQLite operations.
    
    Provides:
    - Schema inspection
    - Query execution
    - Natural language to SQL
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self, db_path: Optional[str] = None):
        """Connect to database."""
        path = db_path or self.db_path
        if not path:
            raise ValueError("No database path specified")
        
        self.db_path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_tables(self) -> List[str]:
        """Get list of tables in database."""
        if not self.conn:
            raise ValueError("Not connected to database")
        
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name: str) -> TableInfo:
        """Get information about a table."""
        if not self.conn:
            raise ValueError("Not connected to database")
        
        # Get columns
        cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
        columns = [
            {
                "name": row[1],
                "type": row[2],
                "nullable": not row[3],
                "primary_key": bool(row[5]),
            }
            for row in cursor.fetchall()
        ]
        
        # Get row count
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        return TableInfo(
            name=table_name,
            columns=columns,
            row_count=row_count,
        )
    
    def get_schema(self) -> Dict[str, List[Dict]]:
        """Get full database schema."""
        tables = self.get_tables()
        schema = {}
        
        for table in tables:
            info = self.get_table_info(table)
            schema[table] = info.columns
        
        return schema
    
    def execute_query(
        self,
        query: str,
        params: Tuple = None,
        limit: int = 100,
    ) -> QueryResult:
        """Execute a SQL query."""
        if not self.conn:
            raise ValueError("Not connected to database")
        
        try:
            cursor = self.conn.execute(query, params or ())
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch rows with limit
            rows = cursor.fetchmany(limit)
            row_count = len(rows)
            
            # Check if there are more rows
            if cursor.fetchone():
                row_count = f"{limit}+"
            
            return QueryResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=row_count,
            )
        
        except Exception as e:
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                error=str(e),
            )
    
    def execute_write(self, query: str, params: Tuple = None) -> int:
        """Execute a write query (INSERT, UPDATE, DELETE)."""
        if not self.conn:
            raise ValueError("Not connected to database")
        
        cursor = self.conn.execute(query, params or ())
        self.conn.commit()
        return cursor.rowcount


class NL2SQL:
    """Convert natural language to SQL queries."""
    
    def __init__(self, schema: Dict[str, List[Dict]]):
        """
        Initialize NL2SQL converter.
        
        Args:
            schema: Database schema as dict of table -> columns
        """
        self.schema = schema
        self.schema_text = self._format_schema()
    
    def _format_schema(self) -> str:
        """Format schema for LLM prompt."""
        lines = []
        for table, columns in self.schema.items():
            col_defs = []
            for col in columns:
                col_def = f"{col['name']} {col['type']}"
                if col.get('primary_key'):
                    col_def += " PRIMARY KEY"
                col_defs.append(col_def)
            
            lines.append(f"TABLE {table} ({', '.join(col_defs)})")
        
        return '\n'.join(lines)
    
    def generate_query(self, question: str) -> Tuple[str, float]:
        """
        Generate SQL from natural language.
        
        Args:
            question: Natural language question
            
        Returns:
            Tuple of (SQL query, confidence score)
        """
        try:
            from ai.llm import LLMClient
            
            prompt = f"""Given this database schema:
{self.schema_text}

Convert this question to a SQL query:
Question: {question}

Return ONLY the SQL query, nothing else. Use standard SQLite syntax."""

            llm = LLMClient()
            response = llm.generate(prompt, temperature=0.3, max_tokens=200)
            
            sql = response.content.strip()
            
            # Clean up SQL
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            # Validate SQL is SELECT only (for safety)
            sql_upper = sql.upper()
            if not sql_upper.startswith('SELECT'):
                if any(sql_upper.startswith(kw) for kw in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER']):
                    return "", 0.0
            
            return sql, 0.8
        
        except Exception as e:
            return f"-- Error: {e}", 0.0


# Tool registrations
@tool(
    name="query_database",
    description="Run a SQL query on a database",
    risk_level=RiskLevel.MEDIUM,
    category="code",
    examples=["query database for all users", "select from orders table"],
)
def query_database(query: str, db_path: str, limit: int = 50) -> ToolResult:
    """Execute SQL query."""
    try:
        db = DatabaseManager()
        db.connect(db_path)
        
        result = db.execute_query(query, limit=limit)
        db.close()
        
        if not result.success:
            return ToolResult(success=False, error=result.error)
        
        # Format results
        output = {
            "columns": result.columns,
            "rows": [list(row) for row in result.rows[:20]],
            "total_rows": result.row_count,
        }
        
        return ToolResult(success=True, output=output)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="show_tables",
    description="Show tables in a database",
    category="code",
)
def show_tables(db_path: str) -> ToolResult:
    """List database tables."""
    try:
        db = DatabaseManager()
        db.connect(db_path)
        
        tables = db.get_tables()
        
        result = []
        for table in tables:
            info = db.get_table_info(table)
            result.append({
                "name": table,
                "columns": len(info.columns),
                "rows": info.row_count,
            })
        
        db.close()
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="describe_table",
    description="Show structure of a database table",
    category="code",
)
def describe_table(table_name: str, db_path: str) -> ToolResult:
    """Describe table structure."""
    try:
        db = DatabaseManager()
        db.connect(db_path)
        
        info = db.get_table_info(table_name)
        db.close()
        
        return ToolResult(
            success=True,
            output={
                "name": info.name,
                "columns": info.columns,
                "rows": info.row_count,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="ask_database",
    description="Ask a question about database data in natural language",
    category="code",
    examples=["how many users are there?", "what are the top 5 products by sales?"],
)
def ask_database(question: str, db_path: str) -> ToolResult:
    """Natural language query."""
    try:
        db = DatabaseManager()
        db.connect(db_path)
        
        schema = db.get_schema()
        nl2sql = NL2SQL(schema)
        
        sql, confidence = nl2sql.generate_query(question)
        
        if not sql or confidence < 0.5:
            db.close()
            return ToolResult(
                success=False,
                error="Could not generate query from question",
            )
        
        result = db.execute_query(sql, limit=20)
        db.close()
        
        if not result.success:
            return ToolResult(
                success=False,
                error=f"Query failed: {result.error}\nGenerated SQL: {sql}",
            )
        
        return ToolResult(
            success=True,
            output={
                "question": question,
                "sql": sql,
                "columns": result.columns,
                "rows": [list(row) for row in result.rows],
                "row_count": result.row_count,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Database Tools...")
    
    # Create test database
    test_db = "test_db.sqlite"
    conn = sqlite3.connect(test_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            created_at TEXT
        )
    """)
    conn.execute("INSERT OR IGNORE INTO users VALUES (1, 'Alice', 'alice@test.com', '2024-01-01')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (2, 'Bob', 'bob@test.com', '2024-01-02')")
    conn.commit()
    conn.close()
    
    # Test database manager
    db = DatabaseManager()
    db.connect(test_db)
    
    print("\nTables:", db.get_tables())
    
    info = db.get_table_info("users")
    print(f"\nTable 'users': {info.row_count} rows")
    for col in info.columns:
        print(f"  - {col['name']}: {col['type']}")
    
    result = db.execute_query("SELECT * FROM users")
    print(f"\nQuery results: {result.row_count} rows")
    for row in result.rows:
        print(f"  {dict(row)}")
    
    db.close()
    
    # Cleanup
    os.remove(test_db)
    print("\nTests complete!")
