#!/usr/bin/env python3
"""
dazzle-checksum.py - Cross-Platform Checksum Tool

A comprehensive tool for generating folder-specific checksum files (.shasum) that enables
data integrity verification across different machines and operating systems.

Features:
- Cross-platform compatibility (Windows, macOS, Linux, BSD)
- FIFO directory processing for memory efficiency
- Native tool integration with Python fallback
- Line ending normalization for consistent checksums
- Symlink/junction loop detection
- Incremental updates and change tracking
- Compatible output format with standard tools
- Monolithic checksum files for entire directory trees

Usage:
    dazzle-checksum.py [OPTIONS] [DIRECTORY]

Examples:
    dazzle-checksum.py                           # Current directory
    dazzle-checksum.py --recursive /path/to/dir  # Recursive processing
    dazzle-checksum.py --algorithm sha512        # Different algorithm
    dazzle-checksum.py --verify                  # Verify existing checksums
    dazzle-checksum.py --update                  # Incremental update
    dazzle-checksum.py --monolithic --recursive  # Single checksum file for tree
    dazzle-checksum.py --monolithic --output checksums.sha256  # Custom output
"""

import os
import sys
import re
import json
import time
import stat
import hashlib
import logging
import argparse
import platform
import subprocess
import shutil
from collections import deque
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Any

# Version information
__version__ = "1.1.0"
__author__ = "Dustin Darcy"

# Try to import unctools for enhanced path handling
try:
    import unctools
    from unctools import normalize_path, convert_to_local, is_unc_path
    from unctools.utils import is_windows as unctools_is_windows, get_platform_info
    from unctools.operations import safe_open, file_exists
    HAVE_UNCTOOLS = True
    # Use unctools function
    def is_windows(): return unctools_is_windows
except ImportError:
    HAVE_UNCTOOLS = False
    # Fallback implementations
    def is_windows(): return os.name == 'nt'
    def normalize_path(p): return Path(p)
    def safe_open(p, *args, **kwargs): return open(p, *args, **kwargs)
    def file_exists(p): return Path(p).exists()

# Constants
DEFAULT_ALGORITHM = 'sha256'
DEFAULT_CHUNK_SIZE = 8192
SUPPORTED_ALGORITHMS = ['md5', 'sha1', 'sha256', 'sha512']
SHASUM_FILENAME = '.shasum'
STATE_FILENAME = '.dazzle-state.json'
MONOLITHIC_DEFAULT_NAME = 'checksums'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DazzleLogger:
    """Enhanced logger with DOS-compatible verbosity levels and visual separation."""

    def __init__(self, verbosity=0, quiet=False, summary_mode=False):
        self.verbosity = verbosity
        self.quiet = quiet
        self.summary_mode = summary_mode
        self.last_was_directory = False

    def _should_log(self, level):
        """Check if we should log at this verbosity level."""
        if self.quiet:
            return level <= 0  # Only errors/warnings in quiet mode
        if self.summary_mode:
            return level <= 1  # Reduced output in summary mode
        return self.verbosity >= level

    def _add_spacing_if_needed(self):
        """Add blank line for directory separation."""
        if self.last_was_directory and self._should_log(1):
            print()

    def error(self, msg):
        """Always show errors."""
        logger.error(msg)

    def warning(self, msg):
        """Always show warnings."""
        logger.warning(msg)

    def info(self, msg, level=1):
        """Info messages with verbosity level."""
        if self._should_log(level):
            logger.info(msg)

    def debug(self, msg):
        """Debug messages (verbosity level 3)."""
        if self._should_log(3):
            logger.debug(msg)

    def directory_start(self, path):
        """Log directory processing start with spacing."""
        if self._should_log(1):
            self._add_spacing_if_needed()
            logger.info(f"Processing directory: {path}")

    def directory_complete(self, path, processed, skipped, failed, elapsed_time):
        """Log directory completion with consistent formatting."""
        if self._should_log(1):
            if failed > 0:
                logger.info(f"Directory {path}: {processed} processed, "
                           f"{skipped} skipped, {failed} failed in {elapsed_time:.2f}s")
            else:
                logger.info(f"Directory {path}: {processed} processed, "
                           f"{skipped} skipped in {elapsed_time:.2f}s")
            self.last_was_directory = True  # Mark that we completed a directory

    def file_processed(self, file_path, level=2):
        """Log individual file processing (verbosity level 2+)."""
        if self._should_log(level):
            logger.info(f"  Processed: {file_path.name}")

    def file_skipped(self, file_path, reason="", level=2):
        """Log skipped files (verbosity level 2+)."""
        if self._should_log(level):
            if reason:
                logger.info(f"  Skipped: {file_path.name} ({reason})")
            else:
                logger.info(f"  Skipped: {file_path.name}")

    def verification_status(self, filename, status, details="", level=2):
        """Log verification results with DOS-compatible indicators."""
        if not self._should_log(level):
            return

        status_indicators = {
            'verified': 'OK',
            'failed': 'FAIL',
            'missing': 'MISS',
            'extra': 'EXTRA'
        }

        indicator = status_indicators.get(status, 'INFO')
        if details:
            logger.info(f"  {indicator} {filename} - {details}")
        else:
            logger.info(f"  {indicator} {filename}")

    def tool_selection(self, tool_name, algorithm):
        """Log native tool selection (debug level)."""
        if tool_name:
            self.debug(f"Using native tool: {tool_name} for {algorithm}")
        else:
            self.debug(f"Using Python implementation for {algorithm}")


# Global logger instance - will be set up in main()
dazzle_logger = None


