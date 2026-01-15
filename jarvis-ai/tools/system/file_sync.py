"""
JARVIS File Sync - File synchronization and backup.

Provides file watching, syncing, and backup capabilities.
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time


@dataclass
class SyncPair:
    """A source-destination sync pair."""
    id: str
    name: str
    source: str
    destination: str
    enabled: bool = True
    last_sync: Optional[datetime] = None
    auto_sync: bool = False
    sync_interval: int = 3600  # seconds


@dataclass
class FileChange:
    """A detected file change."""
    path: str
    change_type: str  # added, modified, deleted
    timestamp: datetime
    size: int = 0


class FileSyncManager:
    """
    File synchronization and backup manager.
    
    Features:
    - One-way sync
    - File watching
    - Backup with versioning
    - Change detection
    """
    
    def __init__(
        self,
        config_path: str = "./storage/file_sync.json",
    ):
        """
        Initialize file sync manager.
        
        Args:
            config_path: Path for sync configuration
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.sync_pairs: Dict[str, SyncPair] = {}
        self.file_hashes: Dict[str, Dict[str, str]] = {}
        
        self._watching = False
        self._watch_thread = None
        
        self._load()
    
    def _load(self):
        """Load sync configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for pair_data in data.get("pairs", []):
                    if pair_data.get('last_sync'):
                        pair_data['last_sync'] = datetime.fromisoformat(pair_data['last_sync'])
                    pair = SyncPair(**pair_data)
                    self.sync_pairs[pair.id] = pair
                
                self.file_hashes = data.get("hashes", {})
            except Exception:
                pass
    
    def _save(self):
        """Save configuration."""
        data = {
            "pairs": [
                {
                    **asdict(p),
                    "last_sync": p.last_sync.isoformat() if p.last_sync else None,
                }
                for p in self.sync_pairs.values()
            ],
            "hashes": self.file_hashes,
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get MD5 hash of file."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def add_sync_pair(
        self,
        name: str,
        source: str,
        destination: str,
        auto_sync: bool = False,
    ) -> SyncPair:
        """
        Add a sync pair.
        
        Args:
            name: Pair name
            source: Source directory
            destination: Destination directory
            auto_sync: Enable auto-sync
            
        Returns:
            SyncPair
        """
        pair = SyncPair(
            id=f"sync_{datetime.now().timestamp()}",
            name=name,
            source=str(Path(source).resolve()),
            destination=str(Path(destination).resolve()),
            auto_sync=auto_sync,
        )
        
        self.sync_pairs[pair.id] = pair
        self._save()
        
        return pair
    
    def remove_sync_pair(self, pair_id: str) -> bool:
        """Remove a sync pair."""
        if pair_id in self.sync_pairs:
            del self.sync_pairs[pair_id]
            self._save()
            return True
        return False
    
    def sync(self, pair_id: str, dry_run: bool = False) -> List[FileChange]:
        """
        Sync files from source to destination.
        
        Args:
            pair_id: Sync pair ID
            dry_run: Only detect changes, don't sync
            
        Returns:
            List of changes
        """
        if pair_id not in self.sync_pairs:
            return []
        
        pair = self.sync_pairs[pair_id]
        source = Path(pair.source)
        dest = Path(pair.destination)
        
        if not source.exists():
            return []
        
        dest.mkdir(parents=True, exist_ok=True)
        
        changes = []
        
        # Scan source files
        for src_file in source.rglob('*'):
            if src_file.is_file():
                rel_path = src_file.relative_to(source)
                dest_file = dest / rel_path
                
                # Check if file needs sync
                needs_sync = False
                change_type = "added"
                
                if not dest_file.exists():
                    needs_sync = True
                    change_type = "added"
                elif src_file.stat().st_mtime > dest_file.stat().st_mtime:
                    needs_sync = True
                    change_type = "modified"
                
                if needs_sync:
                    changes.append(FileChange(
                        path=str(rel_path),
                        change_type=change_type,
                        timestamp=datetime.now(),
                        size=src_file.stat().st_size,
                    ))
                    
                    if not dry_run:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)
        
        if not dry_run:
            pair.last_sync = datetime.now()
            self._save()
        
        return changes
    
    def sync_all(self, dry_run: bool = False) -> Dict[str, List[FileChange]]:
        """Sync all enabled pairs."""
        results = {}
        
        for pair_id, pair in self.sync_pairs.items():
            if pair.enabled:
                results[pair.name] = self.sync(pair_id, dry_run)
        
        return results
    
    def backup(
        self,
        source: str,
        backup_dir: str,
        max_versions: int = 5,
    ) -> str:
        """
        Create a timestamped backup.
        
        Args:
            source: Source file or directory
            backup_dir: Backup destination
            max_versions: Max backup versions to keep
            
        Returns:
            Backup path
        """
        source = Path(source)
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}_{timestamp}"
        backup_path = backup_dir / backup_name
        
        if source.is_file():
            shutil.copy2(source, backup_path)
        else:
            shutil.copytree(source, backup_path)
        
        # Cleanup old versions
        backups = sorted(backup_dir.glob(f"{source.name}_*"))
        while len(backups) > max_versions:
            old = backups.pop(0)
            if old.is_file():
                old.unlink()
            else:
                shutil.rmtree(old)
        
        return str(backup_path)
    
    def detect_changes(self, directory: str) -> List[FileChange]:
        """Detect file changes since last check."""
        directory = str(Path(directory).resolve())
        changes = []
        
        current_hashes = {}
        old_hashes = self.file_hashes.get(directory, {})
        
        for filepath in Path(directory).rglob('*'):
            if filepath.is_file():
                rel_path = str(filepath.relative_to(directory))
                file_hash = self._get_file_hash(str(filepath))
                current_hashes[rel_path] = file_hash
                
                if rel_path not in old_hashes:
                    changes.append(FileChange(
                        path=rel_path,
                        change_type="added",
                        timestamp=datetime.now(),
                        size=filepath.stat().st_size,
                    ))
                elif old_hashes[rel_path] != file_hash:
                    changes.append(FileChange(
                        path=rel_path,
                        change_type="modified",
                        timestamp=datetime.now(),
                        size=filepath.stat().st_size,
                    ))
        
        # Check for deleted files
        for rel_path in old_hashes:
            if rel_path not in current_hashes:
                changes.append(FileChange(
                    path=rel_path,
                    change_type="deleted",
                    timestamp=datetime.now(),
                ))
        
        self.file_hashes[directory] = current_hashes
        self._save()
        
        return changes


from tools.registry import tool, ToolResult


@tool(
    name="sync_files",
    description="Sync files between directories",
    category="files",
    examples=["sync documents to backup"],
)
def sync_files(source: str, destination: str) -> ToolResult:
    """Sync files."""
    try:
        manager = FileSyncManager()
        pair = manager.add_sync_pair("temp_sync", source, destination)
        changes = manager.sync(pair.id)
        manager.remove_sync_pair(pair.id)
        
        return ToolResult(
            success=True,
            output={
                "synced": len([c for c in changes if c.change_type != "deleted"]),
                "changes": [{"path": c.path, "type": c.change_type} for c in changes[:10]],
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="backup_files",
    description="Create a backup of files",
    category="files",
    examples=["backup my project"],
)
def backup_files(source: str, backup_dir: str = "./backups") -> ToolResult:
    """Create backup."""
    try:
        manager = FileSyncManager()
        path = manager.backup(source, backup_dir)
        
        return ToolResult(
            success=True,
            output=f"Backup created: {path}",
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing File Sync Manager...")
    
    manager = FileSyncManager(config_path="./test_file_sync.json")
    
    # Create test directories
    os.makedirs("./test_source", exist_ok=True)
    os.makedirs("./test_dest", exist_ok=True)
    
    # Create test file
    with open("./test_source/test.txt", 'w') as f:
        f.write("Hello, JARVIS!")
    
    # Add sync pair
    pair = manager.add_sync_pair("Test", "./test_source", "./test_dest")
    print(f"Added sync pair: {pair.name}")
    
    # Sync
    changes = manager.sync(pair.id)
    print(f"Synced {len(changes)} files")
    
    # Backup
    backup = manager.backup("./test_source", "./test_backups")
    print(f"Backup created: {backup}")
    
    # Cleanup
    shutil.rmtree("./test_source", ignore_errors=True)
    shutil.rmtree("./test_dest", ignore_errors=True)
    shutil.rmtree("./test_backups", ignore_errors=True)
    os.remove("./test_file_sync.json") if os.path.exists("./test_file_sync.json") else None
    
    print("\nFile sync test complete!")
