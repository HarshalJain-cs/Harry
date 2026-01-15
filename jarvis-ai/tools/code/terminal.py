"""
JARVIS Terminal Emulator - Shell command execution.

Provides terminal/shell access with output capturing and history.
"""

import os
import subprocess
import threading
import queue
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from datetime import datetime

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class CommandResult:
    """Result of a shell command."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: str


class TerminalEmulator:
    """
    Terminal/Shell emulator with session support.
    
    Provides:
    - Command execution with timeout
    - Output capturing
    - Command history
    - Working directory management
    """
    
    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: float = 30.0,
        shell: bool = True,
    ):
        """
        Initialize terminal emulator.
        
        Args:
            working_dir: Initial working directory
            timeout: Default command timeout
            shell: Use shell for commands
        """
        self.working_dir = working_dir or os.getcwd()
        self.timeout = timeout
        self.use_shell = shell
        self.history: List[CommandResult] = []
        self.env = os.environ.copy()
    
    def run(
        self,
        command: str,
        timeout: Optional[float] = None,
        capture: bool = True,
    ) -> CommandResult:
        """
        Execute a shell command.
        
        Args:
            command: Command to execute
            timeout: Command timeout (uses default if None)
            capture: Whether to capture output
            
        Returns:
            CommandResult with output and status
        """
        import time
        start_time = time.time()
        
        effective_timeout = timeout or self.timeout
        
        try:
            result = subprocess.run(
                command,
                shell=self.use_shell,
                cwd=self.working_dir,
                env=self.env,
                capture_output=capture,
                text=True,
                timeout=effective_timeout,
            )
            
            exec_time = time.time() - start_time
            
            cmd_result = CommandResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                execution_time=exec_time,
                timestamp=datetime.now().isoformat(),
            )
            
        except subprocess.TimeoutExpired:
            cmd_result = CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {effective_timeout}s",
                execution_time=effective_timeout,
                timestamp=datetime.now().isoformat(),
            )
        
        except Exception as e:
            cmd_result = CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
            )
        
        self.history.append(cmd_result)
        return cmd_result
    
    def run_async(
        self,
        command: str,
        callback: Optional[Callable[[str], None]] = None,
    ) -> threading.Thread:
        """
        Execute command asynchronously.
        
        Args:
            command: Command to execute
            callback: Function to call with each output line
            
        Returns:
            Thread running the command
        """
        def run_command():
            process = subprocess.Popen(
                command,
                shell=self.use_shell,
                cwd=self.working_dir,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            
            for line in process.stdout:
                if callback:
                    callback(line.strip())
            
            process.wait()
        
        thread = threading.Thread(target=run_command)
        thread.start()
        return thread
    
    def cd(self, path: str):
        """Change working directory."""
        if os.path.isabs(path):
            new_path = path
        else:
            new_path = os.path.join(self.working_dir, path)
        
        if os.path.isdir(new_path):
            self.working_dir = os.path.abspath(new_path)
        else:
            raise ValueError(f"Directory not found: {path}")
    
    def pwd(self) -> str:
        """Get current working directory."""
        return self.working_dir
    
    def set_env(self, key: str, value: str):
        """Set environment variable."""
        self.env[key] = value
    
    def get_env(self, key: str) -> Optional[str]:
        """Get environment variable."""
        return self.env.get(key)
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get command history."""
        return [
            {
                "command": cmd.command,
                "success": cmd.return_code == 0,
                "time": cmd.execution_time,
            }
            for cmd in self.history[-limit:]
        ]
    
    def clear_history(self):
        """Clear command history."""
        self.history.clear()


# Global terminal instance
_terminal: Optional[TerminalEmulator] = None


def get_terminal() -> TerminalEmulator:
    """Get or create global terminal instance."""
    global _terminal
    if _terminal is None:
        _terminal = TerminalEmulator()
    return _terminal


# Tool registrations
@tool(
    name="run_shell",
    description="Run a shell/terminal command",
    risk_level=RiskLevel.HIGH,
    category="code",
    examples=["run command dir", "execute ls -la"],
)
def run_shell(command: str, timeout: int = 30) -> ToolResult:
    """Run shell command."""
    terminal = get_terminal()
    result = terminal.run(command, timeout=timeout)
    
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    
    # Truncate if too long
    if len(output) > 5000:
        output = output[:5000] + "\n... (output truncated)"
    
    return ToolResult(
        success=result.return_code == 0,
        output=output if output else "(no output)",
        error=result.stderr if result.return_code != 0 else None,
    )


@tool(
    name="terminal_cd",
    description="Change terminal working directory",
    category="code",
)
def terminal_cd(path: str) -> ToolResult:
    """Change directory."""
    try:
        terminal = get_terminal()
        terminal.cd(path)
        return ToolResult(success=True, output=f"Changed to: {terminal.pwd()}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="terminal_pwd",
    description="Show current working directory",
    category="code",
)
def terminal_pwd() -> ToolResult:
    """Get current directory."""
    terminal = get_terminal()
    return ToolResult(success=True, output=terminal.pwd())


@tool(
    name="list_files",
    description="List files in directory",
    category="code",
    examples=["list files", "show directory contents"],
)
def list_files(path: Optional[str] = None, show_hidden: bool = False) -> ToolResult:
    """List files in directory."""
    try:
        target = path or get_terminal().pwd()
        
        entries = []
        for entry in os.scandir(target):
            if not show_hidden and entry.name.startswith('.'):
                continue
            
            info = {
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
            }
            
            if entry.is_file():
                info["size"] = entry.stat().st_size
            
            entries.append(info)
        
        # Sort: directories first, then files
        entries.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
        
        return ToolResult(success=True, output=entries)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="read_file",
    description="Read contents of a file",
    category="code",
    examples=["read file config.json", "show contents of readme.md"],
)
def read_file(path: str, lines: Optional[int] = None) -> ToolResult:
    """Read file contents."""
    try:
        terminal = get_terminal()
        
        if not os.path.isabs(path):
            path = os.path.join(terminal.pwd(), path)
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            if lines:
                content = ''.join(f.readlines()[:lines])
            else:
                content = f.read()
        
        # Truncate if too large
        if len(content) > 10000:
            content = content[:10000] + "\n... (file truncated)"
        
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="write_file",
    description="Write content to a file",
    risk_level=RiskLevel.HIGH,
    category="code",
)
def write_file(path: str, content: str, append: bool = False) -> ToolResult:
    """Write to file."""
    try:
        terminal = get_terminal()
        
        if not os.path.isabs(path):
            path = os.path.join(terminal.pwd(), path)
        
        mode = 'a' if append else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "Appended to" if append else "Wrote to"
        return ToolResult(success=True, output=f"{action}: {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Terminal Emulator...")
    
    terminal = TerminalEmulator()
    
    # Test basic command
    print("\n1. Directory listing:")
    result = terminal.run("dir" if os.name == 'nt' else "ls -la")
    print(f"   Return code: {result.return_code}")
    print(f"   Time: {result.execution_time:.3f}s")
    print(f"   Output lines: {len(result.stdout.splitlines())}")
    
    # Test pwd
    print(f"\n2. Current directory: {terminal.pwd()}")
    
    # Test history
    print(f"\n3. History:")
    for cmd in terminal.get_history():
        print(f"   - {cmd['command'][:30]} (success: {cmd['success']})")
    
    print("\nTests complete!")