class ShasumManager:
    """Manages .shasum files with backup, remove, restore, and list operations."""

    def __init__(self, root_dir: Path, backup_dir: Optional[Path] = None, dry_run: bool = False):
        self.root_dir = Path(root_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self.dry_run = dry_run
        self.logger = dazzle_logger if dazzle_logger else logger

    def find_shasum_files(self) -> List[Path]:
        """Find all .shasum files in the directory tree."""
        shasum_files = []

        try:
            for root, dirs, files in os.walk(self.root_dir):
                if SHASUM_FILENAME in files:
                    shasum_path = Path(root) / SHASUM_FILENAME
                    shasum_files.append(shasum_path)

        except Exception as e:
            self.logger.error(f"Error scanning directory tree: {e}")

        return sorted(shasum_files)

    def backup_shasums(self) -> Dict[str, Any]:
        """Backup all .shasum files to parallel directory structure."""
        if not self.backup_dir:
            raise ValueError("backup_dir is required for backup operation")

        shasum_files = self.find_shasum_files()
        if not shasum_files:
            self.logger.info("No .shasum files found to backup")
            return {'files_backed_up': 0, 'errors': []}

        self.logger.info(f"Found {len(shasum_files)} .shasum files to backup")

        if self.dry_run:
            self.logger.info("DRY RUN - would backup:")
            for shasum_file in shasum_files:
                rel_path = shasum_file.relative_to(self.root_dir)
                backup_path = self.backup_dir / rel_path
                self.logger.info(f"  {shasum_file} -> {backup_path}")
            return {'files_backed_up': len(shasum_files), 'errors': []}

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        backed_up = 0
        errors = []

        for shasum_file in shasum_files:
            try:
                # Calculate relative path from root
                rel_path = shasum_file.relative_to(self.root_dir)
                backup_path = self.backup_dir / rel_path

                # Create backup directory structure
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file to backup location
                shutil.copy2(shasum_file, backup_path)

                self.logger.debug(f"Backed up: {rel_path}")
                backed_up += 1

            except Exception as e:
                error_msg = f"Failed to backup {shasum_file}: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        self.logger.info(f"Successfully backed up {backed_up} .shasum files to {self.backup_dir}")
        if errors:
            self.logger.warning(f"Encountered {len(errors)} errors during backup")

        return {'files_backed_up': backed_up, 'errors': errors}

    def remove_shasums(self, force: bool = False) -> Dict[str, Any]:
        """Remove all .shasum files from directory tree."""
        shasum_files = self.find_shasum_files()
        if not shasum_files:
            self.logger.info("No .shasum files found to remove")
            return {'files_removed': 0, 'errors': []}

        self.logger.info(f"Found {len(shasum_files)} .shasum files to remove")

        if self.dry_run:
            self.logger.info("DRY RUN - would remove:")
            for shasum_file in shasum_files:
                self.logger.info(f"  {shasum_file}")
            return {'files_removed': len(shasum_files), 'errors': []}

        # Confirmation prompt unless forced
        if not force:
            try:
                response = input(f"Remove {len(shasum_files)} .shasum files? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    self.logger.info("Operation cancelled by user")
                    return {'files_removed': 0, 'errors': ['Operation cancelled by user']}
            except (EOFError, KeyboardInterrupt):
                self.logger.info("Operation cancelled by user")
                return {'files_removed': 0, 'errors': ['Operation cancelled by user']}

        removed = 0
        errors = []

        for shasum_file in shasum_files:
            try:
                shasum_file.unlink()
                self.logger.debug(f"Removed: {shasum_file}")
                removed += 1

            except Exception as e:
                error_msg = f"Failed to remove {shasum_file}: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        self.logger.info(f"Successfully removed {removed} .shasum files")
        if errors:
            self.logger.warning(f"Encountered {len(errors)} errors during removal")

        return {'files_removed': removed, 'errors': errors}

    def restore_shasums(self) -> Dict[str, Any]:
        """Restore .shasum files from backup directory."""
        if not self.backup_dir:
            raise ValueError("backup_dir is required for restore operation")

        if not self.backup_dir.exists():
            raise FileNotFoundError(f"Backup directory does not exist: {self.backup_dir}")

        # Find .shasum files in backup directory
        backup_files = []
        try:
            for root, dirs, files in os.walk(self.backup_dir):
                if SHASUM_FILENAME in files:
                    backup_path = Path(root) / SHASUM_FILENAME
                    backup_files.append(backup_path)
        except Exception as e:
            self.logger.error(f"Error scanning backup directory: {e}")
            return {'files_restored': 0, 'errors': [f"Error scanning backup directory: {e}"]}

        if not backup_files:
            self.logger.info("No .shasum files found in backup directory")
            return {'files_restored': 0, 'errors': []}

        self.logger.info(f"Found {len(backup_files)} .shasum files to restore")

        if self.dry_run:
            self.logger.info("DRY RUN - would restore:")
            for backup_file in backup_files:
                rel_path = backup_file.relative_to(self.backup_dir)
                target_path = self.root_dir / rel_path
                self.logger.info(f"  {backup_file} -> {target_path}")
            return {'files_restored': len(backup_files), 'errors': []}

        restored = 0
        errors = []

        for backup_file in backup_files:
            try:
                # Calculate target path in original tree
                rel_path = backup_file.relative_to(self.backup_dir)
                target_path = self.root_dir / rel_path

                # Create target directory if needed
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file from backup to target location
                shutil.copy2(backup_file, target_path)

                self.logger.debug(f"Restored: {rel_path}")
                restored += 1

            except Exception as e:
                error_msg = f"Failed to restore {backup_file}: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        self.logger.info(f"Successfully restored {restored} .shasum files from {self.backup_dir}")
        if errors:
            self.logger.warning(f"Encountered {len(errors)} errors during restore")

        return {'files_restored': restored, 'errors': errors}

    def list_shasums(self) -> List[Dict[str, Any]]:
        """List all .shasum files with detailed information."""
        shasum_files = self.find_shasum_files()

        if not shasum_files:
            self.logger.info("No .shasum files found")
            return []

        file_info = []

        for shasum_file in shasum_files:
            try:
                stat_info = shasum_file.stat()

                # Count checksums in file
                checksum_count = 0
                try:
                    with open(shasum_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                checksum_count += 1
                except Exception:
                    checksum_count = "?"

                info = {
                    'path': shasum_file,
                    'size': stat_info.st_size,
                    'modified': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_mtime)),
                    'checksums': checksum_count
                }
                file_info.append(info)

            except Exception as e:
                self.logger.error(f"Error reading {shasum_file}: {e}")

        # Display information
        self.logger.info(f"Found {len(file_info)} .shasum files:")
        for info in file_info:
            rel_path = info['path'].relative_to(self.root_dir)
            self.logger.info(f"  {rel_path}")
            self.logger.info(f"    Size: {info['size']} bytes, Modified: {info['modified']}, Checksums: {info['checksums']}")

        return file_info


class MonolithicWriter:
    """Handles streaming writes to monolithic checksum files."""

    def __init__(self, output_path: Path, root_path: Path, algorithm: str):
        self.output_path = Path(output_path)
        self.temp_path = Path(str(output_path) + '.tmp')
        self.root_path = Path(root_path)
        self.algorithm = algorithm
        self.file_handle = None
        self.entries_written = 0
        self._is_open = False

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if exc_type is not None:
            # Error occurred, clean up temp file
            self.close(success=False)
        else:
            # Normal completion
            self.close(success=True)

    def open(self):
        """Open the monolithic file for writing."""
        try:
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Open temp file for writing
            self.file_handle = open(self.temp_path, 'w', encoding='utf-8', buffering=8192)
            self._is_open = True

            # Write header
            timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self.file_handle.write(f"# Dazzle monolithic checksum file v{__version__} - {self.algorithm} - {timestamp}\n")
            self.file_handle.write(f"# Root directory: {self.root_path}\n")
            self.file_handle.flush()

            logger.debug(f"Opened monolithic file for writing: {self.temp_path}")

        except Exception as e:
            logger.error(f"Failed to open monolithic file {self.temp_path}: {e}")
            self._cleanup_temp()
            raise

    def append_directory_checksums(self, directory: Path, checksums: Dict[str, Any]):
        """Append checksums from a directory to the monolithic file."""
        if not self._is_open or not self.file_handle:
            raise RuntimeError("MonolithicWriter is not open")

        try:
            for filename, checksum_info in sorted(checksums.items()):
                # Calculate relative path from root
                file_path = directory / filename
                try:
                    relative_path = os.path.relpath(file_path, self.root_path)
                    # Use forward slashes for cross-platform compatibility
                    relative_path = relative_path.replace('\\', '/')
                except ValueError:
                    # Handle cases where paths are on different drives (Windows)
                    relative_path = str(file_path)
                    logger.warning(f"Could not create relative path for {file_path}, using absolute path")

                # Write in standard format: hash  filename
                self.file_handle.write(f"{checksum_info['hash']}  {relative_path}\n")
                self.entries_written += 1

            # Flush to ensure data is written
            self.file_handle.flush()

        except Exception as e:
            logger.error(f"Failed to append checksums for {directory}: {e}")
            raise

    def close(self, success: bool = True):
        """Close the monolithic file and finalize."""
        if not self._is_open:
            return

        try:
            if self.file_handle:
                if success:
                    # Write footer
                    self.file_handle.write("# End of checksums\n")
                    self.file_handle.flush()

                # Close file handle
                self.file_handle.close()
                self.file_handle = None

            if success and self.temp_path.exists():
                # Atomic rename to final location
                os.rename(self.temp_path, self.output_path)
                logger.info(f"Wrote {self.entries_written} checksums to monolithic file: {self.output_path}")
            else:
                # Cleanup temp file on failure
                self._cleanup_temp()

        except Exception as e:
            logger.error(f"Error closing monolithic file: {e}")
            self._cleanup_temp()
            raise
        finally:
            self._is_open = False

    def _cleanup_temp(self):
        """Clean up temporary file."""
        try:
            if self.temp_path.exists():
                os.remove(self.temp_path)
        except Exception as e:
            logger.warning(f"Could not remove temp file {self.temp_path}: {e}")


class ProgressTracker:
    """Track progress with percentage completion and ETA."""

    def __init__(self, total_dirs=0, total_files=0, show_progress=True):
        self.total_dirs = total_dirs
        self.total_files = total_files
        self.processed_dirs = 0
        self.processed_files = 0
        self.show_progress = show_progress
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 0.5  # Update every 500ms

    def update_dirs(self, count=1):
        """Update directory progress."""
        self.processed_dirs += count
        self._maybe_display_progress()

    def update_files(self, count=1):
        """Update file progress."""
        self.processed_files += count
        self._maybe_display_progress()

    def _maybe_display_progress(self):
        """Display progress if enough time has passed."""
        if not self.show_progress:
            return

        now = time.time()
        if now - self.last_update >= self.update_interval:
            self.last_update = now
            self._display_progress()

    def _display_progress(self):
        """Display current progress."""
        if self.total_dirs == 0 and self.total_files == 0:
            return

        # Calculate overall progress
        dir_weight = 0.1  # Directories are 10% of the work
        file_weight = 0.9  # Files are 90% of the work

        if self.total_dirs > 0 and self.total_files > 0:
            dir_progress = (self.processed_dirs / self.total_dirs) * dir_weight
            file_progress = (self.processed_files / self.total_files) * file_weight
            overall_progress = dir_progress + file_progress
        elif self.total_dirs > 0:
            overall_progress = self.processed_dirs / self.total_dirs
        else:
            overall_progress = self.processed_files / self.total_files if self.total_files > 0 else 0

        percentage = min(100, overall_progress * 100)

        # Calculate ETA
        elapsed = time.time() - self.start_time
        if percentage > 0 and elapsed > 0:
            eta_seconds = (elapsed / (percentage / 100)) - elapsed
            eta_str = self._format_duration(eta_seconds) if eta_seconds > 0 else "calculating..."
        else:
            eta_str = "calculating..."

        # Create progress bar
        bar_width = 30
        filled = int(bar_width * (percentage / 100))
        bar = '█' * filled + '░' * (bar_width - filled)

        # Print progress (overwrite previous line)
        print(f"\r[{bar}] {percentage:5.1f}% | "
              f"Dirs: {self.processed_dirs}/{self.total_dirs} | "
              f"Files: {self.processed_files}/{self.total_files} | "
              f"ETA: {eta_str}", end='', flush=True)

    def _format_duration(self, seconds):
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m {seconds%60:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def finish(self):
        """Complete the progress display."""
        if self.show_progress and (self.total_dirs > 0 or self.total_files > 0):
            print()  # New line after progress bar
            elapsed = time.time() - self.start_time
            logger.info(f"Completed {self.processed_dirs} directories, {self.processed_files} files in {self._format_duration(elapsed)}")


class SummaryCollector:
    """Collect summary statistics during processing."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters."""
        self.dirs_processed = 0
        self.files_processed = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.total_bytes = 0
        self.verification_results = {
            'verified': 0,
            'failed': 0,
            'missing': 0,
            'extra': 0
        }

    def add_directory(self, file_count, skip_count, fail_count, total_bytes):
        """Add statistics from a directory."""
        self.dirs_processed += 1
        self.files_processed += file_count
        self.files_skipped += skip_count
        self.files_failed += fail_count
        self.total_bytes += total_bytes

    def add_verification(self, results):
        """Add verification results."""
        if 'error' not in results:
            self.verification_results['verified'] += len(results.get('verified', []))
            self.verification_results['failed'] += len(results.get('failed', []))
            self.verification_results['missing'] += len(results.get('missing', []))
            self.verification_results['extra'] += len(results.get('extra', []))

    def get_summary(self):
        """Get summary statistics."""
        return {
            'directories': self.dirs_processed,
            'files_processed': self.files_processed,
            'files_skipped': self.files_skipped,
            'files_failed': self.files_failed,
            'total_bytes': self.total_bytes,
            'verification': self.verification_results
        }

    def print_summary(self):
        """Print a summary of operations."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("OPERATION SUMMARY")
        print("="*60)
        print(f"Directories processed: {summary['directories']}")
        print(f"Files processed:       {summary['files_processed']}")
        if summary['files_skipped'] > 0:
            print(f"Files skipped:         {summary['files_skipped']}")
        if summary['files_failed'] > 0:
            print(f"Files failed:          {summary['files_failed']}")
        print(f"Total data processed:  {self._format_bytes(summary['total_bytes'])}")

        # Verification summary
        if any(summary['verification'].values()):
            print(f"\nVerification results:")
            print(f"  Verified:  {summary['verification']['verified']}")
            print(f"  Failed:    {summary['verification']['failed']}")
            print(f"  Missing:   {summary['verification']['missing']}")
            print(f"  Extra:     {summary['verification']['extra']}")

        print("="*60)

    def _format_bytes(self, bytes_count):
        """Format bytes in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} PB"


def count_dirs_and_files(root_path: Path, include_patterns, exclude_patterns,
                        follow_symlinks=False) -> Tuple[int, int]:
    """Pre-walk directory tree to count directories and files."""
    symlink_handler = SymlinkHandler()
    total_dirs = 0
    total_files = 0

    # Use a simple queue for counting
    dirs_to_visit = deque([root_path])

    while dirs_to_visit:
        current_dir = dirs_to_visit.popleft()

        # Skip if already visited (loop detection)
        if symlink_handler.is_visited(current_dir):
            continue
        symlink_handler.mark_visited(current_dir)

        # Skip if we shouldn't follow this link
        if not symlink_handler.should_follow_link(current_dir, follow_symlinks):
            continue

        try:
            total_dirs += 1

            # Count files in this directory
            for item in current_dir.iterdir():
                if item.is_file():
                    # Apply same filtering logic as main processor
                    if _should_include_file_simple(item, include_patterns, exclude_patterns):
                        total_files += 1
                elif item.is_dir() and not symlink_handler.is_visited(item):
                    dirs_to_visit.append(item)
        except Exception:
            # Skip directories we can't access
            continue

    return total_dirs, total_files


def _should_include_file_simple(file_path: Path, include_patterns, exclude_patterns) -> bool:
    """Simplified version of file inclusion check for counting."""
    filename = file_path.name

    # Always exclude our own files
    if filename in [SHASUM_FILENAME, STATE_FILENAME]:
        return False

    # Apply exclude patterns
    for pattern in exclude_patterns:
        if file_path.match(pattern):
            return False

    # Apply include patterns (if any)
    if include_patterns:
        for pattern in include_patterns:
            if file_path.match(pattern):
                return True
        return False

    return True


class LineEndingHandler:
    """Handles line ending normalization for consistent checksums across platforms."""

    def __init__(self, strategy='auto'):
        """
        Initialize line ending handler.

        Args:
            strategy: 'auto', 'unix', 'windows', 'preserve'
        """
        self.strategy = strategy
        self.text_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.xml', '.json', '.yaml', '.yml',
            '.md', '.rst', '.cfg', '.ini', '.conf', '.log', '.sql', '.sh', '.bat',
            '.cmd', '.ps1', '.php', '.rb', '.pl', '.java', '.c', '.cpp', '.h',
            '.hpp', '.cs', '.vb', '.go', '.rs', '.swift', '.kt', '.scala'
        }

    def should_normalize(self, file_path: Path) -> bool:
        """Determine if a file should have line ending normalization."""
        if self.strategy == 'preserve':
            return False

        # Check file extension
        if file_path.suffix.lower() in self.text_extensions:
            return True

        # Auto-detect by reading first few bytes
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
                if not sample:
                    return False

                # Check for null bytes (indicates binary)
                if b'\x00' in sample:
                    return False

                # Check for text-like content
                try:
                    sample.decode('utf-8')
                    return True
                except UnicodeDecodeError:
                    try:
                        sample.decode('latin-1')
                        return True
                    except UnicodeDecodeError:
                        return False
        except Exception:
            return False

    def normalize_content(self, content: bytes) -> bytes:
        """Normalize line endings in content."""
        if self.strategy == 'preserve':
            return content

        try:
            # Decode to string
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except UnicodeDecodeError:
                return content  # Can't decode, return as-is

        # Normalize line endings
        if self.strategy == 'unix' or self.strategy == 'auto':
            text = text.replace('\r\n', '\n').replace('\r', '\n')
        elif self.strategy == 'windows':
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

        return text.encode('utf-8')


