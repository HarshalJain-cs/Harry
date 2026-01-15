"""
JARVIS Code Analyzer - Static code analysis and understanding.

Provides tools for analyzing code structure, finding issues,
and generating documentation.
"""

import os
import ast
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from tools.registry import tool, ToolResult


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    args: List[str]
    docstring: Optional[str]
    line_start: int
    line_end: int
    complexity: int = 0


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    bases: List[str]
    docstring: Optional[str]
    methods: List[str]
    line_start: int
    line_end: int


@dataclass
class FileAnalysis:
    """Analysis result for a file."""
    path: str
    language: str
    lines: int
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]
    todos: List[str]
    complexity: int


class CodeAnalyzer:
    """
    Analyze code structure and quality.
    
    Supports:
    - Python code parsing
    - Function/class extraction
    - Complexity analysis
    - TODO/FIXME detection
    """
    
    LANGUAGE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rb': 'ruby',
        '.rs': 'rust',
        '.php': 'php',
    }
    
    def __init__(self):
        self.cache = {}
    
    def detect_language(self, filepath: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(filepath).suffix.lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, 'unknown')
    
    def analyze_file(self, filepath: str) -> FileAnalysis:
        """Analyze a source file."""
        language = self.detect_language(filepath)
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        lines = len(content.splitlines())
        
        if language == 'python':
            return self._analyze_python(filepath, content, lines)
        else:
            return self._analyze_generic(filepath, content, lines, language)
    
    def _analyze_python(
        self,
        filepath: str,
        content: str,
        lines: int,
    ) -> FileAnalysis:
        """Analyze Python code using AST."""
        functions = []
        classes = []
        imports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Extract functions
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    docstring = ast.get_docstring(node)
                    
                    # Calculate cyclomatic complexity
                    complexity = self._calculate_complexity(node)
                    
                    functions.append(FunctionInfo(
                        name=node.name,
                        args=args,
                        docstring=docstring,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        complexity=complexity,
                    ))
                
                # Extract classes
                elif isinstance(node, ast.ClassDef):
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(base.attr)
                    
                    methods = [
                        n.name for n in node.body
                        if isinstance(n, ast.FunctionDef)
                    ]
                    
                    classes.append(ClassInfo(
                        name=node.name,
                        bases=bases,
                        docstring=ast.get_docstring(node),
                        methods=methods,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                    ))
                
                # Extract imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        
        except SyntaxError:
            pass
        
        # Find TODOs
        todos = self._find_todos(content)
        
        # Calculate total complexity
        total_complexity = sum(f.complexity for f in functions)
        
        return FileAnalysis(
            path=filepath,
            language='python',
            lines=lines,
            functions=functions,
            classes=classes,
            imports=imports,
            todos=todos,
            complexity=total_complexity,
        )
    
    def _analyze_generic(
        self,
        filepath: str,
        content: str,
        lines: int,
        language: str,
    ) -> FileAnalysis:
        """Generic analysis using regex patterns."""
        functions = []
        classes = []
        
        # Simple function detection patterns
        patterns = {
            'javascript': r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))',
            'typescript': r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))',
            'java': r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{',
            'cpp': r'\w+(?:\s*\*)*\s+(\w+)\s*\([^)]*\)\s*\{',
        }
        
        pattern = patterns.get(language)
        if pattern:
            for match in re.finditer(pattern, content):
                name = match.group(1) or match.group(2)
                if name:
                    functions.append(FunctionInfo(
                        name=name,
                        args=[],
                        docstring=None,
                        line_start=content[:match.start()].count('\n') + 1,
                        line_end=0,
                    ))
        
        todos = self._find_todos(content)
        
        return FileAnalysis(
            path=filepath,
            language=language,
            lines=lines,
            functions=functions,
            classes=classes,
            imports=[],
            todos=todos,
            complexity=0,
        )
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _find_todos(self, content: str) -> List[str]:
        """Find TODO and FIXME comments."""
        todos = []
        pattern = r'(?:#|//|/\*)\s*(TODO|FIXME|XXX|HACK)[\s:]+(.+?)(?:\*/|$)'
        
        for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
            todos.append(f"{match.group(1)}: {match.group(2).strip()}")
        
        return todos
    
    def get_summary(self, analysis: FileAnalysis) -> Dict[str, Any]:
        """Get a summary of the analysis."""
        return {
            "language": analysis.language,
            "lines": analysis.lines,
            "functions": len(analysis.functions),
            "classes": len(analysis.classes),
            "imports": len(analysis.imports),
            "todos": len(analysis.todos),
            "complexity": analysis.complexity,
        }


