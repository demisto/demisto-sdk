"""
Unified Connector Content Manager for syncing external UCC connectors into the
Git-based Content Graph.

This mirrors :mod:`private_content_manager` but targets the ``connectors/``
directory instead of ``Packs/``. The Unified Connector Content (UCC) repository
does not have a ``Packs/`` layout - it only has ``connectors/<name>/...`` at the
repo root - so we only need to sync that subtree into the main content
checkout.

Behavior (mirrors PrivateContentManager, but for connectors):
1. Copies connectors from an external UCC path into ``<content>/connectors/``.
2. Stages the copied files to Git so ``ContentGraphInterface`` can see them.
3. Cleans up (removes files, unstages from Git, optionally removes the
   ``connectors/`` root if we created it) on exit, even on interruption
   (SIGINT/SIGTERM).

The two managers use *independent* class-level signal-handler state so they can
be nested safely inside a single ``contextlib.ExitStack`` when a user passes
both ``--private-content-path`` and ``--connectors-content-path`` to
``validate -a``.
"""

from __future__ import annotations

import atexit
import shutil
import signal
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Set

from demisto_sdk.commands.common.constants import CONNECTORS_FOLDER
from demisto_sdk.commands.common.logger import logger

if TYPE_CHECKING:
    from demisto_sdk.commands.common.git_util import GitUtil