class SymlinkHandler:
    """Handles symlink and junction detection with loop prevention."""

    def __init__(self):
        self.visited_inodes = set()
        self.visited_paths = set()

    def is_symlink_or_junction(self, path: Path) -> Tuple[bool, Optional[str]]:
        """Detect symlinks and Windows junctions."""
        try:
            # Standard symlink detection
            if path.is_symlink():
                return True, 'symlink'

            # Windows junction detection
            if is_windows() and path.is_dir():
                return self._is_junction(path), 'junction'

        except Exception as e:
            logger.debug(f"Error checking symlink status for {path}: {e}")

        return False, None

    def _is_junction(self, path: Path) -> bool:
        """Detect Windows junctions using various methods."""
        try:
            # Method 1: Check file attributes
            if hasattr(os, 'lstat'):
                stat_info = os.lstat(str(path))
                if hasattr(stat, 'S_ISLNK') and stat.S_ISLNK(stat_info.st_mode):
                    return True

            # Method 2: Try to resolve and check if different
            try:
                resolved = path.resolve()
                if str(resolved) != str(path):
                    return True
            except Exception:
                pass

            # Method 3: Use dir command as fallback
            try:
                result = subprocess.run(
                    ['dir', '/AL', str(path.parent)],
                    capture_output=True, text=True, shell=True
                )
                if result.returncode == 0:
                    return '<JUNCTION>' in result.stdout and path.name in result.stdout
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Error detecting junction for {path}: {e}")

        return False

    def should_follow_link(self, path: Path, follow_symlinks: bool = False) -> bool:
        """Determine if we should follow this link."""
        is_link, link_type = self.is_symlink_or_junction(path)

        if not is_link:
            return True  # Regular file/directory

        if not follow_symlinks:
            return False  # User doesn't want to follow links

        # Additional safety checks for links
        try:
            target = path.resolve()
            # Ensure target exists and isn't pointing to parent
            return target.exists() and not self._is_parent_loop(path, target)
        except (OSError, RuntimeError):
            return False  # Broken or dangerous link

    def _is_parent_loop(self, link_path: Path, target_path: Path) -> bool:
        """Check if target is a parent of the link (potential loop)."""
        try:
            link_path.relative_to(target_path)
            return True  # link is inside target - potential loop
        except ValueError:
            return False  # No parent relationship

    def mark_visited(self, path: Path):
        """Mark a path as visited for loop detection."""
        # Mark by resolved path
        try:
            resolved_path = str(path.resolve())
            self.visited_paths.add(resolved_path)
        except Exception:
            self.visited_paths.add(str(path))

        # Mark by inode (if available)
        try:
            stat_info = path.stat()
            inode_key = (stat_info.st_dev, stat_info.st_ino)
            self.visited_inodes.add(inode_key)
        except (OSError, AttributeError):
            pass  # Can't get inode info, path marking is sufficient

    def is_visited(self, path: Path) -> bool:
        """Check if we've already visited this path/inode."""
        # Check by resolved path
        try:
            resolved_path = str(path.resolve())
            if resolved_path in self.visited_paths:
                return True
        except Exception:
            if str(path) in self.visited_paths:
                return True

        # Check by inode (if available)
        try:
            stat_info = path.stat()
            inode_key = (stat_info.st_dev, stat_info.st_ino)
            if inode_key in self.visited_inodes:
                return True
        except (OSError, AttributeError):
            pass

        return False


