"""Unit tests for the pack-level `.pack-ignore` mechanism.

These tests cover the three production changes:

1. `Pack.pack_level_ignored_errors` (in
   `demisto_sdk.commands.content_graph.objects.pack`).
2. `is_error_ignored` honoring pack-level ignores (in
   `demisto_sdk.commands.validate.validators.base_validator`).
3. `extract_error_codes_from_file` aggregating codes from the new `[pack]`
   section (in `demisto_sdk.commands.common.tools`), which feeds the
   `PA137` safety check.
"""

from __future__ import annotations

from configparser import ConfigParser
from typing import Optional

from demisto_sdk.commands.common.tools import (
    extract_error_codes_from_file,
    parse_ignore_list,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import is_error_ignored

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_from_text(text: str) -> dict:
    """Mimic the structure that `PackParser.parse_ignored_errors` produces:
    `dict(ConfigParser(...))`, whose values are `SectionProxy` objects, not
    plain dicts. We must preserve this invariant so the tests catch the bug
    that motivated the corrected design.
    """
    parser = ConfigParser(allow_no_value=True)
    parser.read_string(text)
    return dict(parser)


def _make_pack(pack_ignore_text: str):
    """Build a stand-in for `Pack` exposing exactly the attributes the
    feature touches. We avoid constructing a full Pydantic Pack model to
    keep this test fast and free of unrelated dependencies."""
    from demisto_sdk.commands.content_graph.objects.pack import Pack

    pack = Pack.__new__(Pack)  # bypass Pydantic init
    object.__setattr__(pack, "ignored_errors_dict", _config_from_text(pack_ignore_text))
    object.__setattr__(pack, "object_id", "TestPack")
    return pack


# ---------------------------------------------------------------------------
# Slice 1: Pack.pack_level_ignored_errors
# ---------------------------------------------------------------------------


class TestPackLevelIgnoredErrorsProperty:
    """Verify the property correctly parses the `[pack]` section."""

    def test_no_pack_section_returns_empty(self):
        """
        Given a .pack-ignore that contains only [file:...] sections,
        When pack_level_ignored_errors is accessed,
        Then it should return an empty list.
        """
        pack = _make_pack("[file:foo.yml]\nignore=BA101\n")
        assert pack.pack_level_ignored_errors == []

    def test_empty_pack_section_returns_empty(self):
        """
        Given a .pack-ignore that contains an empty [pack] section,
        When pack_level_ignored_errors is accessed,
        Then it should return an empty list.
        """
        pack = _make_pack("[pack]\n")
        assert pack.pack_level_ignored_errors == []

    def test_single_code(self):
        pack = _make_pack("[pack]\nignore=BA101\n")
        assert pack.pack_level_ignored_errors == ["BA101"]

    def test_multiple_codes(self):
        pack = _make_pack("[pack]\nignore=BA101,RM104,RN107\n")
        assert pack.pack_level_ignored_errors == ["BA101", "RM104", "RN107"]

    def test_pack_level_codes_alongside_file_level_codes(self):
        """
        Given a .pack-ignore that contains BOTH a [pack] section and
        per-file [file:...] sections,
        When pack_level_ignored_errors is accessed,
        Then only the codes under the [pack] section are returned (the
        per-file codes are intentionally NOT included here).
        """
        pack = _make_pack(
            "[pack]\nignore=BA101,RN107\n"
            "[file:foo.yml]\nignore=RM104\n"
            "[file:bar.yml]\nignore=BA108,IN122\n"
        )
        assert pack.pack_level_ignored_errors == ["BA101", "RN107"]

    def test_whitespace_and_empty_entries_are_tolerated(self):
        """
        Given a sloppy ignore line with extra whitespace and empty entries,
        When pack_level_ignored_errors is accessed,
        Then surrounding whitespace is trimmed and empty entries are dropped.
        """
        pack = _make_pack("[pack]\nignore= BA101 ,, RM104 ,\n")
        assert pack.pack_level_ignored_errors == ["BA101", "RM104"]

    def test_pack_section_with_unknown_key_returns_empty(self):
        """
        Given a [pack] section that does not contain an `ignore` key,
        When pack_level_ignored_errors is accessed,
        Then it should return an empty list.
        """
        pack = _make_pack("[pack]\nfoo=bar\n")
        assert pack.pack_level_ignored_errors == []

    def test_result_is_cached(self):
        """`@cached_property` means subsequent accesses must not re-parse."""
        pack = _make_pack("[pack]\nignore=BA101\n")
        first = pack.pack_level_ignored_errors
        # Mutate the underlying dict; the cached value must NOT change.
        object.__setattr__(pack, "ignored_errors_dict", {})
        assert pack.pack_level_ignored_errors is first
        assert pack.pack_level_ignored_errors == ["BA101"]

    def test_exception_is_logged_and_empty_list_returned(self, mocker):
        """
        Given an `ignored_errors_dict` whose access raises an exception,
        When pack_level_ignored_errors is accessed,
        Then the failure is logged at debug level with the expected message
        and an empty list is returned (the validation flow is not broken).
        """
        from demisto_sdk.commands.content_graph.objects import pack as pack_module

        debug_mock = mocker.patch.object(pack_module.logger, "debug")

        pack = _make_pack("[pack]\nignore=BA101\n")
        # Replace the dict with one whose `.get` raises, forcing the
        # defensive `except` branch in the property.
        raising_dict = mocker.MagicMock()
        raising_dict.get.side_effect = RuntimeError("boom")
        object.__setattr__(pack, "ignored_errors_dict", raising_dict)

        assert pack.pack_level_ignored_errors == []
        debug_mock.assert_called_once_with(
            "Failed to extract pack-level ignored errors for TestPack: boom"
        )


# ---------------------------------------------------------------------------
# Slice 2: is_error_ignored
# ---------------------------------------------------------------------------


class _FakeRelatedFile:
    """Stand-in for a related-file object (e.g. README/release-note)."""

    def __init__(self, file_path: str):
        self.file_path = file_path


class _FakeContentItem:
    """Minimal stand-in for a ContentItem.

    Only the attributes that `is_error_ignored` reads are defined."""

    def __init__(
        self,
        pack: Optional[object] = None,
        ignored_errors: Optional[list] = None,
        related_file: Optional[_FakeRelatedFile] = None,
        related_file_attr: str = "readme",
        related_file_ignores: Optional[list] = None,
    ):
        self.in_pack = pack
        self.ignored_errors = ignored_errors or []
        self._related_file_ignores = related_file_ignores or []
        if related_file is not None:
            # Expose the related-file object under the attribute name that
            # `RelatedFileType.<X>.value` resolves to (e.g. "readme").
            setattr(self, related_file_attr, related_file)

    def ignored_errors_related_files(self, _path):
        return self._related_file_ignores


# Codes used across the suite. They must be valid `ALLOWED_IGNORE_ERRORS`
# entries; both BA101 (file-only) and RM104 (related-file) are.
ALLOWED = ["BA101", "RM104", "RN107"]


class TestIsErrorIgnoredPackLevel:
    """Verify pack-level ignores are honored by `is_error_ignored`."""

    def test_pack_level_ignored_for_content_item(self):
        """
        Given a content item whose pack ignores BA101 pack-wide,
        When is_error_ignored is called for BA101,
        Then it returns True.
        """
        pack = _make_pack("[pack]\nignore=BA101\n")
        item = _FakeContentItem(pack=pack)
        assert is_error_ignored("BA101", ALLOWED, item) is True

    def test_pack_level_ignored_for_pack_itself(self):
        """
        Given the pack object itself (PA-validators run on Pack),
        When is_error_ignored is called for a code listed under [pack],
        Then it returns True.
        """
        pack = _make_pack("[pack]\nignore=BA101\n")
        # No `in_pack` on Pack; duck-typed branch must use the pack directly.
        assert is_error_ignored("BA101", ALLOWED, pack) is True

    def test_unrelated_code_not_ignored(self):
        pack = _make_pack("[pack]\nignore=BA101\n")
        item = _FakeContentItem(pack=pack)
        assert is_error_ignored("RM104", ALLOWED, item) is False

    def test_item_with_no_pack_is_not_ignored(self):
        """
        Given a content item whose in_pack is None,
        When is_error_ignored is called,
        Then the pack-level check is skipped safely (no AttributeError)
        and the result is False.
        """
        item = _FakeContentItem(pack=None)
        assert is_error_ignored("BA101", ALLOWED, item) is False

    def test_always_run_wins_over_pack_level(self):
        """
        Given a code listed in ALWAYS_RUN_ON_ERROR_CODE *and* under [pack],
        When is_error_ignored is called,
        Then ALWAYS_RUN_ON_ERROR_CODE wins and the result is False.
        """
        pack = _make_pack("[pack]\nignore=GR109\n")
        item = _FakeContentItem(pack=pack)
        assert is_error_ignored("GR109", ALLOWED + ["GR109"], item) is False

    def test_non_ignorable_code_not_silenced_even_via_pack_level(self):
        """
        Given a code that is NOT in the ignorable whitelist,
        When is_error_ignored is called,
        Then it returns False even if [pack] lists it.
        """
        pack = _make_pack("[pack]\nignore=XX999\n")
        item = _FakeContentItem(pack=pack)
        assert is_error_ignored("XX999", ALLOWED, item) is False

    def test_per_file_ignore_used_when_no_pack_level_ignore(self):
        """
        Given a content item whose pack defines per-file ignores but has
        NO [pack] section,
        When is_error_ignored is called,
        Then the pack-level check does not match and the per-file
        `ignored_errors` list is consulted as before.
        """
        pack = _make_pack("[file:foo.yml]\nignore=RM104\n")
        item = _FakeContentItem(pack=pack, ignored_errors=["BA101"])
        assert is_error_ignored("BA101", ALLOWED, item) is True
        assert is_error_ignored("RM104", ALLOWED, item) is False

    def test_pack_level_ignore_silences_related_file_validation(self):
        """
        Given a validator that runs on a related file (e.g. README) and a
        pack that ignores its error code pack-wide,
        When is_error_ignored is called with the related_file_type,
        Then the pack-level check short-circuits and returns True, even
        though the related file itself has no per-file ignore.
        """
        pack = _make_pack("[pack]\nignore=RM104\n")
        item = _FakeContentItem(
            pack=pack,
            related_file=_FakeRelatedFile("Packs/Test/README.md"),
            related_file_attr=RelatedFileType.README.value,
            related_file_ignores=[],  # no per-file ignore
        )
        assert (
            is_error_ignored("RM104", ALLOWED, item, [RelatedFileType.README]) is True
        )

    def test_related_file_per_file_ignore_silences_when_no_pack_level(self):
        """
        Given a validator that runs on a related file, no [pack] section,
        and a per-file ignore for that related file,
        When is_error_ignored is called with the related_file_type,
        Then the related file's per-file ignore list silences it (True).
        """
        pack = _make_pack("[file:README.md]\nignore=RM104\n")
        item = _FakeContentItem(
            pack=pack,
            related_file=_FakeRelatedFile("Packs/Test/README.md"),
            related_file_attr=RelatedFileType.README.value,
            related_file_ignores=["RM104"],
        )
        assert (
            is_error_ignored("RM104", ALLOWED, item, [RelatedFileType.README]) is True
        )

    def test_related_file_validation_runs_when_ignored_nowhere(self):
        """
        Given a validator that runs on a related file, no [pack] section,
        and no per-file ignore for that related file,
        When is_error_ignored is called with the related_file_type,
        Then the validation is not ignored and must run (False).
        """
        pack = _make_pack("")  # empty .pack-ignore: nothing is ignored
        item = _FakeContentItem(
            pack=pack,
            related_file=_FakeRelatedFile("Packs/Test/README.md"),
            related_file_attr=RelatedFileType.README.value,
            related_file_ignores=[],
        )
        assert (
            is_error_ignored("RM104", ALLOWED, item, [RelatedFileType.README]) is False
        )


# ---------------------------------------------------------------------------
# Slice 3: extract_error_codes_from_file (PA137 coverage)
# ---------------------------------------------------------------------------


class TestExtractErrorCodesFromFile:
    """Verify the PA137 safety net covers the new `[pack]` section."""

    @staticmethod
    def _patch_config(monkeypatch, text: str) -> None:
        parser = ConfigParser(allow_no_value=True)
        parser.read_string(text)
        monkeypatch.setattr(
            "demisto_sdk.commands.common.tools.get_pack_ignore_content",
            lambda _pack: parser,
        )

    def test_only_file_sections(self, monkeypatch):
        self._patch_config(
            monkeypatch,
            "[file:foo.yml]\nignore=BA101,RM104\n",
        )
        assert extract_error_codes_from_file("TestPack") == {"BA101", "RM104"}

    def test_only_pack_section(self, monkeypatch):
        self._patch_config(monkeypatch, "[pack]\nignore=BA101,RN107\n")
        assert extract_error_codes_from_file("TestPack") == {"BA101", "RN107"}

    def test_pack_and_file_sections_aggregated(self, monkeypatch):
        self._patch_config(
            monkeypatch,
            "[pack]\nignore=BA101\n"
            "[file:foo.yml]\nignore=RM104,RN107\n"
            "[file:bar.yml]\nignore=BA101\n",
        )
        assert extract_error_codes_from_file("TestPack") == {"BA101", "RM104", "RN107"}

    def test_whitespace_in_pack_section_tolerated(self, monkeypatch):
        self._patch_config(monkeypatch, "[pack]\nignore= BA101 , RM104 ,\n")
        assert extract_error_codes_from_file("TestPack") == {"BA101", "RM104"}

    def test_no_config_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "demisto_sdk.commands.common.tools.get_pack_ignore_content",
            lambda _pack: None,
        )
        assert extract_error_codes_from_file("TestPack") == set()


# ---------------------------------------------------------------------------
# Shared ignore-list parsing helper
# ---------------------------------------------------------------------------


class TestParseIgnoreList:
    """Verify the shared `[pack]`/`[file:...]` ignore grammar parser."""

    def test_basic_split(self):
        assert parse_ignore_list("BA101,RM104,RN107") == ["BA101", "RM104", "RN107"]

    def test_whitespace_and_empty_entries_dropped(self):
        assert parse_ignore_list(" BA101 , RM104 ,") == ["BA101", "RM104"]

    def test_empty_value_returns_empty_list(self):
        assert parse_ignore_list("") == []

    def test_single_code(self):
        assert parse_ignore_list("BA101") == ["BA101"]
