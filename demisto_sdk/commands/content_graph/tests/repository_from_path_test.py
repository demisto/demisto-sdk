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

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.objects import repository as repository_module
from demisto_sdk.commands.content_graph.objects.repository import (
    ContentDTO,
    from_path,
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
