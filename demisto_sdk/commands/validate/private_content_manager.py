"""
Private Content Manager for syncing private content into the Git-based Content Graph.

This module provides a context manager that:
1. Copies packs from a private content path into the Packs/ directory
2. Stages the copied files to Git so ContentGraphInterface can see them
3. Cleans up (removes files and unstages) on exit, even on interruption (SIGINT/SIGTERM)
"""

from __future__ import annotations

import atexit
import shutil
import signal

# from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.logger import logger

if TYPE_CHECKING:
    from git import Repo


class PrivateContentManager:
    """
    Context manager for syncing private content packs into the main content repository.

    This class handles:
    - Copying packs from a private content path to the main content Packs/ directory
    - Staging the copied files to Git (so the graph builder can see them)
    - Cleanup on exit (removing copied files and unstaging from Git index)
    - Signal handling to ensure cleanup happens even on interruption (Ctrl+C)

    Usage:
        with PrivateContentManager(
            private_content_path=Path("/path/to/private/content"),
            content_path=Path("/path/to/content")
        ) as manager:
            # Private packs are now copied and staged
            # Build the graph here
            pass
        # Cleanup happens automatically
    """

    # Class-level tracking for cleanup on unexpected termination
    _active_instance: Optional["PrivateContentManager"] = None
    _original_sigint_handler = None
    _original_sigterm_handler = None

    def __init__(
        self,
        private_content_path: Path,
        content_path: Path,
    ):
        """
        Initialize the PrivateContentManager.

        Args:
            private_content_path: Path to the private content repository containing Packs/
            content_path: Path to the main content repository
        """
        self.private_content_path = Path(private_content_path)
        self.content_path = content_path
        self.copied_paths: Set[Path] = set()
        self.staged_files: List[str] = []
        self._repo: Optional["Repo"] = None
        self._cleanup_done = False

    @property
    def repo(self) -> "Repo":
        """Lazy-load the Git repository."""
        if self._repo is None:
            from git import Repo

            self._repo = Repo(self.content_path)
        return self._repo

    def _get_private_packs_path(self) -> Path:
        """Get the Packs directory from the private content path."""
        return self.private_content_path / PACKS_DIR

    def _get_content_packs_path(self) -> Path:
        """Get the Packs directory from the main content path."""
        return self.content_path / PACKS_DIR

    def _should_ignore_path(self, path: Path) -> bool:
            """
            Check if the file/folder should be ignored based on the pattern:
            Packs/**/ModelingRules/**/**/*_testdata.json
            """
            return (
                path.suffix == ".json" and 
                path.name.endswith("_testdata.json") and 
                "ModelingRules" in path.parts
            )

    def copy_private_packs(self) -> Set[Path]:
        """
        Entry point to copy private packs. 
        Tries to copy the highest level of 'new' content found.
        """
        private_packs_path = self._get_private_packs_path()
        content_packs_path = self._get_content_packs_path()

        for path in [private_packs_path, content_packs_path]:
            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")

        self.copied_paths.clear()

        for pack_dir in private_packs_path.iterdir():
            if pack_dir.is_dir():
                destination_pack = content_packs_path / pack_dir.name
                # Start the recursive search for the first missing level
                self._copy_first_missing_level(pack_dir, destination_pack)

        logger.info(f"Copied {len(self.copied_paths)} private items to repository.")
        return self.copied_paths

    def _copy_first_missing_level(self, source: Path, destination: Path):
        """
        Recursively finds the first level that does not exist in the destination.
        Copies that level entirely and stops descending.
        """
        if self._should_ignore_path(source):
            logger.debug(f"Skipping ignored private file: {source.name}")
            return

        if not destination.exists():
            # Found the 'first level' that doesn't exist.
            try:
                if source.is_dir():
                    shutil.copytree(
                        source,
                        destination,
                        ignore=shutil.ignore_patterns('*_testdata.json') if "ModelingRules" in source.parts or source.name == "ModelingRules" else None
                    )
                else:
                    shutil.copy2(source, destination)

                self.copied_paths.add(destination)
                logger.debug(f"Copied new content: {destination.relative_to(self.content_path)}")
            except Exception as e:
                logger.error(f"Failed to copy '{source.name}' to '{destination}': {e}")
                raise

        elif source.is_dir():
            # If the folder exists, we must go deeper to find specific missing items
            for item in source.iterdir():
                self._copy_first_missing_level(item, destination / item.name)

        else:
            # File exists in both destination and source; skip it
            logger.debug(f"Skipping existing file: {destination.name}")

    def stage_copied_files(self) -> List[str]:
        """
        Stage all copied files to the Git index.

        This makes the files visible to the ContentGraphInterface during graph building.
        Handles both individual files and directories in copied_paths.

        Returns:
            List of relative file paths that were staged.
        """
        if not self.copied_paths:
            logger.debug("No copied paths to stage")
            return []

        staged_files: List[str] = []

        for copied_path in self.copied_paths:
            if copied_path.is_file():
                # Stage individual file
                try:
                    relative_path = copied_path.relative_to(self.content_path)
                    self.repo.git.add(str(relative_path))
                    staged_files.append(str(relative_path))
                except Exception as e:
                    logger.error(f"Failed to stage file '{copied_path}': {e}")
            elif copied_path.is_dir():
                # Stage all files in the directory
                for file_path in copied_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            relative_path = file_path.relative_to(self.content_path)
                            self.repo.git.add(str(relative_path))
                            staged_files.append(str(relative_path))
                        except Exception as e:
                            logger.error(f"Failed to stage file '{file_path}': {e}")

        self.staged_files = staged_files
        logger.info(f"Staged {len(staged_files)} file(s) from private content")
        return staged_files

    def cleanup(self) -> None:
        """
        Clean up all copied files and unstage them from Git.

        This method is idempotent - it can be called multiple times safely.
        """
        if self._cleanup_done:
            logger.debug("Cleanup already performed, skipping")
            return

        logger.info("Cleaning up private content files...")

        # First, unstage all files from Git index
        self._unstage_files()

        # Then, remove the copied files and directories
        self._remove_copied_paths()

        self._cleanup_done = True
        logger.info("Private content cleanup completed")

    def _unstage_files(self) -> None:
        """Unstage all staged files from the Git index."""
        if not self.staged_files:
            return

        try:
            # Use git reset to unstage files without affecting working directory
            # We need to unstage only the specific files we added

            try:
                self.repo.git.reset("HEAD", "--", *self.staged_files)
            except Exception as e:
                # File might already be unstaged or removed
                logger.debug(f"Could not unstage files: {e}")

            logger.debug(f"Unstaged {len(self.staged_files)} file(s)")
        except Exception as e:
            logger.error(f"Error during unstaging: {e}")
        finally:
            self.staged_files = []

    def _remove_copied_paths(self) -> None:
        """Remove all copied files and directories."""
        for copied_path in list(self.copied_paths):
            try:
                if copied_path.exists():
                    if copied_path.is_dir():
                        shutil.rmtree(copied_path)
                        logger.debug(f"Removed copied directory: {copied_path.name}")
                    else:
                        copied_path.unlink()
                        logger.debug(f"Removed copied file: {copied_path.name}")

            except Exception as e:
                logger.error(f"Failed to remove '{copied_path}': {e}")
            finally:
                self.copied_paths.discard(copied_path)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers to ensure cleanup on interruption."""
        PrivateContentManager._active_instance = self

        # Store original handlers
        PrivateContentManager._original_sigint_handler = signal.getsignal(signal.SIGINT)
        PrivateContentManager._original_sigterm_handler = signal.getsignal(
            signal.SIGTERM
        )

        # Set up new handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Also register with atexit for additional safety
        atexit.register(self._atexit_cleanup)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if PrivateContentManager._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, PrivateContentManager._original_sigint_handler)
            PrivateContentManager._original_sigint_handler = None

        if PrivateContentManager._original_sigterm_handler is not None:
            signal.signal(
                signal.SIGTERM, PrivateContentManager._original_sigterm_handler
            )
            PrivateContentManager._original_sigterm_handler = None

        PrivateContentManager._active_instance = None

        # Unregister atexit handler
        try:
            atexit.unregister(self._atexit_cleanup)
        except Exception:
            pass

    @staticmethod
    def _signal_handler(signum: int, frame) -> None:
        """Handle signals by performing cleanup before exiting."""
        logger.warning(f"Received signal {signum}, performing cleanup...")

        if PrivateContentManager._active_instance is not None:
            PrivateContentManager._active_instance.cleanup()

        # Re-raise the signal with the original handler
        original_handler = None
        if signum == signal.SIGINT:
            original_handler = PrivateContentManager._original_sigint_handler
        elif signum == signal.SIGTERM:
            original_handler = PrivateContentManager._original_sigterm_handler

        if original_handler and callable(original_handler):
            original_handler(signum, frame)
        else:
            # Default behavior - raise KeyboardInterrupt for SIGINT
            if signum == signal.SIGINT:
                raise KeyboardInterrupt
            else:
                raise SystemExit(1)

    def _atexit_cleanup(self) -> None:
        """Cleanup handler for atexit."""
        if not self._cleanup_done:
            logger.debug("Performing atexit cleanup")
            self.cleanup()

    def __enter__(self) -> "PrivateContentManager":
        """Enter the context manager."""
        logger.info(
            f"Setting up private content sync from: {self.private_content_path}"
        )

        # Set up signal handlers for cleanup on interruption
        self._setup_signal_handlers()

        try:
            # Copy private packs to content directory
            self.copy_private_packs()

            # Stage the copied files to Git
            self.stage_copied_files()

            return self
        except Exception:
            # If setup fails, clean up and re-raise
            self.cleanup()
            self._restore_signal_handlers()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the context manager, performing cleanup."""
        try:
            self.cleanup()
        finally:
            self._restore_signal_handlers()

        # Don't suppress exceptions
        return False
