"""
JARVIS Documentation Generator - Auto-generate code documentation.

Uses AI to generate docstrings, README files, and API documentation.
"""

import os
import ast
from typing import Optional, List, Dict, Any
from pathlib import Path

from tools.registry import tool, ToolResult


class DocGenerator:
    """
    Generate documentation for code.
    
    Supports:
    - Function docstrings
    - Class documentation
    - README generation
    - API documentation
    """
    
    def __init__(self):
        self.llm = None
    
    def _get_llm(self):
        """Lazy load LLM client."""
        if self.llm is None:
            from ai.llm import LLMClient
            self.llm = LLMClient()
        return self.llm
    
    def generate_docstring(
        self,
        code: str,
        style: str = "google",
    ) -> str:
        """
        Generate docstring for a function or class.
        
        Args:
            code: Function or class code
            style: Docstring style (google, numpy, sphinx)
            
        Returns:
            Generated docstring
        """
        styles = {
            "google": "Google-style docstrings with Args, Returns, Raises sections",
            "numpy": "NumPy-style docstrings with Parameters, Returns sections",
            "sphinx": "Sphinx-style docstrings with :param and :return:",
        }
        
        style_desc = styles.get(style, styles["google"])
        
        prompt = f"""Generate a {style_desc} for this Python code:

```python
{code}
```

Return ONLY the docstring content (without the triple quotes).
Be concise but comprehensive."""

        llm = self._get_llm()
        response = llm.generate(prompt, temperature=0.3, max_tokens=300)
        
        return response.content.strip()
    
    def add_docstrings_to_file(
        self,
        filepath: str,
        style: str = "google",
    ) -> str:
        """
        Add docstrings to functions/classes in a file.
        
        Args:
            filepath: Path to Python file
            style: Docstring style
            
        Returns:
            Modified file content
        """
        with open(filepath, 'r') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in file: {e}")
        
        lines = content.splitlines(keepends=True)
        insertions = []  # (line_number, docstring)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Check if already has docstring
                if ast.get_docstring(node):
                    continue
                
                # Get the code for this node
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
                node_code = ''.join(lines[start:min(end, start + 15)])
                
                # Generate docstring
                docstring = self.generate_docstring(node_code, style)
                
                # Calculate insertion point (after the def/class line)
                insert_line = node.lineno
                
                # Get indentation
                first_line = lines[start]
                base_indent = len(first_line) - len(first_line.lstrip())
                indent = ' ' * (base_indent + 4)
                
                # Format docstring
                formatted = f'{indent}"""{docstring}"""\n'
                
                insertions.append((insert_line, formatted))
        
        # Apply insertions in reverse order to maintain line numbers
        for line_num, docstring in sorted(insertions, reverse=True):
            lines.insert(line_num, docstring)
        
        return ''.join(lines)
    
    def generate_readme(
        self,
        project_path: str,
        sections: List[str] = None,
    ) -> str:
        """
        Generate README.md for a project.
        
        Args:
            project_path: Path to project root
            sections: Sections to include
            
        Returns:
            README content
        """
        sections = sections or [
            "description", "installation", "usage", "features", "license"
        ]
        
        # Gather project info
        project_info = self._analyze_project(project_path)
        
        prompt = f"""Generate a README.md for this project:

Project Name: {project_info['name']}
Main Files: {', '.join(project_info['files'][:10])}
Dependencies: {', '.join(project_info['dependencies'][:10])}
Has setup.py: {project_info['has_setup']}
Has tests: {project_info['has_tests']}

Include these sections: {', '.join(sections)}

Make it professional and well-formatted with proper markdown."""

        llm = self._get_llm()
        response = llm.generate(prompt, temperature=0.5, max_tokens=800)
        
        return response.content
    
    def _analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze project structure."""
        path = Path(project_path)
        
        # Get project name
        name = path.name
        
        # Get Python files
        files = [f.name for f in path.rglob('*.py') if not f.name.startswith('_')][:20]
        
        # Get dependencies from requirements.txt
        dependencies = []
        req_file = path / 'requirements.txt'
        if req_file.exists():
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dependencies.append(line.split('>=')[0].split('==')[0])
        
        return {
            'name': name,
            'files': files,
            'dependencies': dependencies,
            'has_setup': (path / 'setup.py').exists(),
            'has_tests': (path / 'tests').exists() or (path / 'test').exists(),
        }


# Tool registrations
@tool(
    name="generate_docstring",
    description="Generate a docstring for a function or class",
    category="code",
)
def generate_docstring(
    code: str,
    style: str = "google",
) -> ToolResult:
    """Generate docstring for code."""
    try:
        generator = DocGenerator()
        docstring = generator.generate_docstring(code, style)
        
        return ToolResult(
            success=True,
            output={
                "docstring": docstring,
                "style": style,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="generate_readme",
    description="Generate a README.md for a project",
    category="code",
)
def generate_readme(project_path: str) -> ToolResult:
    """Generate README."""
    try:
        generator = DocGenerator()
        readme = generator.generate_readme(project_path)
        
        return ToolResult(success=True, output=readme)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="document_file",
    description="Add docstrings to all functions in a Python file",
    category="code",
)
def document_file(filepath: str, style: str = "google") -> ToolResult:
    """Add docstrings to file."""
    try:
        generator = DocGenerator()
        new_content = generator.add_docstrings_to_file(filepath, style)
        
        # Show preview (first 2000 chars)
        preview = new_content[:2000]
        if len(new_content) > 2000:
            preview += "\n... (truncated)"
        
        return ToolResult(
            success=True,
            output={
                "preview": preview,
                "message": "Use 'write_file' to save the documented version",
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Documentation Generator...")
    
    # Test docstring generation
    test_code = '''
def calculate_area(length: float, width: float) -> float:
    if length <= 0 or width <= 0:
        raise ValueError("Dimensions must be positive")
    return length * width
'''
    
    print("\nTest code:")
    print(test_code)
    
    generator = DocGenerator()
    
    try:
        docstring = generator.generate_docstring(test_code)
        print("\nGenerated docstring:")
        print(docstring)
    except Exception as e:
        print(f"Error (LLM may not be available): {e}")
    
    print("\nTests complete!")
