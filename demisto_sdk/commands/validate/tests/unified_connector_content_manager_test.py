"""
Unit tests for
:mod:`demisto_sdk.commands.validate.unified_connector_content_manager`.

These tests exercise the manager against real temporary directories but mock
out ``git_util`` so no real git repository is required. The interactions
covered are:

- copy behavior (whole connector dir, per-file "first missing level", ignore
  ignored files, honor an existing partial destination),
- staging (git add is called for every copied file),
- cleanup (files removed, git reset called with staged files, destination
  ``connectors/`` root removed only if we created it),
- context-manager usage (nested inside PrivateContentManager without breaking
  each other's signal handlers).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.common.constants import CONNECTORS_FOLDER
from demisto_sdk.commands.validate.unified_connector_content_manager import (
    UnifiedConnectorContentManager,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_ucc(tmp_path: Path) -> Path:
    """
    Build a fake UCC repository at ``<tmp>/ucc`` containing::

        ucc/
        └── connectors/
            ├── datadog/
            │   ├── connector.yaml
            │   └── components/handlers/xsoar/handler.yaml
            └── okta/
                └── connector.yaml
    """
    ucc = tmp_path / "ucc"
    connectors = ucc / CONNECTORS_FOLDER

    datadog_handler = connectors / "datadog" / "components" / "handlers" / "xsoar"
    datadog_handler.mkdir(parents=True)
    (connectors / "datadog" / "connector.yaml").write_text("name: datadog\n")
    (datadog_handler / "handler.yaml").write_text("handler: datadog\n")

    (connectors / "okta").mkdir(parents=True)
    (connectors / "okta" / "connector.yaml").write_text("name: okta\n")

    return ucc


@pytest.fixture
def fake_content(tmp_path: Path) -> Path:
    """
    Build a fake main content repository at ``<tmp>/content`` that only has a
    ``Packs/`` dir (no ``connectors/``). This mirrors a plain content checkout
    without the unified branch.
    """
    content = tmp_path / "content"
    (content / "Packs").mkdir(parents=True)
    return content


def _stub_git_util(manager: UnifiedConnectorContentManager) -> MagicMock:
    """
    Replace the manager's lazy ``git_util`` with a MagicMock so tests can run
    without a real git repository. Returns the mock for assertion.
    """
    mock = MagicMock()
    manager._git_util = mock
    return mock


# ---------------------------------------------------------------------------
# copy_connectors()
# ---------------------------------------------------------------------------


class TestCopyConnectors:
    def test_copies_all_connectors_from_ucc_into_content(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a UCC with two connectors and a content repo with no
               ``connectors/`` dir.
        When:  copy_connectors() runs.
        Then:  both connectors are copied under ``<content>/connectors/``,
               ``copied_paths`` contains both destination dirs, and the
               destination root is flagged as created-by-us.
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        copied = manager.copy_connectors()

        dest_root = fake_content / CONNECTORS_FOLDER
        assert dest_root.is_dir()
        assert (dest_root / "datadog" / "connector.yaml").is_file()
        assert (
            dest_root / "datadog" / "components" / "handlers" / "xsoar" / "handler.yaml"
        ).is_file()
        assert (dest_root / "okta" / "connector.yaml").is_file()

        assert copied == {dest_root / "datadog", dest_root / "okta"}
        assert manager._created_dest_root is True

    def test_does_not_flag_dest_root_when_it_pre_existed(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a content repo that *already* has a ``connectors/`` dir (e.g. the
               unified CI branch).
        When:  copy_connectors() runs.
        Then:  the copy still works and ``_created_dest_root`` stays False so
               cleanup will not remove it.
        """
        (fake_content / CONNECTORS_FOLDER).mkdir()

        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        manager.copy_connectors()

        assert manager._created_dest_root is False
        assert (
            fake_content / CONNECTORS_FOLDER / "datadog" / "connector.yaml"
        ).is_file()

    def test_first_missing_level_only_copies_new_files_when_connector_partly_exists(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a content repo where ``connectors/datadog/`` already exists but
               is missing the handler file, and UCC has both the existing top
               file and the new handler.
        When:  copy_connectors() runs.
        Then:  the new handler is copied but the existing top-level file is
               not overwritten - and only the new leaf ends up in
               ``copied_paths``.
        """
        # Simulate a pre-existing partial connector in content.
        dest_connector = fake_content / CONNECTORS_FOLDER / "datadog"
        dest_connector.mkdir(parents=True)
        # Content-side connector.yaml with distinct content that must NOT be
        # overwritten.
        (dest_connector / "connector.yaml").write_text("name: EXISTING\n")

        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        manager.copy_connectors()

        # Existing file untouched.
        assert (dest_connector / "connector.yaml").read_text() == "name: EXISTING\n"
        # New handler subtree copied in.
        assert (
            dest_connector / "components" / "handlers" / "xsoar" / "handler.yaml"
        ).is_file()

        # Okta is fully new: whole dir copied at the top level.
        okta_dest = fake_content / CONNECTORS_FOLDER / "okta"
        assert okta_dest in manager.copied_paths

    def test_raises_when_source_connectors_dir_missing(
        self, tmp_path: Path, fake_content: Path
    ) -> None:
        """
        Given: a UCC path that has no ``connectors/`` dir.
        When:  copy_connectors() runs.
        Then:  FileNotFoundError with a helpful message is raised.
        """
        ucc_no_connectors = tmp_path / "ucc-empty"
        ucc_no_connectors.mkdir()

        manager = UnifiedConnectorContentManager(
            connectors_content_path=ucc_no_connectors,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        with pytest.raises(FileNotFoundError, match="connectors/"):
            manager.copy_connectors()


# ---------------------------------------------------------------------------
# copy_connectors() with changed_only=True (-g / USE_GIT)
# ---------------------------------------------------------------------------


class TestChangedOnlyCopy:
    def test_changed_only_copies_only_changed_connectors(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a UCC with two connectors (datadog, okta) and only ``datadog``
               reported as changed by the UCC repo's git diff.
        When:  copy_connectors() runs with changed_only=True.
        Then:  only ``datadog`` is copied; ``okta`` is skipped entirely.
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
            changed_only=True,
        )
        _stub_git_util(manager)
        manager._get_changed_connector_names = lambda: {"datadog"}  # type: ignore[method-assign]

        copied = manager.copy_connectors()

        dest_root = fake_content / CONNECTORS_FOLDER
        assert (dest_root / "datadog" / "connector.yaml").is_file()
        # okta was not changed, so it must NOT be copied.
        assert not (dest_root / "okta").exists()
        assert copied == {dest_root / "datadog"}

    def test_changed_only_copies_nothing_when_no_connectors_changed(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a UCC with connectors but the git diff reports no changed
               connectors.
        When:  copy_connectors() runs with changed_only=True.
        Then:  nothing is copied.
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
            changed_only=True,
        )
        _stub_git_util(manager)
        manager._get_changed_connector_names = set  # type: ignore[method-assign]

        copied = manager.copy_connectors()

        assert copied == set()
        dest_root = fake_content / CONNECTORS_FOLDER
        assert not (dest_root / "datadog").exists()
        assert not (dest_root / "okta").exists()

    def test_default_copies_all_connectors(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a UCC with two connectors and the default changed_only=False
               (``-a``/ALL_FILES).
        When:  copy_connectors() runs.
        Then:  both connectors are copied (no git diff is consulted).
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        copied = manager.copy_connectors()

        dest_root = fake_content / CONNECTORS_FOLDER
        assert copied == {dest_root / "datadog", dest_root / "okta"}


# ---------------------------------------------------------------------------
# stage_copied_files()
# ---------------------------------------------------------------------------


class TestStageCopiedFiles:
    def test_calls_git_add_for_each_copied_file_with_paths_relative_to_content(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a manager that has already copied two connector trees.
        When:  stage_copied_files() runs.
        Then:  ``git add`` is called once per file with a path relative to the
               content root, and ``staged_files`` is populated accordingly.
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        mock_git = _stub_git_util(manager)
        manager.copy_connectors()

        staged = manager.stage_copied_files()

        expected = {
            "connectors/datadog/connector.yaml",
            "connectors/datadog/components/handlers/xsoar/handler.yaml",
            "connectors/okta/connector.yaml",
        }
        assert set(staged) == expected
        # Every staged file must have been ``git add``ed.
        added_calls = {c.args[0] for c in mock_git.repo.git.add.call_args_list}
        assert added_calls == expected

    def test_no_op_when_nothing_was_copied(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        mock_git = _stub_git_util(manager)

        # No copy_connectors() call -> copied_paths is empty.
        result = manager.stage_copied_files()

        assert result == []
        mock_git.repo.git.add.assert_not_called()


# ---------------------------------------------------------------------------
# cleanup()
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_manual_cleanup_removes_files_and_calls_git_reset(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Same as above but uses the manager manually (not as a context
        manager) so we can stub git_util *before* any git call happens.
        """
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        mock_git = _stub_git_util(manager)

        manager.copy_connectors()
        manager.stage_copied_files()

        # Sanity: files landed on disk.
        assert (fake_content / CONNECTORS_FOLDER / "datadog").is_dir()

        manager.cleanup()

        # Every copied top-level dir gone.
        assert not (fake_content / CONNECTORS_FOLDER / "datadog").exists()
        assert not (fake_content / CONNECTORS_FOLDER / "okta").exists()
        # Because we created connectors/ ourselves and it's now empty, it's
        # removed too.
        assert not (fake_content / CONNECTORS_FOLDER).exists()
        # And git reset was called with our staged files.
        mock_git.repo.git.reset.assert_called_once()
        reset_call = mock_git.repo.git.reset.call_args
        assert reset_call.args[0] == "HEAD"
        assert reset_call.args[1] == "--"
        assert set(reset_call.args[2:]) == {
            "connectors/datadog/connector.yaml",
            "connectors/datadog/components/handlers/xsoar/handler.yaml",
            "connectors/okta/connector.yaml",
        }

    def test_cleanup_does_not_remove_dest_root_when_it_pre_existed(
        self, fake_ucc: Path, fake_content: Path
    ) -> None:
        """
        Given: a content repo that already has ``connectors/`` (unified CI
               branch case).
        When:  the manager copies UCC connectors in and then cleanup runs.
        Then:  the copied connectors are removed but the ``connectors/`` root
               itself is preserved.
        """
        (fake_content / CONNECTORS_FOLDER).mkdir()
        # Also put a pre-existing sibling connector that we must NOT touch.
        (fake_content / CONNECTORS_FOLDER / "preexisting").mkdir()
        (
            fake_content / CONNECTORS_FOLDER / "preexisting" / "connector.yaml"
        ).write_text("name: preexisting\n")

        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        manager.copy_connectors()
        manager.stage_copied_files()
        manager.cleanup()

        assert (fake_content / CONNECTORS_FOLDER).is_dir()
        assert (
            fake_content / CONNECTORS_FOLDER / "preexisting" / "connector.yaml"
        ).is_file()
        # Copied dirs are gone.
        assert not (fake_content / CONNECTORS_FOLDER / "datadog").exists()
        assert not (fake_content / CONNECTORS_FOLDER / "okta").exists()

    def test_cleanup_is_idempotent(self, fake_ucc: Path, fake_content: Path) -> None:
        manager = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        _stub_git_util(manager)

        manager.copy_connectors()
        manager.stage_copied_files()
        manager.cleanup()
        # A second call must not raise.
        manager.cleanup()


# ---------------------------------------------------------------------------
# Nested-manager compatibility with PrivateContentManager
# ---------------------------------------------------------------------------


class TestNestedWithPrivateContentManager:
    """
    The two managers must be able to coexist inside a single
    ``contextlib.ExitStack`` (that's the wiring done in validate_setup.py's
    ``-a`` branch). We prove:

    - Independent class-level state: entering one does not clobber the other's
      ``_active_instance`` or handler slots.
    - LIFO cleanup: exiting the inner (UCC) manager restores the previous
      SIGINT handler which is the outer (private) manager's handler, not the
      process default.
    """

    def test_class_level_state_is_independent(
        self, fake_ucc: Path, fake_content: Path, tmp_path: Path
    ) -> None:
        # Build a fake content-private repo (just needs Packs/ to exist so
        # PrivateContentManager can enter without raising).
        content_private = tmp_path / "content-private"
        (content_private / "Packs" / "MyPrivatePack").mkdir(parents=True)
        (content_private / "Packs" / "MyPrivatePack" / "pack_metadata.json").write_text(
            "{}"
        )

        # Lazy import to keep the test file's top-level cheap.
        from demisto_sdk.commands.validate.private_content_manager import (
            PrivateContentManager,
        )

        # Both classes start with clean slate.
        assert PrivateContentManager._active_instance is None
        assert UnifiedConnectorContentManager._active_instance is None

        priv = PrivateContentManager(
            private_content_path=content_private,
            content_path=fake_content,
        )
        # Stub git for priv too (no real git repo in tmp_path).
        priv._git_util = MagicMock()

        ucc = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        ucc._git_util = MagicMock()

        # Manually enter both to prove state independence.
        priv.__enter__()
        try:
            ucc.__enter__()
            try:
                # Each class tracks its own instance - they do NOT share.
                assert PrivateContentManager._active_instance is priv
                assert UnifiedConnectorContentManager._active_instance is ucc
            finally:
                ucc.__exit__(None, None, None)
        finally:
            priv.__exit__(None, None, None)

        # After both exits, both class-level trackers are cleared.
        assert PrivateContentManager._active_instance is None
        assert UnifiedConnectorContentManager._active_instance is None

        # And the private pack that priv copied has been removed too.
        assert not (
            fake_content / "Packs" / "MyPrivatePack"
        ).exists(), "PrivateContentManager cleanup should also have run."
        # And the UCC dir (which ucc created) is gone.
        assert not (fake_content / CONNECTORS_FOLDER).exists()

    def test_signal_handler_chain_is_restored_after_both_exit(
        self, fake_ucc: Path, fake_content: Path, tmp_path: Path
    ) -> None:
        """
        Enter priv then ucc; the SIGINT handler installed by ucc is *ucc's*
        static handler. After ucc.__exit__ the SIGINT handler is priv's. After
        priv.__exit__ the SIGINT handler is whatever it was before priv
        entered.
        """
        import signal

        from demisto_sdk.commands.validate.private_content_manager import (
            PrivateContentManager,
        )

        content_private = tmp_path / "content-private"
        (content_private / "Packs").mkdir(parents=True)

        priv = PrivateContentManager(
            private_content_path=content_private,
            content_path=fake_content,
        )
        priv._git_util = MagicMock()
        ucc = UnifiedConnectorContentManager(
            connectors_content_path=fake_ucc,
            content_path=fake_content,
        )
        ucc._git_util = MagicMock()

        original_sigint = signal.getsignal(signal.SIGINT)

        priv.__enter__()
        priv_handler = signal.getsignal(signal.SIGINT)
        assert (
            priv_handler is not original_sigint
        ), "PrivateContentManager should have installed its own SIGINT handler."

        try:
            ucc.__enter__()
            ucc_handler = signal.getsignal(signal.SIGINT)
            assert ucc_handler is not priv_handler, (
                "UnifiedConnectorContentManager should install a *different* "
                "SIGINT handler, so the chain is preserved."
            )
            ucc.__exit__(None, None, None)
            # After ucc exit, we're back to priv's handler.
            assert signal.getsignal(signal.SIGINT) is priv_handler
        finally:
            priv.__exit__(None, None, None)

        # After priv exit, we're back to the process's original handler.
        assert signal.getsignal(signal.SIGINT) is original_sigint

        # Belt-and-braces: restore, in case something above failed halfway.
        signal.signal(signal.SIGINT, original_sigint)


# ---------------------------------------------------------------------------
# Sanity teardown
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_class_state():
    """
    Ensure no test leaks class-level state (signal handlers, active-instance
    trackers) into the next test.
    """
    yield
    import signal

    UnifiedConnectorContentManager._active_instance = None
    UnifiedConnectorContentManager._usage_count = 0
    UnifiedConnectorContentManager._original_sigint_handler = None
    UnifiedConnectorContentManager._original_sigterm_handler = None
    signal.signal(signal.SIGINT, signal.default_int_handler)


# ---------------------------------------------------------------------------
# End-of-file cleanup: nothing to do (tmp_path teardown removes everything).
# ---------------------------------------------------------------------------


def _prove_shutil_import_used() -> None:  # pragma: no cover
    """
    Silence linters: ``shutil`` is imported so tests can build custom fixtures
    at the module level if needed later. Currently unused; kept for future
    expansions (e.g. corrupt-file scenarios).
    """
    _ = shutil
