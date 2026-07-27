"""
Unit tests for ``check_nightly_gate.py``.

The tests are deliberately focused on the two pure functions that
carry all the business logic (``classify`` and ``decide``) plus:

* A few targeted checks on the glob compiler, since a subtle bug there
  would either let must-files slip through or block innocent PRs.
* Coverage of the modern ``must_exclude`` model (``must: ['**']`` +
  exclusions), the legacy explicit-list model, and the mixed backwards-
  compat behavior.
* Coverage of the "skipped-anyway" acknowledgement wording for a
  must-tier PR that only carries the ``nightly-run-skipped`` label.
* Assertion that the Content-build alternative footer is present in
  every fail/warn/skipped-anyway comment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Utils.github_workflow_scripts.nightly_gate.check_nightly_gate import (
    COMMENT_MARKER,
    LABEL_PASSED,
    LABEL_SKIPPED,
    Classification,
    Decision,
    DecisionStatus,
    GateConfig,
    _glob_to_regex,
    _parse_labels,
    _render_ok_comment,
    classify,
    decide,
    load_config,
)

# ---------------------------------------------------------------------------
# Glob compilation
# ---------------------------------------------------------------------------


class TestGlobToRegex:
    """The glob compiler is the load-bearing part of the whole gate."""

    @pytest.mark.parametrize(
        "pattern, path, expected",
        [
            # Literal match.
            ("a/b/c.py", "a/b/c.py", True),
            ("a/b/c.py", "a/b/d.py", False),
            # `*` should match a single segment only.
            ("a/*/c.py", "a/b/c.py", True),
            ("a/*/c.py", "a/b/x/c.py", False),
            ("a/*.py", "a/b.py", True),
            ("a/*.py", "a/b/c.py", False),
            # `**` in the middle should span any number of levels,
            # including zero.
            ("a/**/c.py", "a/c.py", True),
            ("a/**/c.py", "a/b/c.py", True),
            ("a/**/c.py", "a/b/c/d/c.py", True),
            ("a/**/c.py", "x/c.py", False),
            # `**` at the end should span into subdirs.
            ("a/**", "a/b.py", True),
            ("a/**", "a/b/c.py", True),
            ("a/**", "b/a", False),
            # `**/` at the start should match any prefix.
            ("**/tests/**", "foo/tests/bar.py", True),
            ("**/tests/**", "foo/bar/tests/x/y.py", True),
            ("**/tests/**", "tests/x.py", True),
            ("**/tests/**", "src/x.py", False),
            # `**` alone means everything.
            ("**", "anything/at/all.py", True),
            # Question mark matches a single non-slash char.
            ("a?.py", "ab.py", True),
            ("a?.py", "a/.py", False),
            # Docker-prefix pattern used by the real config:
            # `docker**` should match `docker.py` and `docker_helper/`.
            (
                "demisto_sdk/commands/common/docker**",
                "demisto_sdk/commands/common/docker.py",
                True,
            ),
            (
                "demisto_sdk/commands/common/docker**",
                "demisto_sdk/commands/common/docker_helper/x.py",
                True,
            ),
            (
                "demisto_sdk/commands/common/docker**",
                "demisto_sdk/commands/common/other.py",
                False,
            ),
        ],
    )
    def test_matches(self, pattern: str, path: str, expected: bool) -> None:
        rx = _glob_to_regex(pattern)
        assert bool(rx.match(path)) is expected

    def test_special_regex_chars_are_escaped(self) -> None:
        # A literal `.` in the pattern should not act as regex `.`.
        rx = _glob_to_regex("a.py")
        assert rx.match("a.py")
        assert not rx.match("ax.py")

    def test_readme_star_pattern(self) -> None:
        # `**/README*` from the real skip config.
        rx = _glob_to_regex("**/README*")
        assert rx.match("README.md")
        assert rx.match("docs/README")
        assert rx.match("a/b/README.rst")
        assert not rx.match("docs/AUTHORS.md")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def legacy_config() -> GateConfig:
    """A minimal *legacy-mode* config (explicit lists per tier).

    Exercises the old precedence: ``skip > must > recommended``.
    """
    return GateConfig(
        must=[
            "demisto_sdk/commands/content_graph/objects/**",
            "demisto_sdk/commands/content_graph/common.py",
            "demisto_sdk/commands/common/docker**",
        ],
        recommended=[
            # Deliberately overlaps with Must so we can assert Must wins.
            "demisto_sdk/commands/validate/**",
            "demisto_sdk/commands/common/tools.py",
        ],
        skip=[
            "**/tests/**",
            "**/test_data/**",
            "**/*.md",
        ],
    )


@pytest.fixture
def modern_config() -> GateConfig:
    """A *modern-mode* config: ``must: ['**']`` + ``must_exclude`` + ``skip``.

    Encodes the current real-world posture: any SDK change requires
    nightly by default, with a small exclude list downgrading a few
    well-tested subtrees to `recommended`, and a broad skip list for
    docs / tests / CI / etc.
    """
    return GateConfig(
        must=["**"],
        must_exclude=[
            "demisto_sdk/commands/prepare_content/**",
            "demisto_sdk/commands/common/tools.py",
        ],
        # `recommended` is intentionally empty in modern mode; presence
        # of `must_exclude` is what flips the classifier over.
        recommended=[],
        skip=[
            "**/tests/**",
            "**/test_data/**",
            "**/*.md",
            ".changelog/**",
            ".github/**",
            "Utils/**",
        ],
    )


# ---------------------------------------------------------------------------
# classify() - legacy mode
# ---------------------------------------------------------------------------


class TestClassifyLegacyMode:
    """Preserve the explicit-lists behavior for callers still on the old config."""

    def test_no_files_yields_none_tier(self, legacy_config: GateConfig) -> None:
        result = classify([], legacy_config)
        assert result.tier == "none"
        assert result == Classification(tier="none")

    def test_must_hit_wins_over_recommended(self, legacy_config: GateConfig) -> None:
        result = classify(
            [
                "demisto_sdk/commands/content_graph/objects/pack.py",
                "demisto_sdk/commands/validate/foo.py",
            ],
            legacy_config,
        )
        assert result.tier == "must"
        assert result.matched_must == [
            "demisto_sdk/commands/content_graph/objects/pack.py"
        ]
        assert result.matched_recommended == ["demisto_sdk/commands/validate/foo.py"]

    def test_recommended_only(self, legacy_config: GateConfig) -> None:
        result = classify(
            [
                "demisto_sdk/commands/validate/foo.py",
                "demisto_sdk/commands/common/tools.py",
            ],
            legacy_config,
        )
        assert result.tier == "recommended"
        assert not result.matched_must
        assert len(result.matched_recommended) == 2

    def test_skip_beats_must(self, legacy_config: GateConfig) -> None:
        """A test file under a Must path should not trigger the gate."""
        result = classify(
            [
                "demisto_sdk/commands/content_graph/objects/tests/pack_test.py",
                "demisto_sdk/commands/content_graph/objects/pack.md",
            ],
            legacy_config,
        )
        assert result.tier == "skip_only"
        assert result.matched_must == []
        assert len(result.matched_skip) == 2

    def test_only_unmatched_files_yields_none(self, legacy_config: GateConfig) -> None:
        result = classify(["some/other/file.py", "toplevel_file.txt"], legacy_config)
        assert result.tier == "none"
        assert result.matched_must == []
        assert result.matched_recommended == []
        assert result.matched_skip == []
        assert len(result.unmatched) == 2

    def test_mixed_skip_and_recommended_is_recommended(
        self, legacy_config: GateConfig
    ) -> None:
        result = classify(
            [
                "demisto_sdk/commands/validate/foo.py",
                "demisto_sdk/commands/validate/tests/foo_test.py",
                "docs/CHANGELOG.md",
            ],
            legacy_config,
        )
        assert result.tier == "recommended"
        assert result.matched_recommended == ["demisto_sdk/commands/validate/foo.py"]
        assert len(result.matched_skip) == 2

    def test_blank_lines_are_ignored(self, legacy_config: GateConfig) -> None:
        result = classify(
            ["", "  ", "demisto_sdk/commands/common/docker_helper.py"],
            legacy_config,
        )
        assert result.tier == "must"
        assert len(result.matched_must) == 1

    def test_docker_prefix_pattern(self, legacy_config: GateConfig) -> None:
        # `docker**` should also match nested files.
        result = classify(
            ["demisto_sdk/commands/common/docker_helper/utils.py"],
            legacy_config,
        )
        assert result.tier == "must"


# ---------------------------------------------------------------------------
# classify() - modern mode (must: ['**'] + must_exclude)
# ---------------------------------------------------------------------------


class TestClassifyModernMode:
    """The `must: ['**']` + `must_exclude` semantics.

    Under this model, **any** SDK change is a must-hit unless it is
    explicitly downgraded via `must_exclude` or ignored via `skip`.
    """

    def test_arbitrary_sdk_file_is_must(self, modern_config: GateConfig) -> None:
        # A file that used to not be listed at all in the legacy config
        # (e.g. any random validator) is now must-tier by default.
        result = classify(
            ["demisto_sdk/commands/validate/validators/BA_validators/BA100.py"],
            modern_config,
        )
        assert result.tier == "must"
        assert result.matched_must == [
            "demisto_sdk/commands/validate/validators/BA_validators/BA100.py"
        ]
        assert result.matched_recommended == []

    def test_must_exclude_downgrades_to_recommended(
        self, modern_config: GateConfig
    ) -> None:
        result = classify(
            ["demisto_sdk/commands/prepare_content/prepare_upload_manager.py"],
            modern_config,
        )
        assert result.tier == "recommended"
        assert result.matched_must == []
        assert result.matched_recommended == [
            "demisto_sdk/commands/prepare_content/prepare_upload_manager.py"
        ]

    def test_skip_beats_must_and_must_exclude(self, modern_config: GateConfig) -> None:
        """A test file must be skipped even though `**` also matches it."""
        result = classify(
            [
                "demisto_sdk/commands/prepare_content/tests/foo_test.py",
                "docs/README.md",
                ".github/copilot-instructions.md",
                ".changelog/1234.yml",
                "Utils/github_workflow_scripts/some_script.py",
            ],
            modern_config,
        )
        assert result.tier == "skip_only"
        assert result.matched_must == []
        assert result.matched_recommended == []
        assert len(result.matched_skip) == 5

    def test_must_and_must_exclude_together(self, modern_config: GateConfig) -> None:
        """Must wins over must_exclude at the overall-tier level.

        Any single must-hit forces the whole PR into `must`, even when
        every other file was downgraded.
        """
        result = classify(
            [
                # Must-hit (not in must_exclude, not in skip).
                "demisto_sdk/commands/content_graph/objects/pack.py",
                # Downgraded to recommended.
                "demisto_sdk/commands/common/tools.py",
                # Skipped.
                "README.md",
            ],
            modern_config,
        )
        assert result.tier == "must"
        assert result.matched_must == [
            "demisto_sdk/commands/content_graph/objects/pack.py"
        ]
        assert result.matched_recommended == ["demisto_sdk/commands/common/tools.py"]
        assert result.matched_skip == ["README.md"]

    def test_only_excluded_files_is_recommended(
        self, modern_config: GateConfig
    ) -> None:
        result = classify(
            [
                "demisto_sdk/commands/common/tools.py",
                "demisto_sdk/commands/prepare_content/prepare_upload_manager.py",
            ],
            modern_config,
        )
        assert result.tier == "recommended"
        assert result.matched_must == []
        assert len(result.matched_recommended) == 2

    def test_only_skipped_files_is_skip_only(self, modern_config: GateConfig) -> None:
        result = classify(
            [
                "README.md",
                "docs/architecture.md",
                ".github/workflows/nightly-gate.yml",
            ],
            modern_config,
        )
        assert result.tier == "skip_only"

    def test_empty_input_is_none(self, modern_config: GateConfig) -> None:
        assert classify([], modern_config).tier == "none"


# ---------------------------------------------------------------------------
# decide()
# ---------------------------------------------------------------------------


class TestDecide:
    def _cls(self, tier: str) -> Classification:
        return Classification(
            tier=tier,
            matched_must=(["a/must.py"] if tier == "must" else []),
            matched_recommended=(["a/rec.py"] if tier == "recommended" else []),
        )

    def test_must_no_label_fails(self) -> None:
        decision = decide(self._cls("must"), labels=[])
        assert decision.exit_code == 1
        assert decision.status == "fail"
        assert decision.comment_body is not None
        assert COMMENT_MARKER in decision.comment_body
        assert LABEL_PASSED in decision.comment_body
        assert LABEL_SKIPPED in decision.comment_body

    def test_must_fail_comment_mentions_content_build_alternative(self) -> None:
        decision = decide(self._cls("must"), labels=[])
        assert decision.comment_body is not None
        # The alternative escape hatch must be surfaced so authors know
        # they don't necessarily have to run the full nightly.
        assert "Content build" in decision.comment_body
        # It must be wrapped in a collapsible `<details>` block so the
        # primary "here's what you need to do" instructions stay above
        # the fold in the sticky PR comment.
        assert "<details>" in decision.comment_body
        assert "click to expand" in decision.comment_body
        # The Content build's config file is `validation_config.toml`
        # (which lives in the Content repo, not the SDK's
        # `sdk_validation_config.toml`). Pin the correct filename so a
        # future refactor doesn't accidentally flip it back to the
        # SDK-side name.
        assert "validation_config.toml" in decision.comment_body
        assert "sdk_validation_config.toml" not in decision.comment_body
        # And it must explicitly call out the `-a` requirement so no one
        # tries to use `-g` (which wouldn't exercise a new validator on
        # unchanged files).
        assert "validate -a" in decision.comment_body

    def test_must_with_passed_label_ok(self) -> None:
        decision = decide(self._cls("must"), labels=[LABEL_PASSED])
        assert decision.exit_code == 0
        assert decision.status == "ok"
        assert decision.comment_body is not None
        # Passed-label path: acknowledgement is a clean ✅, no pushback.
        assert "acknowledged (required)" in decision.comment_body
        assert "reconsider" not in decision.comment_body

    def test_must_with_skipped_label_is_ok_but_pushes_back(self) -> None:
        """`nightly-run-skipped` on a must-tier PR must not fail the check,
        but should nudge the author to reconsider and mention the
        Content-build alternative."""
        decision = decide(self._cls("must"), labels=[LABEL_SKIPPED])
        assert decision.exit_code == 0
        assert decision.status == "ok"
        assert decision.comment_body is not None
        # Distinct header + explicit "reconsider" wording so it's not
        # confused with a plain acknowledgement.
        assert "SDK Nightly skipped for a required change" in decision.comment_body
        assert "reconsider" in decision.comment_body
        # Must still mention the Content-build alternative so the author
        # sees the recommended way to move to `nightly-run-passed`.
        assert "Content build" in decision.comment_body
        assert "validation_config.toml" in decision.comment_body
        assert "sdk_validation_config.toml" not in decision.comment_body

    def test_must_with_both_labels_prefers_passed(self) -> None:
        decision = decide(self._cls("must"), labels=[LABEL_PASSED, LABEL_SKIPPED])
        # Both labels present: treat as "passed" (pipeline actually ran),
        # so no pushback wording.
        assert decision.status == "ok"
        assert decision.comment_body is not None
        assert "acknowledged (required)" in decision.comment_body
        assert "reconsider" not in decision.comment_body

    def test_recommended_no_label_warns(self) -> None:
        decision = decide(self._cls("recommended"), labels=[])
        assert decision.exit_code == 0
        assert decision.status == "warn"
        assert decision.comment_body is not None
        assert "recommended" in decision.comment_body.lower()

    def test_recommended_warn_comment_mentions_content_build_alternative(self) -> None:
        decision = decide(self._cls("recommended"), labels=[])
        assert decision.comment_body is not None
        assert "Content build" in decision.comment_body
        assert "validation_config.toml" in decision.comment_body
        assert "sdk_validation_config.toml" not in decision.comment_body

    def test_recommended_with_passed_label_ok(self) -> None:
        decision = decide(self._cls("recommended"), labels=[LABEL_PASSED])
        assert decision.exit_code == 0
        assert decision.status == "ok"
        assert decision.comment_body is not None
        assert "acknowledged (recommended)" in decision.comment_body

    def test_recommended_with_skipped_label_ok(self) -> None:
        decision = decide(self._cls("recommended"), labels=[LABEL_SKIPPED])
        assert decision.exit_code == 0
        assert decision.status == "ok"
        assert decision.comment_body is not None
        # Distinct header so authors know the pipeline was intentionally
        # skipped rather than run + passed.
        assert "recommended, skipped" in decision.comment_body

    def test_none_tier_is_noop_and_deletes_stale_comment(self) -> None:
        decision = decide(self._cls("none"), labels=[])
        assert decision.exit_code == 0
        assert decision.status == "noop"
        assert decision.comment_body is None
        assert decision.delete_comment is True

    def test_skip_only_tier_is_noop(self) -> None:
        decision = decide(self._cls("skip_only"), labels=[])
        assert decision.exit_code == 0
        assert decision.status == "noop"
        assert decision.delete_comment is True

    def test_unrelated_labels_do_not_satisfy_gate(self) -> None:
        decision = decide(self._cls("must"), labels=["bug", "documentation"])
        assert decision.status == "fail"

    def test_label_matching_is_case_insensitive(self) -> None:
        decision = decide(self._cls("must"), labels=["NIGHTLY-RUN-PASSED"])
        assert decision.status == "ok"

    def test_decision_dataclass_shape(self) -> None:
        # Sanity check the Decision dataclass surface stays stable
        # (workflow YAML parses its string fields).
        d = Decision(
            exit_code=1,
            status=DecisionStatus.FAIL,
            comment_body="x",
            delete_comment=False,
        )
        assert d.exit_code == 1
        # Enum inherits from `str`, so string comparison must still hold
        # for every downstream caller that predates the enum introduction.
        assert d.status == "fail"
        assert d.status is DecisionStatus.FAIL
        assert d.comment_body == "x"
        assert d.delete_comment is False

    def test_decision_status_enum_is_str_subclass(self) -> None:
        # Guard the DecisionStatus contract: values ARE strings so
        # existing `== "fail"` checks, `in ("fail", "warn")` membership
        # tests, and JSON serialization keep working unchanged.
        assert issubclass(DecisionStatus, str)
        assert DecisionStatus.OK == "ok"
        assert DecisionStatus.WARN == "warn"
        assert DecisionStatus.FAIL == "fail"
        assert DecisionStatus.NOOP == "noop"
        assert DecisionStatus.FAIL in ("fail", "warn")


# ---------------------------------------------------------------------------
# _parse_labels
# ---------------------------------------------------------------------------


class TestParseLabels:
    """Cover the JSON-first label parser used by the GitHub Actions
    workflow so the shell no longer has to munge comma-containing
    labels."""

    def test_json_takes_precedence_over_csv(self) -> None:
        assert _parse_labels(
            '["nightly-run-passed", "foo"]', "ignored,csv"
        ) == ["nightly-run-passed", "foo"]

    def test_empty_json_falls_back_to_csv(self) -> None:
        assert _parse_labels("", "a, b, c") == ["a", "b", "c"]

    def test_whitespace_only_json_falls_back_to_csv(self) -> None:
        assert _parse_labels("   ", "x,y") == ["x", "y"]

    def test_json_preserves_labels_with_commas(self) -> None:
        # The whole point of switching to JSON: a shell CSV round-trip
        # would split "weird, label" into two bogus labels.
        assert _parse_labels('["weird, label", "clean"]', "") == [
            "weird, label",
            "clean",
        ]

    def test_empty_json_array_yields_empty_list(self) -> None:
        assert _parse_labels("[]", "ignored") == []

    def test_both_empty_yields_empty_list(self) -> None:
        assert _parse_labels("", "") == []

    def test_invalid_json_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            _parse_labels("not json", "")

    def test_non_array_json_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            _parse_labels('{"not": "an array"}', "")

    def test_json_array_with_non_strings_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            _parse_labels('["ok", 42]', "")


# ---------------------------------------------------------------------------
# _render_ok_comment
# ---------------------------------------------------------------------------


class TestRenderOkComment:
    """Directly cover the branches of the OK-comment renderer so the
    tier x label matrix is fully exercised even for edge cases that
    `decide()` never emits."""

    def _cls(self, tier: str) -> Classification:
        return Classification(
            tier=tier,
            matched_must=(["x/must.py"] if tier == "must" else []),
            matched_recommended=(["x/rec.py"] if tier == "recommended" else []),
        )

    def test_must_passed_is_plain_ack(self) -> None:
        out = _render_ok_comment(self._cls("must"), tier="must", label=LABEL_PASSED)
        assert "acknowledged (required)" in out
        assert "reconsider" not in out
        # Files list is included in a `<details>` block.
        assert "x/must.py" in out

    def test_must_skipped_pushes_back(self) -> None:
        out = _render_ok_comment(self._cls("must"), tier="must", label=LABEL_SKIPPED)
        assert "SDK Nightly skipped for a required change" in out
        assert "reconsider" in out
        assert "does not block merge" in out
        # Alternative footer is embedded here too.
        assert "Content build" in out
        assert "validation_config.toml" in out
        assert "sdk_validation_config.toml" not in out

    def test_recommended_passed_is_plain_ack(self) -> None:
        out = _render_ok_comment(
            self._cls("recommended"), tier="recommended", label=LABEL_PASSED
        )
        assert "acknowledged (recommended)" in out
        assert "skipped" not in out

    def test_recommended_skipped_is_distinct_ack(self) -> None:
        out = _render_ok_comment(
            self._cls("recommended"), tier="recommended", label=LABEL_SKIPPED
        )
        assert "recommended, skipped" in out

    def test_default_label_argument_is_passed(self) -> None:
        # Guards against accidental default flip (would silently turn
        # every ack into the "skipped-anyway" pushback).
        out = _render_ok_comment(self._cls("must"), tier="must")
        assert "acknowledged (required)" in out
        assert "reconsider" not in out


# ---------------------------------------------------------------------------
# Real config file
# ---------------------------------------------------------------------------


REAL_CONFIG = Path(__file__).resolve().parents[4] / ".github" / "nightly-gate-paths.yml"


class TestRealConfig:
    """Smoke tests against the actual `.github/nightly-gate-paths.yml`.

    The shipping config uses the legacy explicit-list model (`must` and
    `recommended` are enumerated per-path). The classifier's modern
    `must_exclude` model is still fully implemented and exercised by
    `TestClassifyModernMode` above, but is NOT enabled in the real
    config right now.
    """

    @pytest.fixture(scope="class")
    def cfg(self) -> GateConfig:
        return load_config(REAL_CONFIG)

    def test_config_loads(self, cfg: GateConfig) -> None:
        assert cfg.must, "Must list should not be empty"
        assert cfg.recommended, "Recommended list should not be empty"
        assert cfg.skip, "Skip list should not be empty"

    @pytest.mark.parametrize(
        "changed_file",
        [
            # Historically-must files under content_graph.
            "demisto_sdk/commands/content_graph/objects/pack.py",
            "demisto_sdk/commands/content_graph/parsers/integration_parser.py",
            "demisto_sdk/commands/content_graph/common.py",
            "demisto_sdk/commands/content_graph/neo4j_service.py",
            "demisto_sdk/commands/content_graph/content_graph_builder.py",
            "demisto_sdk/commands/content_graph/interface/graph.py",
            "demisto_sdk/commands/content_graph/strict_objects/pack.py",
            "demisto_sdk/commands/content_graph/commands/create.py",
            # New: `content_graph/**` now sweeps in any other top-level
            # .py in that subtree (previously not listed at all).
            "demisto_sdk/commands/content_graph/content_graph_setup.py",
            # Non-content_graph must files.
            "demisto_sdk/commands/validate/private_content_manager.py",
            "demisto_sdk/commands/validate/validators/GR_validators/GR105_x.py",
            "demisto_sdk/commands/common/docker_helper.py",
            "demisto_sdk/commands/common/docker.py",
        ],
    )
    def test_real_must_files_hit_must_tier(
        self, cfg: GateConfig, changed_file: str
    ) -> None:
        assert classify([changed_file], cfg).tier == "must"

    @pytest.mark.parametrize(
        "changed_file",
        [
            "demisto_sdk/commands/validate/validators/BA_validators/BA100.py",
            "demisto_sdk/commands/prepare_content/prepare_upload_manager.py",
            "demisto_sdk/commands/upload/upload.py",
            "demisto_sdk/commands/create_artifacts/content_artifacts_creator.py",
            "demisto_sdk/commands/update_release_notes/update_rn.py",
            "demisto_sdk/commands/pre_commit/pre_commit_command.py",
            "demisto_sdk/commands/common/git_util.py",
            "demisto_sdk/commands/common/tools.py",
            "demisto_sdk/commands/common/constants.py",
        ],
    )
    def test_real_recommended_files_hit_recommended_tier(
        self, cfg: GateConfig, changed_file: str
    ) -> None:
        assert classify([changed_file], cfg).tier == "recommended"

    @pytest.mark.parametrize(
        "changed_file",
        [
            "demisto_sdk/commands/content_graph/objects/tests/pack_test.py",
            "demisto_sdk/commands/content_graph/objects/test_data/x.json",
            "demisto_sdk/commands/validate/README.md",
            "demisto_sdk/commands/content_graph/images/graph.png",
        ],
    )
    def test_real_skip_files_ignored(self, cfg: GateConfig, changed_file: str) -> None:
        # Either skip_only (if it's the only file) or the file falls out
        # of the must/recommended lists entirely.
        result = classify([changed_file], cfg)
        assert result.tier == "skip_only"
        assert result.matched_must == []
        assert result.matched_recommended == []

    def test_real_unrelated_file_is_noop(self, cfg: GateConfig) -> None:
        assert classify(["demisto_sdk/utils/utils.py"], cfg).tier == "none"