class FIFODirectoryWalker:
    """FIFO directory processor for memory-efficient traversal."""

    def __init__(self, follow_symlinks=False):
        self.processing_queue = deque()
        self.symlink_handler = SymlinkHandler()
        self.follow_symlinks = follow_symlinks
        self.processed_count = 0

    def walk_and_process(self, root_path: Path, processor_func, recursive=True):
        """
        FIFO directory processing with callback.

        Args:
            root_path: Starting directory
            processor_func: Function to call for each directory
            recursive: Whether to process subdirectories
        """
        self.processing_queue.append(root_path)

        while self.processing_queue:
            current_dir = self.processing_queue.popleft()

            # Safety check for loops
            if self.symlink_handler.is_visited(current_dir):
                logger.warning(f"Skipping {current_dir} - already visited (loop detected)")
                continue

            # Mark as visited
            self.symlink_handler.mark_visited(current_dir)

            # Check if we should follow this directory (symlink safety)
            if not self.symlink_handler.should_follow_link(current_dir, self.follow_symlinks):
                logger.debug(f"Skipping {current_dir} - symlink/junction not followed")
                continue

            # Process current directory
            try:
                if dazzle_logger:
                    dazzle_logger.directory_start(current_dir)
                else:
                    logger.info(f"Processing directory: {current_dir}")
                processor_func(current_dir)
                self.processed_count += 1
            except Exception as e:
                logger.error(f"Error processing directory {current_dir}: {e}")
                continue

            # Add subdirectories to queue if recursive
            if recursive:
                try:
                    subdirs = [item for item in current_dir.iterdir()
                              if item.is_dir() and not self.symlink_handler.is_visited(item)]
                    for subdir in subdirs:
                        self.processing_queue.append(subdir)
                        logger.debug(f"Added to queue: {subdir}")
                except Exception as e:
                    logger.warning(f"Error listing subdirectories of {current_dir}: {e}")


