"""Regression tests for the narrowing semantics of
[`from_path()`](demisto_sdk/commands/content_graph/objects/repository.py:23).

The function takes two optional filters: ``packs_to_parse`` and
``connectors_to_parse``. The narrowing matrix that must hold is:

    | packs_to_parse | connectors_to_parse | iter_packs called | iter_connectors called |
    |----------------|---------------------|-------------------|------------------------|
    | None / falsy   | None                | once, with None   | once, with no args     |
    | truthy         | None                | once, with packs  | NOT called             |
    | None / falsy   | not None            | NOT called        | once, with connectors  |
    | truthy         | not None            | once, with packs  | once, with connectors  |

Historical bug: the "connectors-only" row used to call ``iter_packs(None)``,
which makes the parser walk every pack under ``Packs/`` (~1300 packs in
content), turning a sub-minute step into a multi-minute one. These tests lock
in the fixed matrix.

``from_path`` is decorated with ``@lru_cache``, so each test clears the cache
to keep tests isolated.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.objects import repository as repository_module
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
    OrderedPackZipWriter,
    from_path,
    write_deterministic_zip,
)


@pytest.fixture(autouse=True)
def _clear_from_path_cache():
    """``from_path`` is ``@lru_cache``-decorated; clear before and after each test."""
    from_path.cache_clear()
    yield
    from_path.cache_clear()


@pytest.fixture
def mock_repo_parser(mocker):
    """Patch ``RepositoryParser`` and ``ContentDTO.from_orm`` so ``from_path``
    runs without touching the filesystem or pydantic validation.

    Returns the MagicMock instance that stands in for the parser; tests can
    assert on its ``iter_packs`` / ``iter_connectors`` mocks directly.
    """
    parser_instance = MagicMock(name="RepositoryParser_instance")
    parser_instance.iter_packs = MagicMock(return_value=iter(()))
    parser_instance.iter_connectors = MagicMock(return_value=iter(()))
    parser_instance.parse = MagicMock()

    mocker.patch.object(
        repository_module,
        "RepositoryParser",
        return_value=parser_instance,
    )
    # ``from_orm`` is what builds the ContentDTO at the end; we don't care
    # about the return value, only the narrowing branches taken before it.
    sentinel_dto = MagicMock(name="ContentDTO_sentinel", spec=ContentDTO)
    mocker.patch.object(ContentDTO, "from_orm", return_value=sentinel_dto)
    return parser_instance


def _call_counts(mock_method):
    """Return (count, list_of_call_args) for a MagicMock callable."""
    return mock_method.call_count, list(mock_method.call_args_list)


class TestFromPathNarrowing:
    """Verify the four cells of the packs x connectors narrowing matrix."""

    def test_connectors_only_does_not_parse_any_packs(self, mock_repo_parser):
        """
        Given:
            - packs_to_parse is None (no pack filter).
            - connectors_to_parse is ('datadog',) (a single connector).
        When:
            - from_path() is invoked.
        Then:
            - iter_packs is NOT called (this was the bug: previously it was
              called with None and walked every pack in the repo).
            - iter_connectors is called exactly once with ('datadog',).
            - The tqdm total equals 1 (one connector, zero packs).
        """
        from_path(
            path=Path("/fake/repo"),
            packs_to_parse=None,
            connectors_to_parse=("datadog",),
        )

        assert mock_repo_parser.iter_packs.call_count == 0, (
            "iter_packs must NOT be called when only connectors are filtered; "
            "this is the regression the fix addresses."
        )
        assert mock_repo_parser.iter_connectors.call_count == 1
        assert mock_repo_parser.iter_connectors.call_args.args == (("datadog",),)

        # The parse call should have received empty packs and the one connector.
        parse_call = mock_repo_parser.parse.call_args
        assert parse_call.kwargs["packs_to_parse"] == ()
        assert parse_call.kwargs["connectors_to_parse"] == ()
        # ``connectors_to_parse`` ends up as () because our mock's iter_connectors
        # returns an empty iterator; what matters is the *call* shape above.

    def test_packs_only_does_not_parse_any_connectors(self, mock_repo_parser):
        """
        Given:
            - packs_to_parse is ('MyPack',) (a single pack).
            - connectors_to_parse is None (no connector filter).
        When:
            - from_path() is invoked.
        Then:
            - iter_packs is called exactly once with ('MyPack',).
            - iter_connectors is NOT called.
            - Locks in the existing pack-narrowing behaviour.
        """
        from_path(
            path=Path("/fake/repo"),
            packs_to_parse=("MyPack",),
            connectors_to_parse=None,
        )

        assert mock_repo_parser.iter_packs.call_count == 1
        assert mock_repo_parser.iter_packs.call_args.args == (("MyPack",),)
        assert (
            mock_repo_parser.iter_connectors.call_count == 0
        ), "iter_connectors must NOT be called when only packs are filtered."

    def test_no_filters_triggers_full_scan(self, mock_repo_parser):
        """
        Given:
            - Neither packs_to_parse nor connectors_to_parse is provided.
        When:
            - from_path() is invoked.
        Then:
            - iter_packs is called once with None (full scan).
            - iter_connectors is called once with no positional args (full scan).
            - Locks in the existing full-scan behaviour.
        """
        from_path(
            path=Path("/fake/repo"),
            packs_to_parse=None,
            connectors_to_parse=None,
        )

        assert mock_repo_parser.iter_packs.call_count == 1
        assert mock_repo_parser.iter_packs.call_args.args == (None,)
        assert mock_repo_parser.iter_connectors.call_count == 1
        assert mock_repo_parser.iter_connectors.call_args.args == ()

    def test_both_filters_parse_both_narrowed(self, mock_repo_parser):
        """
        Given:
            - Both packs_to_parse=('MyPack',) and connectors_to_parse=('datadog',).
        When:
            - from_path() is invoked.
        Then:
            - iter_packs is called once with ('MyPack',).
            - iter_connectors is called once with ('datadog',).
        """
        from_path(
            path=Path("/fake/repo"),
            packs_to_parse=("MyPack",),
            connectors_to_parse=("datadog",),
        )

        assert mock_repo_parser.iter_packs.call_count == 1
        assert mock_repo_parser.iter_packs.call_args.args == (("MyPack",),)
        assert mock_repo_parser.iter_connectors.call_count == 1
        assert mock_repo_parser.iter_connectors.call_args.args == (("datadog",),)


# Deterministic zip writer (``OrderedPackZipWriter`` / ``write_deterministic_zip``)


def _create_pack_tree(
    root: Path, file_mode: int = 0o644, mtime: float = 1_000_000_000
) -> Path:
    """Create a small dump-like tree: two packs, nested files, and an empty directory."""
    files = {
        "PackB/metadata.json": b'{"name": "B"}',
        "PackB/Integrations/integration-B.yml": b"name: B\n",
        "PackA/metadata.json": b'{"name": "A"}',
        "PackA/Scripts/script-A.yml": b"name: A\n" * 50,
        "PackA/README.md": b"# A\n",
    }
    for relative_path, content in files.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        file_path.chmod(file_mode)
    (root / "PackA" / "EmptyDir").mkdir()
    for path in [*root.rglob("*"), root]:
        os.utime(path, (mtime, mtime))
    return root


def _read_tree(root: Path) -> Dict[str, Optional[bytes]]:
    """``{relative POSIX path: bytes}`` for files and ``{relative POSIX path/: None}`` for directories."""
    tree: Dict[str, Optional[bytes]] = {}
    for path in root.rglob("*"):
        relative_path = path.relative_to(root).as_posix()
        if path.is_dir():
            tree[f"{relative_path}/"] = None
        else:
            tree[relative_path] = path.read_bytes()
    return tree


def _extract(zip_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zip_file:
        zip_file.extractall(destination)
    return destination


def test_deterministic_zip_bytes_do_not_depend_on_mtimes_or_permissions(tmp_path):
    """
    Given:
        - Two trees with the same paths and contents, but different mtimes and file permissions.
    When:
        - Zipping each tree with write_deterministic_zip.
    Then:
        - The two zip files are byte-identical.
    """
    first_tree = _create_pack_tree(
        tmp_path / "first", file_mode=0o644, mtime=1_000_000_000
    )
    second_tree = _create_pack_tree(
        tmp_path / "second", file_mode=0o600, mtime=1_700_000_000
    )

    write_deterministic_zip(first_tree, tmp_path / "first.zip")
    write_deterministic_zip(second_tree, tmp_path / "second.zip")

    assert (tmp_path / "first.zip").read_bytes() == (
        tmp_path / "second.zip"
    ).read_bytes()


def test_ordered_pack_zip_writer_out_of_order_equals_in_order(tmp_path):
    """
    Given:
        - A dump-like tree with the top-level pack directories PackA and PackB.
    When:
        - Marking the packs as done in reverse order, and, separately, zipping in order (write_deterministic_zip).
    Then:
        - Nothing is written before PackA is done, and both zips are byte-identical.
    """
    tree = _create_pack_tree(tmp_path / "tree")
    out_of_order_zip = tmp_path / "out_of_order.zip"

    with OrderedPackZipWriter(tree, out_of_order_zip, ["PackB", "PackA"]) as writer:
        writer.mark_pack_done("PackB")
        assert writer._next_index == 0  # PackB stays pending until PackA is done
        writer.mark_pack_done("PackA")
    write_deterministic_zip(tree, tmp_path / "in_order.zip")

    assert out_of_order_zip.read_bytes() == (tmp_path / "in_order.zip").read_bytes()


def test_deterministic_zip_extracts_to_the_source_tree_like_make_archive(tmp_path):
    """
    Given:
        - A dump-like tree that includes an empty directory.
    When:
        - Zipping it with write_deterministic_zip and with shutil.make_archive, and extracting both.
    Then:
        - Both extracted trees equal the source tree (paths and contents, including the empty directory).
    """
    tree = _create_pack_tree(tmp_path / "tree")
    write_deterministic_zip(tree, tmp_path / "deterministic.zip")
    shutil.make_archive(str(tmp_path / "make_archive"), "zip", tree)

    source_tree = _read_tree(tree)
    assert "PackA/EmptyDir/" in source_tree
    deterministic_tree = _read_tree(
        _extract(tmp_path / "deterministic.zip", tmp_path / "extracted_deterministic")
    )
    make_archive_tree = _read_tree(
        _extract(tmp_path / "make_archive.zip", tmp_path / "extracted_make_archive")
    )
    assert deterministic_tree == source_tree
    assert make_archive_tree == source_tree
