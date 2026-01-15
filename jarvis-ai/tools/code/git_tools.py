"""
JARVIS Git Tools - Version control integration.

Provides Git operations like status, commit, diff, and history.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

try:
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from tools.registry import tool, ToolResult, RiskLevel


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str
    is_dirty: bool
    staged: List[str]
    modified: List[str]
    untracked: List[str]
    ahead: int = 0
    behind: int = 0


@dataclass
class CommitInfo:
    """Git commit information."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    files_changed: int = 0


class GitManager:
    """
    Git repository manager.
    
    Provides easy access to common Git operations.
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize Git manager.
        
        Args:
            repo_path: Path to repository (uses cwd if None)
        """
        if not GIT_AVAILABLE:
            raise RuntimeError("GitPython not installed. Run: pip install gitpython")
        
        self.repo_path = repo_path or os.getcwd()
        self.repo = None
        self._init_repo()
    
    def _init_repo(self):
        """Initialize repository connection."""
        try:
            self.repo = Repo(self.repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            self.repo = None
    
    @property
    def is_valid(self) -> bool:
        """Check if repository is valid."""
        return self.repo is not None
    
    def get_status(self) -> GitStatus:
        """Get repository status."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        # Get staged files
        staged = [item.a_path for item in self.repo.index.diff("HEAD")]
        
        # Get modified files
        modified = [item.a_path for item in self.repo.index.diff(None)]
        
        # Get untracked files
        untracked = self.repo.untracked_files
        
        # Get branch info
        branch = self.repo.active_branch.name
        
        # Get ahead/behind counts
        ahead, behind = 0, 0
        try:
            tracking = self.repo.active_branch.tracking_branch()
            if tracking:
                commits_behind = list(self.repo.iter_commits(f'{branch}..{tracking.name}'))
                commits_ahead = list(self.repo.iter_commits(f'{tracking.name}..{branch}'))
                ahead = len(commits_ahead)
                behind = len(commits_behind)
        except:
            pass
        
        return GitStatus(
            branch=branch,
            is_dirty=self.repo.is_dirty(),
            staged=staged,
            modified=modified,
            untracked=untracked,
            ahead=ahead,
            behind=behind,
        )
    
    def get_log(self, limit: int = 10) -> List[CommitInfo]:
        """Get commit history."""
        if not self.is_valid:
            return []
        
        commits = []
        for commit in list(self.repo.iter_commits())[:limit]:
            commits.append(CommitInfo(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:7],
                message=commit.message.strip().split('\n')[0],
                author=commit.author.name,
                date=commit.committed_datetime.strftime("%Y-%m-%d %H:%M"),
                files_changed=len(commit.stats.files),
            ))
        
        return commits
    
    def get_diff(self, staged: bool = False) -> str:
        """Get diff of changes."""
        if not self.is_valid:
            return ""
        
        if staged:
            diff = self.repo.git.diff('--staged')
        else:
            diff = self.repo.git.diff()
        
        return diff
    
    def stage_files(self, files: List[str] = None):
        """Stage files for commit."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        if files:
            self.repo.index.add(files)
        else:
            # Stage all changes
            self.repo.git.add('-A')
    
    def commit(self, message: str) -> str:
        """Create a commit."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        commit = self.repo.index.commit(message)
        return commit.hexsha[:7]
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        if not self.is_valid:
            return ""
        return self.repo.active_branch.name
    
    def get_branches(self) -> List[str]:
        """Get list of branches."""
        if not self.is_valid:
            return []
        return [branch.name for branch in self.repo.branches]
    
    def checkout_branch(self, branch: str, create: bool = False):
        """Switch to a branch."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        if create:
            self.repo.create_head(branch)
        
        self.repo.heads[branch].checkout()
    
    def pull(self) -> str:
        """Pull from remote."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        origin = self.repo.remotes.origin
        result = origin.pull()
        return str(result)
    
    def push(self) -> str:
        """Push to remote."""
        if not self.is_valid:
            raise ValueError("Not a valid Git repository")
        
        origin = self.repo.remotes.origin
        result = origin.push()
        return str(result)


# Tool registrations
@tool(
    name="git_status",
    description="Get Git repository status",
    category="code",
    examples=["git status", "show git status"],
)
def git_status(path: Optional[str] = None) -> ToolResult:
    """Get Git status."""
    try:
        git = GitManager(path)
        if not git.is_valid:
            return ToolResult(success=False, error="Not a Git repository")
        
        status = git.get_status()
        
        return ToolResult(
            success=True,
            output={
                "branch": status.branch,
                "dirty": status.is_dirty,
                "staged": len(status.staged),
                "modified": len(status.modified),
                "untracked": len(status.untracked),
                "ahead": status.ahead,
                "behind": status.behind,
                "staged_files": status.staged[:5],
                "modified_files": status.modified[:5],
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_log",
    description="Show Git commit history",
    category="code",
    examples=["git log", "show recent commits"],
)
def git_log(limit: int = 5, path: Optional[str] = None) -> ToolResult:
    """Get Git log."""
    try:
        git = GitManager(path)
        if not git.is_valid:
            return ToolResult(success=False, error="Not a Git repository")
        
        commits = git.get_log(limit=limit)
        
        return ToolResult(
            success=True,
            output=[
                {
                    "hash": c.short_hash,
                    "message": c.message[:50],
                    "author": c.author,
                    "date": c.date,
                }
                for c in commits
            ],
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_diff",
    description="Show Git diff of changes",
    category="code",
    examples=["git diff", "show changes"],
)
def git_diff(staged: bool = False, path: Optional[str] = None) -> ToolResult:
    """Get Git diff."""
    try:
        git = GitManager(path)
        if not git.is_valid:
            return ToolResult(success=False, error="Not a Git repository")
        
        diff = git.get_diff(staged=staged)
        
        if not diff:
            return ToolResult(success=True, output="No changes")
        
        # Truncate if too long
        if len(diff) > 5000:
            diff = diff[:5000] + "\n... (truncated)"
        
        return ToolResult(success=True, output=diff)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_commit",
    description="Create a Git commit",
    risk_level=RiskLevel.MEDIUM,
    category="code",
    examples=["git commit with message 'fix bug'", "commit changes"],
)
def git_commit(message: str, path: Optional[str] = None) -> ToolResult:
    """Create a commit."""
    try:
        git = GitManager(path)
        if not git.is_valid:
            return ToolResult(success=False, error="Not a Git repository")
        
        # Stage all changes first
        git.stage_files()
        
        commit_hash = git.commit(message)
        
        return ToolResult(
            success=True,
            output=f"Created commit {commit_hash}: {message}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_branch",
    description="List or switch Git branches",
    category="code",
)
def git_branch(
    switch_to: Optional[str] = None,
    create: bool = False,
    path: Optional[str] = None,
) -> ToolResult:
    """Manage branches."""
    try:
        git = GitManager(path)
        if not git.is_valid:
            return ToolResult(success=False, error="Not a Git repository")
        
        if switch_to:
            git.checkout_branch(switch_to, create=create)
            return ToolResult(success=True, output=f"Switched to branch: {switch_to}")
        
        branches = git.get_branches()
        current = git.get_current_branch()
        
        return ToolResult(
            success=True,
            output={
                "current": current,
                "branches": branches,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing Git Tools...")
    
    if not GIT_AVAILABLE:
        print("GitPython not installed")
    else:
        try:
            git = GitManager()
            if git.is_valid:
                status = git.get_status()
                print(f"Branch: {status.branch}")
                print(f"Dirty: {status.is_dirty}")
                print(f"Modified: {len(status.modified)}")
                
                commits = git.get_log(limit=3)
                print("\nRecent commits:")
                for c in commits:
                    print(f"  {c.short_hash} - {c.message[:40]}")
            else:
                print("Not a Git repository")
        except Exception as e:
            print(f"Error: {e}")