class UnifiedConnectorContentManager:
    """
    Context manager for syncing external Unified Connector Content (UCC)
    connectors into the main content repository.

    This class handles:
    - Copying connectors from a UCC path (``<ucc>/connectors/*``) into the main
      content ``connectors/`` directory (creating the destination root if it
      does not yet exist).
    - Staging the copied files to Git (so the graph builder can see them).
    - Cleanup on exit (removing copied files, unstaging from Git index, and
      removing the destination ``connectors/`` root if we created it).
    - Signal handling to ensure cleanup happens even on interruption (Ctrl+C).

    Usage:
        with UnifiedConnectorContentManager(
            connectors_content_path=Path("/path/to/ucc"),
            content_path=Path("/path/to/content"),
        ) as manager:
            # UCC connectors are now copied under <content>/connectors/ and
            # staged. Build the graph / run validate here.
            pass
        # Cleanup happens automatically.
    """

    # Class-level tracking for cleanup on unexpected termination.
    # These are intentionally *separate* from PrivateContentManager's so both
    # managers can be nested inside a single ExitStack without one clobbering
    # the other's signal handlers.
    _active_instance: Optional["UnifiedConnectorContentManager"] = None
    _usage_count = 0
    _original_sigint_handler = None
    _original_sigterm_handler = None

    def __init__(
        self,
        connectors_content_path: Path,
        content_path: Path,
        changed_only: bool = False,
    ):
        """
        Initialize the UnifiedConnectorContentManager.

        Args:
            connectors_content_path: Path to the Unified Connector Content
                repository (must contain a ``connectors/`` directory).
            content_path: Path to the main content repository.
            changed_only: When ``True`` (used for ``-g``/USE_GIT), copy only the
                connectors that were actually changed in the UCC repo's own git
                diff, instead of copying every connector. When ``False`` (used
                for ``-a``/ALL_FILES), copy all connectors. In ``-g`` the graph
                only reparses the changed connectors, so copying the unchanged
                ones is unnecessary work.
        """
        self.connectors_content_path = Path(connectors_content_path)
        self.content_path = Path(content_path)
        self.changed_only = changed_only
        self.copied_paths: Set[Path] = set()
        self.staged_files: List[str] = []
        self._git_util: Optional["GitUtil"] = None
        self._cleanup_done = False
        # Track whether we created <content>/connectors/ ourselves so cleanup
        # can remove it. If it pre-existed we leave it alone.
        self._created_dest_root = False

    @property
    def git_util(self) -> "GitUtil":
        """Lazy-load the GitUtil."""
        if self._git_util is None:
            from demisto_sdk.commands.common.git_util import GitUtil

            self._git_util = GitUtil(self.content_path)
        return self._git_util

    def _get_source_connectors_path(self) -> Path:
        """Get the connectors/ directory in the UCC source repo."""
        return self.connectors_content_path / CONNECTORS_FOLDER

    def _get_dest_connectors_path(self) -> Path:
        """Get the connectors/ directory in the main content repo."""
        return self.content_path / CONNECTORS_FOLDER

    def _get_changed_connector_names(self) -> Set[str]:
        """
        Compute the set of top-level connector directory names that were changed
        in the UCC repo's own git diff (modified/added/renamed).

        Used only when ``changed_only`` is set (``-g``/USE_GIT) to scope the
        copy to the connectors that actually changed. The diff is run against
        the UCC repo itself (not the main content repo), mirroring
        ``Initializer.collect_files_to_run``.

        Returns:
            Set of connector directory names (e.g. ``{"MyConnector"}``). An
            empty set means nothing under ``connectors/`` changed.
        """
        from demisto_sdk.commands.common.git_util import GitUtil

        connectors_git_util = GitUtil(self.connectors_content_path)
        changed_files = connectors_git_util.get_all_changed_files()

        connector_names: Set[str] = set()
        for changed_file in changed_files:
            parts = changed_file.parts
            # We only care about files under connectors/<connector_name>/...
            if len(parts) >= 2 and parts[0] == CONNECTORS_FOLDER:
                connector_names.add(parts[1])
        return connector_names

    def copy_connectors(self) -> Set[Path]:
        """
        Entry point to copy UCC connectors.

        Tries to copy the highest level of 'new' content found, mirroring the
        behavior of :meth:`PrivateContentManager.copy_private_packs`.

        Creates ``<content>/connectors/`` if it does not exist yet and records
        that fact so cleanup can undo it.

        When ``changed_only`` is set (``-g``/USE_GIT), only the connectors
        changed in the UCC repo's git diff are copied - the graph only reparses
        those, so copying the unchanged connectors would be wasted work.
        """
        source_connectors_path = self._get_source_connectors_path()
        dest_connectors_path = self._get_dest_connectors_path()

        if not source_connectors_path.exists():
            raise FileNotFoundError(
                f"Directory not found: {source_connectors_path}. "
                f"Expected a 'connectors/' directory under "
                f"{self.connectors_content_path}."
            )

        # The main content repo may not have a connectors/ dir yet (e.g. a
        # plain content checkout without the unified branch). Create it and
        # remember so cleanup can undo it.
        if not dest_connectors_path.exists():
            dest_connectors_path.mkdir(parents=True, exist_ok=False)
            self._created_dest_root = True
            logger.debug(f"Created destination connectors root: {dest_connectors_path}")

        self.copied_paths.clear()

        changed_connector_names: Optional[Set[str]] = None
        if self.changed_only:
            changed_connector_names = self._get_changed_connector_names()
            logger.info(
                f"USE_GIT mode: copying only {len(changed_connector_names)} "
                f"changed connector(s): {sorted(changed_connector_names)}"
            )

        for connector_dir in source_connectors_path.iterdir():
            if changed_connector_names is not None and (
                connector_dir.name not in changed_connector_names
            ):
                # In USE_GIT mode, skip connectors that were not changed.
                continue
            if connector_dir.is_dir():
                destination_connector = dest_connectors_path / connector_dir.name
                # Start the recursive search for the first missing level
                self._copy_first_missing_level(connector_dir, destination_connector)
            elif connector_dir.is_file():
                # Rare, but handle top-level files under connectors/ too.
                destination_file = dest_connectors_path / connector_dir.name
                self._copy_first_missing_level(connector_dir, destination_file)

        logger.info(
            f"Copied {len(self.copied_paths)} UCC connector item(s) to repository."
        )
        return self.copied_paths

    def _copy_first_missing_level(self, source: Path, destination: Path):
        """
        Recursively finds the first level that does not exist in the destination.
        Copies that level entirely and stops descending.
        """
        if not destination.exists():
            # Found the 'first level' that doesn't exist.
            try:
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)

                self.copied_paths.add(destination)
                logger.debug(
                    f"Copied new connector content: "
                    f"{destination.relative_to(self.content_path)}"
                )
            except Exception as e:
                logger.error(f"Failed to copy '{source.name}' to '{destination}': {e}")
                raise

        elif source.is_dir():
            # If the folder exists, we must go deeper to find specific missing items
            for item in source.iterdir():
                self._copy_first_missing_level(item, destination / item.name)

        else:
            # File exists in both destination and source. We keep the existing
            # local copy (mirroring PrivateContentManager), but warn loudly:
            # otherwise validation would silently run against a stale local
            # connector instead of the UCC version the user pointed at.
            logger.warning(
                f"Connector file already exists locally and will NOT be "
                f"overwritten by the UCC version: "
                f"{destination.relative_to(self.content_path)}. "
                f"Validation will run against the existing local copy."
            )

    def stage_copied_files(self) -> List[str]:
        """
        Stage all copied files to the Git index.

        This makes the files visible to the ContentGraphInterface during graph
        building. Handles both individual files and directories in
        ``copied_paths``.

        Returns:
            List of relative file paths that were staged.
        """
        if not self.copied_paths:
            logger.debug("No copied paths to stage")
            return []

        staged_files: List[str] = []

        for copied_path in self.copied_paths:
            if copied_path.is_file():
                try:
                    relative_path = copied_path.relative_to(self.content_path)
                    self.git_util.repo.git.add(str(relative_path))
                    staged_files.append(str(relative_path))
                except Exception as e:
                    logger.error(f"Failed to stage file '{copied_path}': {e}")
            elif copied_path.is_dir():
                for file_path in copied_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            relative_path = file_path.relative_to(self.content_path)
                            self.git_util.repo.git.add(str(relative_path))
                            staged_files.append(str(relative_path))
                        except Exception as e:
                            logger.error(f"Failed to stage file '{file_path}': {e}")

        self.staged_files = staged_files
        logger.info(
            f"Staged {len(staged_files)} file(s) from unified connector content"
        )
        return staged_files

    def cleanup(self) -> None:
        """
        Clean up all copied files and unstage them from Git.

        This method is idempotent - it can be called multiple times safely.
        """
        if self._cleanup_done:
            logger.debug("Cleanup already performed, skipping")
            return

        logger.info("Cleaning up unified connector content files...")

        # First, unstage all files from Git index
        self._unstage_files()

        # Then, remove the copied files and directories
        self._remove_copied_paths()

        # Finally, if we created <content>/connectors/ ourselves and it is now
        # empty, remove it too so the working tree is byte-identical to how we
        # found it.
        if self._created_dest_root:
            dest_root = self._get_dest_connectors_path()
            try:
                if dest_root.exists() and not any(dest_root.iterdir()):
                    dest_root.rmdir()
                    logger.debug(
                        f"Removed destination connectors root we created: "
                        f"{dest_root}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to remove destination connectors root "
                    f"'{dest_root}': {e}"
                )
            finally:
                self._created_dest_root = False

        self._cleanup_done = True
        logger.info("Unified connector content cleanup completed")

    def _unstage_files(self) -> None:
        """Unstage all staged files from the Git index."""
        if not self.staged_files:
            return

        try:
            try:
                self.git_util.repo.git.reset("HEAD", "--", *self.staged_files)
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
        UnifiedConnectorContentManager._active_instance = self

        # Store original handlers (these may themselves be another manager's
        # handler, e.g. PrivateContentManager's - the chain is preserved).
        UnifiedConnectorContentManager._original_sigint_handler = signal.getsignal(
            signal.SIGINT
        )
        UnifiedConnectorContentManager._original_sigterm_handler = signal.getsignal(
            signal.SIGTERM
        )

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Also register with atexit for additional safety
        atexit.register(self._atexit_cleanup)

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if UnifiedConnectorContentManager._original_sigint_handler is not None:
            signal.signal(
                signal.SIGINT,
                UnifiedConnectorContentManager._original_sigint_handler,
            )
            UnifiedConnectorContentManager._original_sigint_handler = None

        if UnifiedConnectorContentManager._original_sigterm_handler is not None:
            signal.signal(
                signal.SIGTERM,
                UnifiedConnectorContentManager._original_sigterm_handler,
            )
            UnifiedConnectorContentManager._original_sigterm_handler = None

        UnifiedConnectorContentManager._active_instance = None

        # Unregister atexit handler
        try:
            atexit.unregister(self._atexit_cleanup)
        except ValueError:
            # Best-effort cleanup: handler may already be unregistered.
            logger.debug("Atexit cleanup handler was already unregistered.")
        except Exception as e:
            # Do not fail teardown, but keep visibility into unexpected issues.
            logger.debug(f"Failed to unregister atexit cleanup handler: {e}")

    @staticmethod
    def _signal_handler(signum: int, frame) -> None:
        """Handle signals by performing cleanup before exiting.

        We cleanup this manager first, then chain to the previously-installed
        handler (which may be another manager or the process default). This
        preserves LIFO cleanup order when both managers are active.
        """
        logger.warning(
            f"Received signal {signum}, performing unified connector "
            f"content cleanup..."
        )

        if UnifiedConnectorContentManager._active_instance is not None:
            UnifiedConnectorContentManager._active_instance.cleanup()

        original_handler = None
        if signum == signal.SIGINT:
            original_handler = UnifiedConnectorContentManager._original_sigint_handler
        elif signum == signal.SIGTERM:
            original_handler = UnifiedConnectorContentManager._original_sigterm_handler

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
            logger.debug("Performing atexit cleanup (unified connector content)")
            self.cleanup()

    def __enter__(self) -> "UnifiedConnectorContentManager":
        """Enter the context manager."""
        logger.info(
            f"Setting up unified connector content sync from: "
            f"{self.connectors_content_path}"
        )

        if UnifiedConnectorContentManager._active_instance:
            UnifiedConnectorContentManager._usage_count += 1
            return UnifiedConnectorContentManager._active_instance

        UnifiedConnectorContentManager._active_instance = self
        UnifiedConnectorContentManager._usage_count = 1

        self._setup_signal_handlers()
        try:
            self.copy_connectors()
            self.stage_copied_files()
            return self
        except Exception:
            self.cleanup()
            self._restore_signal_handlers()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        UnifiedConnectorContentManager._usage_count -= 1

        if UnifiedConnectorContentManager._usage_count <= 0:
            try:
                self.cleanup()
            finally:
                self._restore_signal_handlers()