class DazzleHashCalculator:
    """Main hash calculator with normalization and native tool integration."""

    def __init__(self, algorithm=DEFAULT_ALGORITHM, line_ending_strategy='auto',
                 chunk_size=DEFAULT_CHUNK_SIZE):
        self.algorithm = algorithm.lower()
        self.chunk_size = chunk_size
        self.line_handler = LineEndingHandler(line_ending_strategy)
        self.native_tool = self._detect_native_tool()

    def _detect_native_tool(self) -> Optional[str]:
        """Detect available native checksum tools."""
        tools_to_try = []

        if is_windows():
            tools_to_try = ['fsum', 'certutil']
        else:
            if self.algorithm == 'sha256':
                tools_to_try = ['sha256sum', 'shasum']
            elif self.algorithm == 'sha1':
                tools_to_try = ['sha1sum', 'shasum']
            elif self.algorithm == 'md5':
                tools_to_try = ['md5sum', 'md5']
            elif self.algorithm == 'sha512':
                tools_to_try = ['sha512sum', 'shasum']

        for tool in tools_to_try:
            if self._tool_available(tool):
                if dazzle_logger:
                    dazzle_logger.tool_selection(tool, self.algorithm)
                else:
                    logger.debug(f"Using native tool: {tool}")
                return tool

        if dazzle_logger:
            dazzle_logger.tool_selection(None, self.algorithm)
        else:
            logger.debug("No native tools available, using Python implementation")
        return None

    def _tool_available(self, tool: str) -> bool:
        """Check if a native tool is available."""
        try:
            # Special handling for fsum
            if tool == 'fsum':
                result = subprocess.run([tool], capture_output=True, text=True, timeout=5)
                # fsum returns usage info when called without arguments
                return 'SlavaSoft' in result.stdout or 'fsum' in result.stdout.lower()

            # For other tools, try --help or --version
            for flag in ['--help', '--version', '-h']:
                try:
                    result = subprocess.run([tool, flag], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 or 'usage' in result.stderr.lower():
                        return True
                except Exception:
                    continue

            return False
        except Exception:
            return False

    def _calculate_with_native_tool(self, file_path: Path) -> str:
        """Calculate hash using native tool."""
        if not self.native_tool:
            raise ValueError("No native tool available")

        # Handle different tools
        if self.native_tool == 'fsum':
            return self._calculate_with_fsum(file_path)
        elif self.native_tool == 'certutil':
            return self._calculate_with_certutil(file_path)
        elif self.native_tool.endswith('sum'):
            return self._calculate_with_hashsum(file_path)
        elif self.native_tool == 'shasum':
            return self._calculate_with_shasum(file_path)
        else:
            raise ValueError(f"Unsupported native tool: {self.native_tool}")

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash for a single file."""
        # Normalize path using unctools if available
        if HAVE_UNCTOOLS:
            file_path = normalize_path(file_path)

        # Try native tool first
        if self.native_tool:
            try:
                return self._calculate_with_native_tool(file_path)
            except Exception as e:
                # Only log warning in debug mode to reduce noise
                logger.debug(f"Native tool {self.native_tool} failed for {file_path}, using Python: {e}")

        # Fallback to Python implementation
        return self._calculate_with_python(file_path)

    def _calculate_with_fsum(self, file_path: Path) -> str:
        """Calculate hash using Windows fsum tool."""
        cmd = ['fsum', f'-{self.algorithm}', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        # Parse fsum output - skip header lines and comments
        lines = result.stdout.splitlines()
        for line in lines:
            line = line.strip()
            # Skip empty lines, comment lines, and header lines
            if not line or line.startswith(';') or line.startswith('SlavaSoft'):
                continue

            # Look for hash lines - they contain the filename with * prefix
            if ' *' in line:
                hash_value = line.split(' *')[0].strip()
                return hash_value.lower()

            # Alternative format: hash followed by space and filename
            parts = line.split()
            if len(parts) >= 2 and len(parts[0]) in [32, 40, 64, 128]:  # Common hash lengths
                return parts[0].lower()

        raise ValueError(f"Could not parse fsum output: {result.stdout}")

    def _calculate_with_certutil(self, file_path: Path) -> str:
        """Calculate hash using Windows certutil."""
        algo_map = {'md5': 'MD5', 'sha1': 'SHA1', 'sha256': 'SHA256', 'sha512': 'SHA512'}
        certutil_algo = algo_map.get(self.algorithm)

        if not certutil_algo:
            raise ValueError(f"Unsupported algorithm for certutil: {self.algorithm}")

        cmd = ['certutil', '-hashfile', str(file_path), certutil_algo]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        # Parse certutil output - hash is typically on the second non-empty line
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        for line in lines[1:]:  # Skip first line (filename)
            # Remove spaces and check if it looks like a hash
            clean_line = line.replace(' ', '').replace('\t', '')
            if len(clean_line) in [32, 40, 64, 128] and all(c in '0123456789abcdefABCDEF' for c in clean_line):
                return clean_line.lower()

        raise ValueError(f"Could not parse certutil output: {result.stdout}")

    def _calculate_with_hashsum(self, file_path: Path) -> str:
        """Calculate hash using Unix *sum tools."""
        cmd = [self.native_tool, str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        # Parse output (first field is hash)
        first_line = result.stdout.strip().split('\n')[0]
        hash_value = first_line.split()[0]
        return hash_value.lower()

    def _calculate_with_shasum(self, file_path: Path) -> str:
        """Calculate hash using shasum tool."""
        algo_map = {'sha1': '1', 'sha256': '256', 'sha512': '512'}
        shasum_algo = algo_map.get(self.algorithm)

        if not shasum_algo:
            raise ValueError(f"Unsupported algorithm for shasum: {self.algorithm}")

        cmd = ['shasum', f'-a{shasum_algo}', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        # Parse output (first field is hash)
        first_line = result.stdout.strip().split('\n')[0]
        hash_value = first_line.split()[0]
        return hash_value.lower()

    def _calculate_with_python(self, file_path: Path) -> str:
        """Calculate hash using Python hashlib."""
        try:
            hasher = hashlib.new(self.algorithm)
        except ValueError:
            raise ValueError(f"Unsupported hash algorithm: {self.algorithm}")

        # Use safe_open if available
        try:
            if HAVE_UNCTOOLS:
                with safe_open(file_path, 'rb') as f:
                    return self._hash_file_content(f, hasher)
            else:
                with open(file_path, 'rb') as f:
                    return self._hash_file_content(f, hasher)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    def _hash_file_content(self, file_obj, hasher) -> str:
        """Hash file content with optional normalization."""
        # Check if we should normalize line endings
        first_chunk = file_obj.read(self.chunk_size)
        if not first_chunk:
            return hasher.hexdigest()

        # Reset file pointer
        file_obj.seek(0)

        # Determine if we should normalize
        temp_path = Path(file_obj.name) if hasattr(file_obj, 'name') else None
        should_normalize = (temp_path and
                          self.line_handler.should_normalize(temp_path))

        if should_normalize:
            # Read entire file and normalize
            content = file_obj.read()
            normalized_content = self.line_handler.normalize_content(content)
            hasher.update(normalized_content)
        else:
            # Stream processing for large files
            file_obj.seek(0)
            while chunk := file_obj.read(self.chunk_size):
                hasher.update(chunk)

        return hasher.hexdigest()


def is_monolithic_file(file_path: Path) -> bool:
    """Detect if a checksum file is in monolithic format."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first few lines to check for monolithic markers
            for i, line in enumerate(f):
                if i > 10:  # Only check first 10 lines
                    break

                line = line.strip()
                if not line or line.startswith('#'):
                    # Check for monolithic format indicators
                    if 'monolithic' in line.lower() or 'root directory:' in line.lower():
                        return True
                    continue
                else:
                    # Check if we have relative paths (indicating monolithic)
                    # Individual .shasum files should only have filenames, no paths
                    parts = line.split('  ', 1)
                    if len(parts) == 2:
                        filename = parts[1]
                        # If filename contains path separators, it's likely monolithic
                        if '/' in filename or '\\' in filename:
                            return True
                    break

        return False
    except Exception:
        return False


class ChecksumGenerator:
    """Main checksum generator orchestrator."""

    def __init__(self, algorithm=DEFAULT_ALGORITHM, line_ending_strategy='auto',
                 include_patterns=None, exclude_patterns=None, follow_symlinks=False,
                 log_file=None, summary_mode=False, generate_individual=True,
                 generate_monolithic=False, output_file=None, show_all_verifications=False):
        self.algorithm = algorithm.lower()
        self.calculator = DazzleHashCalculator(algorithm, line_ending_strategy)
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or ['*.tmp', '*.log', SHASUM_FILENAME, STATE_FILENAME]
        self.follow_symlinks = follow_symlinks
        self.log_file = log_file
        self.summary_mode = summary_mode
        self.generate_individual = generate_individual
        self.generate_monolithic = generate_monolithic
        self.output_file = output_file
        self.show_all_verifications = show_all_verifications
        self.summary_collector = SummaryCollector()
        self.progress_tracker = None

        # Set up log file if specified
        if self.log_file:
            self._setup_log_file()

    def _setup_log_file(self):
        """Set up detailed logging to file."""
        log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = logging.FileHandler(self.log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Add to root logger
        logging.getLogger().addHandler(file_handler)
        logger.info(f"Detailed logging enabled to: {self.log_file}")

    def should_include_file(self, file_path: Path) -> bool:
        """Determine if a file should be included in checksums."""
        return _should_include_file_simple(file_path, self.include_patterns, self.exclude_patterns)

    def generate_checksums_for_directory(self, directory: Path) -> Dict[str, Any]:
        """Generate checksums for all files in a directory (non-recursive)."""
        checksums = {}
        files_processed = 0
        files_skipped = 0
        files_failed = 0
        total_bytes = 0
        start_time = time.time()

        try:
            # Get all files in directory
            files = [f for f in directory.iterdir() if f.is_file()]

            # Use DazzleLogger for consistent output
            if dazzle_logger:
                dazzle_logger.info(f"Found {len(files)} files in {directory}", level=1)
            else:
                # Fallback for direct calls
                if self.log_file:
                    logger.debug(f"Found {len(files)} files in {directory}")
                elif not self.summary_mode:
                    logger.info(f"Found {len(files)} files in {directory}")

            for file_path in files:
                if not self.should_include_file(file_path):
                    files_skipped += 1
                    if dazzle_logger:
                        dazzle_logger.file_skipped(file_path)
                    elif self.log_file:
                        logger.debug(f"Skipped: {file_path}")
                    continue

                try:
                    if dazzle_logger:
                        dazzle_logger.file_processed(file_path)
                    elif self.log_file:
                        logger.debug(f"Processing file: {file_path}")

                    hash_value = self.calculator.calculate_file_hash(file_path)

                    # Get file stats
                    stat_info = file_path.stat()
                    file_size = stat_info.st_size
                    total_bytes += file_size

                    checksums[file_path.name] = {
                        'hash': hash_value,
                        'size': file_size,
                        'mtime': stat_info.st_mtime,
                        'algorithm': self.algorithm
                    }
                    files_processed += 1

                    # Update progress tracker
                    if self.progress_tracker:
                        self.progress_tracker.update_files(1)

                    if self.log_file:
                        logger.debug(f"Completed: {file_path} -> {hash_value}")

                except Exception as e:
                    files_failed += 1
                    if self.log_file:
                        logger.error(f"Error processing {file_path}: {e}")
                    elif not self.summary_mode:
                        logger.error(f"Error processing {file_path}: {e}")

        except Exception as e:
            if self.log_file:
                logger.error(f"Error listing directory {directory}: {e}")
            elif not self.summary_mode:
                logger.error(f"Error listing directory {directory}: {e}")

        elapsed_time = time.time() - start_time

        # Log results using DazzleLogger
        if dazzle_logger:
            dazzle_logger.directory_complete(directory, files_processed, files_skipped, files_failed, elapsed_time)
        else:
            # Fallback for direct calls
            if self.log_file:
                logger.info(f"Directory {directory}: {files_processed} processed, "
                           f"{files_skipped} skipped, {files_failed} failed in {elapsed_time:.2f}s")
            elif not self.summary_mode:
                logger.info(f"Directory {directory}: {files_processed} processed, "
                           f"{files_skipped} skipped in {elapsed_time:.2f}s")

        # Add to summary
        self.summary_collector.add_directory(files_processed, files_skipped, files_failed, total_bytes)

        return checksums

    def write_shasum_file(self, directory: Path, checksums: Dict[str, Any]):
        """Write checksums to .shasum file in native-compatible format."""
        shasum_path = directory / SHASUM_FILENAME

        try:
            with open(shasum_path, 'w', encoding='utf-8') as f:
                # Write header comment
                f.write(f"# Dazzle checksum tool v{__version__} - {self.algorithm} - {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")

                # Write checksums in standard format
                for filename, info in sorted(checksums.items()):
                    f.write(f"{info['hash']}  {filename}\n")

                # Write end marker
                f.write("# End of checksums\n")

            if self.log_file:
                logger.info(f"Wrote {len(checksums)} checksums to {shasum_path}")
            elif not self.summary_mode:
                logger.info(f"Wrote {len(checksums)} checksums to {shasum_path}")

        except Exception as e:
            if self.log_file:
                logger.error(f"Error writing .shasum file to {directory}: {e}")
            elif not self.summary_mode:
                logger.error(f"Error writing .shasum file to {directory}: {e}")

    def verify_checksums_in_directory(self, directory: Path) -> Dict[str, Any]:
        """Verify checksums in a directory against its .shasum file."""
        shasum_path = directory / SHASUM_FILENAME

        if not shasum_path.exists():
            return {'error': f"No {SHASUM_FILENAME} file found in {directory}"}

        results = {
            'verified': [],
            'failed': [],
            'missing': [],
            'extra': []
        }

        # Read existing checksums
        stored_checksums = {}
        try:
            with open(shasum_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('  ', 1)
                        if len(parts) == 2:
                            hash_value, filename = parts
                            stored_checksums[filename] = hash_value.lower()
        except Exception as e:
            return {'error': f"Error reading {shasum_path}: {e}"}

        # Check each stored checksum
        for filename, expected_hash in stored_checksums.items():
            file_path = directory / filename

            if not file_path.exists():
                results['missing'].append(filename)
                continue

            try:
                actual_hash = self.calculator.calculate_file_hash(file_path)
                if actual_hash.lower() == expected_hash.lower():
                    results['verified'].append(filename)
                    if self.log_file:
                        logger.debug(f"Verified: {filename}")
                else:
                    results['failed'].append({
                        'filename': filename,
                        'expected': expected_hash,
                        'actual': actual_hash
                    })
                    if self.log_file:
                        logger.error(f"Hash mismatch: {filename} - expected {expected_hash[:16]}... got {actual_hash[:16]}...")

                # Update progress tracker
                if self.progress_tracker:
                    self.progress_tracker.update_files(1)

            except Exception as e:
                results['failed'].append({
                    'filename': filename,
                    'error': str(e)
                })
                if self.log_file:
                    logger.error(f"Error verifying {filename}: {e}")

        # Check for extra files
        current_files = {f.name for f in directory.iterdir()
                        if f.is_file() and self.should_include_file(f)}
        stored_files = set(stored_checksums.keys())
        results['extra'] = list(current_files - stored_files)

        # Add to summary
        self.summary_collector.add_verification(results)

        return results

    def verify_monolithic_file(self, monolithic_file: Path, root_directory: Path) -> Dict[str, Any]:
        """Verify checksums from a monolithic file."""
        if not monolithic_file.exists():
            return {'error': f"Monolithic file not found: {monolithic_file}"}

        results = {
            'verified': [],
            'failed': [],
            'missing': [],
            'extra': []
        }

        # Read monolithic checksums
        stored_checksums = {}
        file_root = None

        try:
            with open(monolithic_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# Root directory:'):
                        # Extract root directory from header
                        file_root = line.split(':', 1)[1].strip()
                    elif line and not line.startswith('#'):
                        parts = line.split('  ', 1)
                        if len(parts) == 2:
                            hash_value, relative_path = parts
                            # Convert to platform-appropriate path separators
                            relative_path = relative_path.replace('/', os.sep)
                            stored_checksums[relative_path] = hash_value.lower()
        except Exception as e:
            return {'error': f"Error reading monolithic file: {e}"}

        # Determine base path for verification
        if file_root and Path(file_root).exists():
            base_path = Path(file_root)
        else:
            base_path = root_directory

        # Check each stored checksum
        for relative_path, expected_hash in stored_checksums.items():
            file_path = base_path / relative_path

            if not file_path.exists():
                results['missing'].append(relative_path)
                continue

            try:
                actual_hash = self.calculator.calculate_file_hash(file_path)
                if actual_hash.lower() == expected_hash.lower():
                    results['verified'].append(relative_path)
                    if self.log_file:
                        logger.debug(f"Verified: {relative_path}")
                else:
                    results['failed'].append({
                        'filename': relative_path,
                        'expected': expected_hash,
                        'actual': actual_hash
                    })
                    if self.log_file:
                        logger.error(f"Hash mismatch: {relative_path} - expected {expected_hash[:16]}... got {actual_hash[:16]}...")

                # Update progress tracker
                if self.progress_tracker:
                    self.progress_tracker.update_files(1)

            except Exception as e:
                results['failed'].append({
                    'filename': relative_path,
                    'error': str(e)
                })
                if self.log_file:
                    logger.error(f"Error verifying {relative_path}: {e}")

        # Note: Extra file detection is more complex for monolithic mode
        # We would need to recursively scan the directory tree and compare
        # This is left as a future enhancement

        # Add to summary
        self.summary_collector.add_verification(results)

        return results

    def process_directory_tree(self, root_directory: Path, recursive=True,
                             verify_only=False, update_mode=False):
        """Process an entire directory tree."""
        if not root_directory.exists():
            logger.error(f"Directory does not exist: {root_directory}")
            return

        if not root_directory.is_dir():
            logger.error(f"Path is not a directory: {root_directory}")
            return

        # Check for monolithic verification mode
        if verify_only and self.generate_monolithic:
            # Look for monolithic file
            if self.output_file:
                monolithic_file = Path(self.output_file)
            else:
                # Try default monolithic filename
                ext = f".{self.algorithm}"
                monolithic_file = root_directory / f"{MONOLITHIC_DEFAULT_NAME}{ext}"

            if monolithic_file.exists():
                results = self.verify_monolithic_file(monolithic_file, root_directory)
                if not self.summary_mode and not self.log_file:
                    self._print_verification_results(monolithic_file, results, self.show_all_verifications)
                elif self.log_file and 'error' not in results:
                    logger.info(f"Verified monolithic file: {monolithic_file}")
                return
            else:
                logger.error(f"Monolithic file not found: {monolithic_file}")
                return

        # Check for individual file verification of a potential monolithic file
        if verify_only and not recursive and not self.generate_monolithic:
            shasum_file = root_directory / SHASUM_FILENAME
            if shasum_file.exists() and is_monolithic_file(shasum_file):
                logger.info("Detected monolithic checksum file, using monolithic verification mode")
                results = self.verify_monolithic_file(shasum_file, root_directory)
                if not self.summary_mode and not self.log_file:
                    self._print_verification_results(shasum_file, results, self.show_all_verifications)
                return

        # Initialize progress tracking if summary mode
        if self.summary_mode:
            if not self.summary_mode:
                logger.info("Counting directories and files...")
            total_dirs, total_files = count_dirs_and_files(
                root_directory, self.include_patterns, self.exclude_patterns, self.follow_symlinks
            )
            self.progress_tracker = ProgressTracker(total_dirs, total_files, True)
            if not self.summary_mode:
                logger.info(f"Found {total_dirs} directories, {total_files} files to process")

        # Set up monolithic writer if needed
        monolithic_writer = None
        if self.generate_monolithic and not verify_only:
            if not recursive:
                logger.error("Monolithic mode requires --recursive flag")
                return

            # Determine output file path
            if self.output_file:
                output_path = Path(self.output_file)
                if not output_path.is_absolute():
                    output_path = root_directory / output_path
            else:
                # Default monolithic filename
                ext = f".{self.algorithm}"
                output_path = root_directory / f"{MONOLITHIC_DEFAULT_NAME}{ext}"

            monolithic_writer = MonolithicWriter(output_path, root_directory, self.algorithm)

        walker = FIFODirectoryWalker(self.follow_symlinks)

        def process_single_directory(directory: Path):
            if verify_only:
                if self.generate_monolithic:
                    # This shouldn't happen as we handle it above
                    logger.error("Monolithic verification should be handled before directory walking")
                else:
                    results = self.verify_checksums_in_directory(directory)
                    if not self.summary_mode and not self.log_file:
                        self._print_verification_results(directory, results, self.show_all_verifications)
                    elif self.log_file and 'error' not in results:
                        logger.info(f"Verified directory: {directory}")
            else:
                checksums = self.generate_checksums_for_directory(directory)
                if checksums:
                    # Write to monolithic file if enabled
                    if monolithic_writer and self.generate_monolithic:
                        monolithic_writer.append_directory_checksums(directory, checksums)

                    # Write individual .shasum file if enabled
                    if self.generate_individual:
                        self.write_shasum_file(directory, checksums)

            # Update progress tracker
            if self.progress_tracker:
                self.progress_tracker.update_dirs(1)

        if not self.summary_mode:
            logger.info(f"Starting {'recursive ' if recursive else ''}processing of {root_directory}")

        start_time = time.time()

        try:
            if monolithic_writer:
                with monolithic_writer:
                    walker.walk_and_process(root_directory, process_single_directory, recursive)
            else:
                walker.walk_and_process(root_directory, process_single_directory, recursive)
        except Exception as e:
            logger.error(f"Error during directory processing: {e}")
            if monolithic_writer and monolithic_writer._is_open:
                monolithic_writer.close(success=False)
            raise

        # Finish progress tracking
        if self.progress_tracker:
            self.progress_tracker.finish()

        elapsed_time = time.time() - start_time

        if not self.summary_mode:
            logger.info(f"Completed processing {walker.processed_count} directories in {elapsed_time:.2f}s")

        # Print summary if in summary mode
        if self.summary_mode:
            self.summary_collector.print_summary()

    def _print_verification_results(self, path: Path, results: Dict[str, Any], show_all=False):
        """Print verification results for a directory or monolithic file."""
        if 'error' in results:
            if dazzle_logger:
                dazzle_logger.error(f"{path}: {results['error']}")
            else:
                logger.error(f"{path}: {results['error']}")
            return

        verified_count = len(results['verified'])
        failed_count = len(results['failed'])
        missing_count = len(results['missing'])
        extra_count = len(results['extra'])

        # Show individual file results if requested or verbose
        if show_all or (dazzle_logger and dazzle_logger.verbosity >= 2):
            # Show all verification results
            for filename in results['verified']:
                logger.info(f"  OK {filename}")

        # Always show problems
        if failed_count > 0:
            for item in results['failed']:
                if isinstance(item, dict):
                    if 'error' in item:
                        if dazzle_logger:
                            dazzle_logger.error(f"  ERROR {item['filename']}: {item['error']}")
                        else:
                            logger.error(f"  ERROR {item['filename']}: {item['error']}")
                    else:
                        # Always show hash mismatches (problems)
                        if dazzle_logger:
                            logger.error(f"  FAIL {item['filename']}: "
                                       f"expected {item['expected'][:16]}... "
                                       f"got {item['actual'][:16]}...")
                        else:
                            logger.error(f"  FAIL {item['filename']}: "
                                       f"expected {item['expected'][:16]}... "
                                       f"got {item['actual'][:16]}...")

        if missing_count > 0:
            for filename in results['missing']:
                # Always show missing files (problems)
                logger.warning(f"  MISS {filename}")

        if extra_count > 0:
            for filename in results['extra']:
                # Always show extra files (problems)
                logger.warning(f"  EXTRA {filename}")

        # Summary line
        if failed_count == 0 and missing_count == 0:
            status = "OK"
            if dazzle_logger:
                dazzle_logger.info(f"{status} {path}: {verified_count} verified, "
                                 f"{failed_count} failed, {missing_count} missing, {extra_count} extra")
            else:
                logger.info(f"{status} {path}: {verified_count} verified, "
                           f"{failed_count} failed, {missing_count} missing, {extra_count} extra")
        else:
            status = "FAIL"
            if dazzle_logger:
                dazzle_logger.error(f"{status} {path}: {verified_count} verified, "
                                  f"{failed_count} failed, {missing_count} missing, {extra_count} extra")
            else:
                logger.error(f"{status} {path}: {verified_count} verified, "
                           f"{failed_count} failed, {missing_count} missing, {extra_count} extra")


def create_argument_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Dazzle Cross-Platform Checksum Tool",
        epilog="""
Examples:
  %(prog)s                              # Current directory only
  %(prog)s --recursive /path/to/dir     # Recursive processing
  %(prog)s --algorithm sha512           # Use SHA-512
  %(prog)s --verify                     # Verify existing checksums
  %(prog)s --include "*.txt,*.doc"      # Include only specific patterns
  %(prog)s --exclude "*.tmp,*.log"      # Exclude specific patterns
  %(prog)s --recursive --mode monolithic # Single checksum file for tree
  %(prog)s --recursive --mode both      # Both individual and monolithic files
  %(prog)s --mode monolithic --output all.sha256  # Custom monolithic output
  %(prog)s -r --manage backup --backup-dir ./backup  # Backup all .shasum files
  %(prog)s -r --manage remove           # Remove all .shasum files
  %(prog)s -r --manage restore --backup-dir ./backup # Restore from backup
  %(prog)s -r --manage list             # List all .shasum files
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional arguments
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to process (default: current directory)')

    # Algorithm options
    parser.add_argument('--algorithm', '-a', choices=SUPPORTED_ALGORITHMS,
                       default=DEFAULT_ALGORITHM,
                       help=f'Hash algorithm (default: {DEFAULT_ALGORITHM})')

    # Processing options
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Process subdirectories recursively')
    parser.add_argument('--follow-symlinks', action='store_true',
                       help='Follow symbolic links and junctions')

    # Operation modes
    parser.add_argument('--verify', action='store_true',
                       help='Verify existing checksums instead of generating')
    parser.add_argument('--update', '-u', action='store_true',
                       help='Update existing checksums (incremental)')

    # Management operations (mutually exclusive with generation)
    parser.add_argument('--manage', choices=['backup', 'remove', 'restore', 'list'],
                       help='Manage existing .shasum files instead of generating new ones')
    parser.add_argument('--backup-dir', metavar='DIR',
                       help='Directory for .shasum backup/restore operations')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')

    # Checksum generation mode
    parser.add_argument('--mode', choices=['individual', 'monolithic', 'both'],
                       default='individual',
                       help='Checksum file generation mode (default: individual)')
    parser.add_argument('--output', metavar='FILE',
                       help='Output filename for monolithic mode or custom location')

    # File filtering
    parser.add_argument('--include', action='append',
                       help='Include file patterns (can specify multiple)')
    parser.add_argument('--exclude', action='append',
                       help='Exclude file patterns (can specify multiple)')

    # Line ending handling
    parser.add_argument('--line-endings', choices=['auto', 'unix', 'windows', 'preserve'],
                       default='auto', help='Line ending normalization strategy')

    # Output options
    parser.add_argument('--compatible', action='store_true',
                       help='Generate output compatible with standard tools (no comments)')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                       help='Increase verbosity level (use -v, -vv, or -vvv)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress output (errors and warnings only)')
    parser.add_argument('--log', metavar='FILE',
                       help='Write detailed log to file')
    parser.add_argument('--summary', action='store_true',
                       help='Show progress bar and summary (less verbose console output)')

    # Tool options
    parser.add_argument('--force-python', action='store_true',
                       help='Force use of Python implementation (skip native tools)')
    parser.add_argument('-y', '--yes', action='store_true',
                       help='Auto-accept prompts (assume --recursive for monolithic verify)')
    parser.add_argument('--show-all-verifications', action='store_true',
                       help='Show all verification results, not just problems (use with --verify)')

    # Version
    parser.add_argument('--version', action='version',
                       version=f'%(prog)s {__version__}')

    return parser


def setup_logging(verbosity=0, quiet=False):
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.WARNING
    elif verbosity >= 3:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure root logger
    logging.getLogger().setLevel(level)

    # Create a more detailed formatter for debug mode
    if verbosity >= 3:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
    else:
        formatter = logging.Formatter('%(levelname)s - %(message)s')

    # Update handler formatter
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
        handler.setLevel(level)


def main():
    """Main entry point."""
    try:
        parser = create_argument_parser()
        args = parser.parse_args()

        # Validate argument combinations
        if args.summary and args.verbose > 0:
            logger.error("Cannot use --summary and --verbose together")
            return 1

        if args.summary and args.quiet:
            logger.error("Cannot use --summary and --quiet together")
            return 1

        # Validate mode requirements
        if args.mode in ['monolithic', 'both'] and not args.recursive and not args.verify:
            logger.error("Monolithic modes require --recursive flag")
            return 1

        # Validate management operation requirements
        if args.manage:
            if args.manage in ['backup', 'restore'] and not args.backup_dir:
                logger.error(f"--backup-dir is required for --manage {args.manage}")
                return 1
            if args.verify or args.update:
                logger.error("--manage cannot be used with --verify or --update")
                return 1

        # Setup logging
        setup_logging(args.verbose, args.quiet or args.summary)

        # Initialize enhanced logger
        global dazzle_logger
        dazzle_logger = DazzleLogger(
            verbosity=args.verbose,
            quiet=args.quiet,
            summary_mode=args.summary
        )

        # Log startup info
        dazzle_logger.info(f"Dazzle Checksum Tool v{__version__}", level=0)

        if args.verbose >= 3:
            dazzle_logger.debug(f"Platform: {platform.platform()}")
            dazzle_logger.debug(f"Python: {platform.python_version()}")
            dazzle_logger.debug(f"UNCtools available: {HAVE_UNCTOOLS}")
            dazzle_logger.debug(f"is_windows(): {is_windows()}")

        # Validate directory
        directory = Path(args.directory).resolve()
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return 1

        if not directory.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            return 1

        # Handle management operations (mutually exclusive with generation)
        if args.manage:
            dazzle_logger.info(f"Starting {args.manage} operation on {directory}")

            manager = ShasumManager(
                root_dir=directory,
                backup_dir=Path(args.backup_dir) if args.backup_dir else None,
                dry_run=args.dry_run
            )

            try:
                if args.manage == 'backup':
                    results = manager.backup_shasums()
                    if results['errors']:
                        return 1

                elif args.manage == 'remove':
                    results = manager.remove_shasums(force=args.yes)
                    if results['errors']:
                        return 1

                elif args.manage == 'restore':
                    results = manager.restore_shasums()
                    if results['errors']:
                        return 1

                elif args.manage == 'list':
                    results = manager.list_shasums()

                dazzle_logger.info(f"Management operation '{args.manage}' completed successfully")
                return 0

            except Exception as e:
                logger.error(f"Management operation failed: {e}")
                if args.verbose >= 3:
                    import traceback
                    logger.debug(traceback.format_exc())
                return 1

        # Handle smart monolithic verification logic
        if args.mode in ['monolithic', 'both'] and args.verify and not args.recursive:
            # Check for monolithic file
            if args.output:
                monolithic_file = Path(args.output)
                if not monolithic_file.is_absolute():
                    monolithic_file = directory / monolithic_file
            else:
                # Try .shasum first, then default monolithic name
                shasum_file = directory / SHASUM_FILENAME
                default_mono = directory / f"{MONOLITHIC_DEFAULT_NAME}.{args.algorithm}"

                if shasum_file.exists() and is_monolithic_file(shasum_file):
                    monolithic_file = shasum_file
                elif default_mono.exists():
                    monolithic_file = default_mono
                else:
                    dazzle_logger.error(f"No monolithic checksum file found in {directory}")
                    dazzle_logger.info("Looked for: .shasum (monolithic) or checksums.{algorithm}")
                    return 1

            if monolithic_file.exists() and is_monolithic_file(monolithic_file):
                if not args.yes:
                    dazzle_logger.warning("Monolithic file detected - this implies --recursive verification")
                    dazzle_logger.info("Use -y/--yes to auto-accept, or add --recursive manually")
                    response = input("Continue with recursive verification? [y/N]: ")
                    if response.lower() not in ['y', 'yes']:
                        dazzle_logger.info("Verification cancelled")
                        return 0

                # Auto-enable recursive for monolithic verification
                args.recursive = True
                dazzle_logger.info("Auto-enabled --recursive for monolithic verification")

        # Process include/exclude patterns
        include_patterns = []
        if args.include:
            for pattern_group in args.include:
                include_patterns.extend(p.strip() for p in pattern_group.split(','))

        exclude_patterns = []
        if args.exclude:
            for pattern_group in args.exclude:
                exclude_patterns.extend(p.strip() for p in pattern_group.split(','))

        # Determine generation modes based on --mode
        generate_individual = False
        generate_monolithic = False

        if args.mode == 'individual':
            generate_individual = True
        elif args.mode == 'monolithic':
            generate_monolithic = True
        elif args.mode == 'both':
            generate_individual = True
            generate_monolithic = True

        # Create checksum generator
        generator = ChecksumGenerator(
            algorithm=args.algorithm,
            line_ending_strategy=args.line_endings,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            follow_symlinks=args.follow_symlinks,
            log_file=args.log,
            summary_mode=args.summary,
            generate_individual=generate_individual,
            generate_monolithic=generate_monolithic,
            output_file=args.output,
            show_all_verifications=args.show_all_verifications
        )

        # Force Python implementation if requested
        if args.force_python:
            generator.calculator.native_tool = None
            if not args.summary:
                logger.info("Forcing Python implementation")

        # Log generation mode if not verifying
        if not args.verify:
            mode_descriptions = {
                'individual': 'Individual .shasum files per directory',
                'monolithic': 'Single monolithic checksum file',
                'both': 'Both individual and monolithic files'
            }
            dazzle_logger.info(f"Mode: {mode_descriptions[args.mode]}", level=1)

        # Process directory tree
        generator.process_directory_tree(
            directory,
            recursive=args.recursive,
            verify_only=args.verify,
            update_mode=args.update
        )

        if not args.summary:
            logger.info("Processing completed successfully")

        return 0

    except KeyboardInterrupt:
        print()  # New line after progress bar if interrupted
        logger.info("Operation interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Show traceback in verbose mode if args is available
        try:
            if args.verbose >= 3:
                import traceback
                logger.debug(traceback.format_exc())
        except NameError:
            # args not available, show traceback anyway for debugging
            import traceback
            logger.debug(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
