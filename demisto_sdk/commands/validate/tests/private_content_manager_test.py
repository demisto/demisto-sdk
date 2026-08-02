"""
Unit tests for
:mod:`demisto_sdk.commands.validate.private_content_manager`.

These tests focus on the ``changed_only`` copy scoping introduced for
``-g``/USE_GIT mode: in ``-g`` only the private packs that were actually changed
in the private repo's own git diff should be copied, while in ``-a``/ALL_FILES
mode (the default, ``changed_only=False``) all private packs are copied.

They exercise the manager against real temporary directories but mock out
``git_util`` so no real git repository is required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.validate.private_content_manager import (
    PrivateContentManager,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _build_fake_private(tmp_path: Path) -> Path:
    """
    Build a fake private content repository at ``<tmp>/content-private``
    containing two packs::

        content-private/
        └── Packs/
            ├── PackA/
            │   └── pack_metadata.json
            └── PackB/
                └── pack_metadata.json
    """
    private = tmp_path / "content-private"
    packs = private / PACKS_DIR

    (packs / "PackA").mkdir(parents=True)
    (packs / "PackA" / "pack_metadata.json").write_text('{"name": "PackA"}\n')

    (packs / "PackB").mkdir(parents=True)
    (packs / "PackB" / "pack_metadata.json").write_text('{"name": "PackB"}\n')

    return private


def _build_fake_content(tmp_path: Path) -> Path:
    """Build a fake main content repository with an empty ``Packs/`` dir."""
    content = tmp_path / "content"
    (content / PACKS_DIR).mkdir(parents=True)
    return content


def _stub_git_util(manager: PrivateContentManager) -> MagicMock:
    """Replace the manager's lazy ``git_util`` with a MagicMock."""
    mock = MagicMock()
    manager._git_util = mock
    return mock


# ---------------------------------------------------------------------------
# copy_private_packs() with changed_only=True (-g / USE_GIT)
# ---------------------------------------------------------------------------


class TestChangedOnlyCopy:
    def test_changed_only_copies_only_changed_packs(self, tmp_path: Path) -> None:
        """
        Given: a private repo with two packs (PackA, PackB) and only ``PackA``
               reported as changed by the private repo's git diff.
        When:  copy_private_packs() runs with changed_only=True.
        Then:  only ``PackA`` is copied; ``PackB`` is skipped entirely.
        """
        private = _build_fake_private(tmp_path)
        content = _build_fake_content(tmp_path)

        manager = PrivateContentManager(
            private_content_path=private,
            content_path=content,
            changed_only=True,
        )
        _stub_git_util(manager)
        manager._get_changed_pack_names = lambda: {"PackA"}  # type: ignore[method-assign]

        copied = manager.copy_private_packs()

        dest_packs = content / PACKS_DIR
        assert (dest_packs / "PackA" / "pack_metadata.json").is_file()
        # PackB was not changed, so it must NOT be copied.
        assert not (dest_packs / "PackB").exists()
        assert copied == {dest_packs / "PackA"}

    def test_changed_only_copies_nothing_when_no_packs_changed(
        self, tmp_path: Path
    ) -> None:
        """
        Given: a private repo with packs but the git diff reports no changed
               packs.
        When:  copy_private_packs() runs with changed_only=True.
        Then:  nothing is copied.
        """
        private = _build_fake_private(tmp_path)
        content = _build_fake_content(tmp_path)

        manager = PrivateContentManager(
            private_content_path=private,
            content_path=content,
            changed_only=True,
        )
        _stub_git_util(manager)
        manager._get_changed_pack_names = set  # type: ignore[method-assign]

        copied = manager.copy_private_packs()

        assert copied == set()
        dest_packs = content / PACKS_DIR
        assert not (dest_packs / "PackA").exists()
        assert not (dest_packs / "PackB").exists()

    def test_default_copies_all_packs(self, tmp_path: Path) -> None:
        """
        Given: a private repo with two packs and the default changed_only=False
               (``-a``/ALL_FILES).
        When:  copy_private_packs() runs.
        Then:  both packs are copied (no git diff is consulted).
        """
        private = _build_fake_private(tmp_path)
        content = _build_fake_content(tmp_path)

        manager = PrivateContentManager(
            private_content_path=private,
            content_path=content,
        )
        _stub_git_util(manager)

        copied = manager.copy_private_packs()

        dest_packs = content / PACKS_DIR
        assert copied == {dest_packs / "PackA", dest_packs / "PackB"}


# ---------------------------------------------------------------------------
# _get_changed_pack_names()
# ---------------------------------------------------------------------------


class TestGetChangedPackNames:
    def test_extracts_top_level_pack_names_from_changed_files(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """
        Given: the private repo's git diff returns changed files under
               ``Packs/<pack>/...`` plus an unrelated top-level file.
        When:  _get_changed_pack_names() runs.
        Then:  only the top-level pack names under ``Packs/`` are returned.
        """
        private = _build_fake_private(tmp_path)
        content = _build_fake_content(tmp_path)

        manager = PrivateContentManager(
            private_content_path=private,
            content_path=content,
            changed_only=True,
        )

        fake_git_util = MagicMock()
        fake_git_util.get_all_changed_files.return_value = {
            Path("Packs/PackA/pack_metadata.json"),
            Path("Packs/PackA/Integrations/Foo/Foo.yml"),
            Path("Packs/PackB/README.md"),
            Path("some_root_file.txt"),
        }
        monkeypatch.setattr(
            "demisto_sdk.commands.common.git_util.GitUtil",
            lambda *args, **kwargs: fake_git_util,
        )

        assert manager._get_changed_pack_names() == {"PackA", "PackB"}