# Tool registrations
@tool(
    name="analyze_code",
    description="Analyze a source code file",
    category="code",
    examples=["analyze code in main.py", "show functions in script.py"],
)
def analyze_code(path: str) -> ToolResult:
    """Analyze source code file."""
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, error=f"File not found: {path}")
        
        analyzer = CodeAnalyzer()
        analysis = analyzer.analyze_file(path)
        summary = analyzer.get_summary(analysis)
        
        # Add function details
        summary["function_list"] = [
            {"name": f.name, "args": f.args, "complexity": f.complexity}
            for f in analysis.functions[:10]
        ]
        
        summary["class_list"] = [
            {"name": c.name, "methods": c.methods[:5]}
            for c in analysis.classes[:5]
        ]
        
        if analysis.todos:
            summary["todo_list"] = analysis.todos[:5]
        
        return ToolResult(success=True, output=summary)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_function",
    description="Find a function definition in code",
    category="code",
)
def find_function(name: str, path: str) -> ToolResult:
    """Find function by name."""
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, error=f"File not found: {path}")
        
        analyzer = CodeAnalyzer()
        analysis = analyzer.analyze_file(path)
        
        for func in analysis.functions:
            if func.name == name or name in func.name:
                with open(path, 'r') as f:
                    lines = f.readlines()
                
                start = max(0, func.line_start - 1)
                end = min(len(lines), func.line_end)
                code = ''.join(lines[start:end])
                
                return ToolResult(
                    success=True,
                    output={
                        "name": func.name,
                        "args": func.args,
                        "docstring": func.docstring,
                        "lines": f"{func.line_start}-{func.line_end}",
                        "code": code[:2000],
                    },
                )
        
        return ToolResult(success=False, error=f"Function '{name}' not found")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="explain_code",
    description="Explain what code does using AI",
    category="code",
)
def explain_code(path: str, lines: Optional[str] = None) -> ToolResult:
    """Explain code using LLM."""
    try:
        from ai.llm import LLMClient
        
        if not os.path.exists(path):
            return ToolResult(success=False, error=f"File not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if lines:
            # Parse line range (e.g., "10-20")
            parts = lines.split('-')
            start = int(parts[0]) - 1
            end = int(parts[1]) if len(parts) > 1 else start + 1
            content_lines = content.splitlines()
            content = '\n'.join(content_lines[start:end])
        
        # Truncate if too long
        if len(content) > 3000:
            content = content[:3000] + "\n... (truncated)"
        
        llm = LLMClient()
        response = llm.generate(
            prompt=f"Explain what this code does in simple terms:\n\n```\n{content}\n```",
            system_prompt="You are a helpful code explainer. Give clear, concise explanations.",
            max_tokens=300,
        )
        
        return ToolResult(success=True, output=response.content)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Code Analyzer...")
    
    analyzer = CodeAnalyzer()
    
    # Analyze this file
    analysis = analyzer.analyze_file(__file__)
    summary = analyzer.get_summary(analysis)
    
    print(f"\nFile: {analysis.path}")
    print(f"Language: {summary['language']}")
    print(f"Lines: {summary['lines']}")
    print(f"Functions: {summary['functions']}")
    print(f"Classes: {summary['classes']}")
    print(f"Complexity: {summary['complexity']}")
    
    print("\nFunctions:")
    for f in analysis.functions[:5]:
        print(f"  - {f.name}({', '.join(f.args)}) [complexity: {f.complexity}]")
    
    print("\nTests complete!")
