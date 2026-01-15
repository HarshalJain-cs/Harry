"""
JARVIS Code Interpreter - Safe Python code execution.

Provides a sandboxed environment for executing Python code snippets
with restricted access and timeout protection.
"""

import sys
import ast
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from io import StringIO
import contextlib
import threading
import queue

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    variables: Dict[str, Any] = None
    execution_time: float = 0.0


class SafeExecutor:
    """Execute code with safety restrictions."""
    
    # Allowed built-in functions
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'ascii': ascii,
        'bin': bin, 'bool': bool, 'bytes': bytes, 'callable': callable,
        'chr': chr, 'dict': dict, 'dir': dir, 'divmod': divmod,
        'enumerate': enumerate, 'filter': filter, 'float': float,
        'format': format, 'frozenset': frozenset, 'getattr': getattr,
        'hasattr': hasattr, 'hash': hash, 'hex': hex, 'id': id,
        'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
        'iter': iter, 'len': len, 'list': list, 'map': map,
        'max': max, 'min': min, 'next': next, 'object': object,
        'oct': oct, 'ord': ord, 'pow': pow, 'print': print,
        'range': range, 'repr': repr, 'reversed': reversed, 'round': round,
        'set': set, 'slice': slice, 'sorted': sorted, 'str': str,
        'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
    }
    
    # Allowed module imports
    SAFE_MODULES = {
        'math', 'datetime', 'json', 'random', 're', 
        'collections', 'itertools', 'functools', 'string',
        'statistics', 'decimal', 'fractions',
    }
    
    # Blocked patterns
    BLOCKED_PATTERNS = [
        'import os', 'import sys', 'import subprocess',
        'import shutil', '__import__', 'eval(', 'exec(',
        'compile(', 'open(', 'file(', 'input(',
        '__builtins__', '__code__', '__globals__',
    ]
    
    def __init__(self, timeout: float = 5.0, max_output: int = 10000):
        self.timeout = timeout
        self.max_output = max_output
        self.local_vars = {}
    
    def validate_code(self, code: str) -> tuple[bool, str]:
        """Validate code for safety."""
        # Check for blocked patterns
        code_lower = code.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.lower() in code_lower:
                return False, f"Blocked pattern detected: {pattern}"
        
        # Try to parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # Check for dangerous nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] not in self.SAFE_MODULES:
                        return False, f"Import not allowed: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] not in self.SAFE_MODULES:
                    return False, f"Import not allowed: {node.module}"
        
        return True, "OK"
    
    def execute(self, code: str) -> ExecutionResult:
        """Execute code safely with timeout."""
        import time
        start_time = time.time()
        
        # Validate code
        is_valid, message = self.validate_code(code)
        if not is_valid:
            return ExecutionResult(
                success=False,
                output="",
                error=message,
            )
        
        # Prepare safe globals
        safe_globals = {
            '__builtins__': self.SAFE_BUILTINS,
            '__name__': '__main__',
        }
        
        # Add safe imports
        import math, datetime, json, random, re
        import collections, itertools, functools, string
        safe_globals.update({
            'math': math,
            'datetime': datetime,
            'json': json,
            'random': random,
            're': re,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            'string': string,
        })
        
        # Capture output
        output_buffer = StringIO()
        result_queue = queue.Queue()
        
        def run_code():
            try:
                with contextlib.redirect_stdout(output_buffer):
                    with contextlib.redirect_stderr(output_buffer):
                        exec(code, safe_globals, self.local_vars)
                result_queue.put(('success', None))
            except Exception as e:
                result_queue.put(('error', str(e)))
        
        # Run with timeout
        thread = threading.Thread(target=run_code)
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.timeout}s",
            )
        
        # Get result
        output = output_buffer.getvalue()
        if len(output) > self.max_output:
            output = output[:self.max_output] + "\n... (output truncated)"
        
        exec_time = time.time() - start_time
        
        try:
            status, error = result_queue.get_nowait()
        except queue.Empty:
            status, error = 'error', 'Unknown error'
        
        return ExecutionResult(
            success=(status == 'success'),
            output=output,
            error=error,
            variables={k: repr(v)[:100] for k, v in self.local_vars.items()},
            execution_time=exec_time,
        )


class CodeInterpreter:
    """
    Interactive code interpreter with session support.
    
    Maintains state between executions within a session.
    """
    
    def __init__(self, timeout: float = 5.0):
        self.executor = SafeExecutor(timeout=timeout)
        self.history: List[tuple[str, ExecutionResult]] = []
    
    def run(self, code: str) -> ExecutionResult:
        """Execute code and store in history."""
        result = self.executor.execute(code)
        self.history.append((code, result))
        return result
    
    def reset(self):
        """Reset interpreter state."""
        self.executor.local_vars.clear()
        self.history.clear()
    
    def get_variables(self) -> Dict[str, str]:
        """Get current variables."""
        return {k: repr(v)[:200] for k, v in self.executor.local_vars.items()}
    
    def get_history(self, limit: int = 10) -> List[tuple[str, bool]]:
        """Get execution history."""
        return [(code, result.success) for code, result in self.history[-limit:]]


# Tool registrations
@tool(
    name="run_python",
    description="Execute Python code safely",
    risk_level=RiskLevel.MEDIUM,
    category="code",
    examples=["run python print(2+2)", "execute code for i in range(5): print(i)"],
)
def run_python(code: str) -> ToolResult:
    """Run Python code in sandbox."""
    interpreter = CodeInterpreter()
    result = interpreter.run(code)
    
    if result.success:
        return ToolResult(
            success=True,
            output={
                "output": result.output or "(no output)",
                "variables": result.variables,
                "time": f"{result.execution_time:.3f}s",
            },
        )
    else:
        return ToolResult(
            success=False,
            error=result.error,
            output=result.output,
        )


@tool(
    name="calculate",
    description="Evaluate a mathematical expression",
    category="code",
    examples=["calculate 2+2", "what is 15*3"],
)
def calculate(expression: str) -> ToolResult:
    """Evaluate math expression."""
    import math
    
    # Clean expression
    expr = expression.replace('^', '**')
    
    # Safe evaluation context
    safe_dict = {
        'abs': abs, 'round': round, 'min': min, 'max': max,
        'sum': sum, 'pow': pow,
        'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
        'tan': math.tan, 'log': math.log, 'log10': math.log10,
        'pi': math.pi, 'e': math.e,
    }
    
    try:
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        return ToolResult(
            success=True,
            output={"expression": expression, "result": result},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Code Interpreter...")
    
    interpreter = CodeInterpreter()
    
    # Test basic execution
    print("\n1. Basic math:")
    result = interpreter.run("print(2 + 2)")
    print(f"   Output: {result.output}")
    
    # Test variables
    print("\n2. Variables:")
    result = interpreter.run("x = 10\ny = 20\nprint(x + y)")
    print(f"   Output: {result.output}")
    print(f"   Variables: {interpreter.get_variables()}")
    
    # Test loops
    print("\n3. Loop:")
    result = interpreter.run("for i in range(5): print(i, end=' ')")
    print(f"   Output: {result.output}")
    
    # Test blocked code
    print("\n4. Blocked import:")
    result = interpreter.run("import os")
    print(f"   Error: {result.error}")
    
    print("\nTests complete!")
