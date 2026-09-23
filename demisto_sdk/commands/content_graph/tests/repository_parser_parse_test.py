"""Regression tests for the narrowing semantics of
[`RepositoryParser.parse()`](demisto_sdk/commands/content_graph/parsers/repository.py:41).

The ``parse()`` method takes two optional caller-intent inputs:
``packs_to_parse`` and ``connectors_to_parse``. For both, ``None`` means
"no caller intent provided, default to a full scan" and an explicit empty
tuple ``()`` means "the caller explicitly wants none of these to be parsed".

The matrix that must hold (now symmetric for packs and connectors):

    | packs_to_parse | connectors_to_parse | iter_packs called | parse_pack count | iter_connectors called | parse_connector count |
    |----------------|---------------------|-------------------|------------------|------------------------|-----------------------|
    | None           | None                | yes (default)     | n_packs          | yes (default)          | n_connectors          |
    | ()             | (some,)             | NO                | 0                | NO                     | 1                     |
    | (some,)        | ()                  | NO                | 1                | NO                     | 0                     |

Historical bug (round 2): the packs branch used ``if not packs_to_parse``
(truthy/falsy), which silently treated the caller-supplied empty tuple as
"None" and re-expanded it to a full scan of every pack on disk - cancelling
out the symmetric narrowing introduced in
[`from_path()`](demisto_sdk/commands/content_graph/objects/repository.py:23)
(commit 692bbec1). The connectors branch already used ``is None`` correctly.

These tests lock in the symmetric ``is None`` checks at the parser layer so
the two layers (``from_path`` and ``RepositoryParser.parse``) cannot drift
apart again.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from demisto_sdk.commands.content_graph.parsers.repository import RepositoryParser


@pytest.fixture
def parser(mocker):
    """Build a real ``RepositoryParser`` instance against a fake path, with
    ``iter_packs``, ``iter_connectors``, ``parse_pack`` and ``parse_connector``
    mocked so the test does not touch the filesystem or spawn subprocesses.

    ``parse_pack`` / ``parse_connector`` are mocked at the class level because
    they are ``@staticmethod`` invoked through ``RepositoryParser.parse_pack``
    inside the multiprocessing pool path; we also stub the pool itself to keep
    the test synchronous and isolated.
    """
    p = RepositoryParser(Path("/fake/repo"))

    # Default to empty iterators; individual tests can override.
    mocker.patch.object(p, "iter_packs", return_value=iter(()))
    mocker.patch.object(p, "iter_connectors", return_value=iter(()))

    fake_pack_parser = MagicMock(name="PackParser_instance")
    fake_connector_parser = MagicMock(name="ConnectorParser_instance")

    mocker.patch.object(RepositoryParser, "parse_pack", return_value=fake_pack_parser)
    mocker.patch.object(
        RepositoryParser, "parse_connector", return_value=fake_connector_parser
    )

    # Replace ``multiprocessing.Pool`` so ``imap_unordered`` runs synchronously
    # via the patched ``RepositoryParser.parse_pack`` rather than fork()ing.
    class _SyncPool:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def imap_unordered(self, func, iterable):
            for item in iterable:
                yield func(item)

    mocker.patch(
        "demisto_sdk.commands.content_graph.parsers.repository.multiprocessing.Pool",
        _SyncPool,
    )

    return p


class TestRepositoryParserParseNarrowing:
    """Verify ``parse()`` honors the caller's explicit empty-tuple intent."""

    def test_connectors_only_does_not_parse_any_packs(self, parser):
        """
        Given:
            - A RepositoryParser where iter_packs would yield 3 packs if asked.
        When:
            - parse() is called with packs_to_parse=() and a single connector
              path in connectors_to_parse.
        Then:
            - iter_packs is NOT called (this is the bug: previously the empty
              tuple was treated like None and re-expanded to a full scan).
            - parse_pack is NOT called.
            - self.packs stays empty.
            - parse_connector is called exactly once for the supplied path.
            - self.connectors contains the single parsed connector.
        """
        # If iter_packs were (incorrectly) called, it would yield 3 packs.
        parser.iter_packs.return_value = iter(
            [Path("/fake/Packs/A"), Path("/fake/Packs/B"), Path("/fake/Packs/C")]
        )
        connector_path = Path("/fake/connectors/datadog")

        parser.parse(
            packs_to_parse=(),
            connectors_to_parse=(connector_path,),
        )

        assert parser.iter_packs.call_count == 0, (
            "iter_packs must NOT be called when the caller passes an empty "
            "tuple of packs; this is the round-2 regression."
        )
        assert RepositoryParser.parse_pack.call_count == 0
        assert parser.packs == []

        assert parser.iter_connectors.call_count == 0, (
            "iter_connectors must NOT be called when an explicit connectors "
            "list is provided."
        )
        assert RepositoryParser.parse_connector.call_count == 1
        assert RepositoryParser.parse_connector.call_args.args == (connector_path,)
        assert len(parser.connectors) == 1

    def test_packs_only_does_not_parse_any_connectors(self, parser):
        """
        Given:
            - A RepositoryParser.
        When:
            - parse() is called with a single pack path in packs_to_parse and
              connectors_to_parse=().
        Then:
            - iter_packs is NOT called (caller provided an explicit list).
            - parse_pack is called exactly once for the supplied path.
            - iter_connectors is NOT called (the connectors-side has used
              ``is None`` correctly all along; lock it in).
            - parse_connector is NOT called.
            - self.connectors stays empty.
        """
        pack_path = Path("/fake/Packs/MyPack")

        parser.parse(
            packs_to_parse=(pack_path,),
            connectors_to_parse=(),
        )

        assert parser.iter_packs.call_count == 0
        assert RepositoryParser.parse_pack.call_count == 1
        assert RepositoryParser.parse_pack.call_args.args == (pack_path,)
        assert len(parser.packs) == 1

        assert parser.iter_connectors.call_count == 0, (
            "iter_connectors must NOT be called when an explicit (even empty) "
            "connectors list is provided."
        )
        assert RepositoryParser.parse_connector.call_count == 0
        assert parser.connectors == []

    def test_both_none_triggers_full_scan_on_both_sides(self, parser):
        """
        Given:
            - A RepositoryParser where iter_packs yields 2 packs and
              iter_connectors yields 1 connector.
        When:
            - parse() is called with both arguments left as their None defaults.
        Then:
            - iter_packs is called once (default full-scan behaviour).
            - parse_pack is called once per yielded pack.
            - iter_connectors is called once (default full-scan behaviour).
            - parse_connector is called once per yielded connector.
            - Locks in the existing default behaviour so the new ``is None``
              guard does not accidentally regress it.
        """
        parser.iter_packs.return_value = iter(
            [Path("/fake/Packs/A"), Path("/fake/Packs/B")]
        )
        parser.iter_connectors.return_value = iter([Path("/fake/connectors/c1")])

        parser.parse()

        assert parser.iter_packs.call_count == 1
        assert RepositoryParser.parse_pack.call_count == 2
        assert len(parser.packs) == 2

        assert parser.iter_connectors.call_count == 1
        assert RepositoryParser.parse_connector.call_count == 1
        assert len(parser.connectors) == 1
