"""
Unit tests for ``check_nightly_gate.py``.

The tests are deliberately focused on the two pure functions that
carry all the business logic (``classify`` and ``decide``) plus a few
targeted checks on the glob compiler, since a subtle bug there would
either let must-files slip through or block innocent PRs.
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
    GateConfig,
    _glob_to_regex,
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
def sample_config() -> GateConfig:
    """A minimal config exercising all three tiers and overlaps."""
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


# ---------------------------------------------------------------------------
# classify()
# ---------------------------------------------------------------------------


class TestClassify:
    def test_no_files_yields_none_tier(self, sample_config: GateConfig) -> None:
        result = classify([], sample_config)
        assert result.tier == "none"
        assert result == Classification(tier="none")

    def test_must_hit_wins_over_recommended(self, sample_config: GateConfig) -> None:
        result = classify(
            [
                "demisto_sdk/commands/content_graph/objects/pack.py",
                "demisto_sdk/commands/validate/foo.py",
            ],
            sample_config,
        )
        assert result.tier == "must"
        assert result.matched_must == [
            "demisto_sdk/commands/content_graph/objects/pack.py"
        ]
        assert result.matched_recommended == ["demisto_sdk/commands/validate/foo.py"]

    def test_recommended_only(self, sample_config: GateConfig) -> None:
        result = classify(
            [
                "demisto_sdk/commands/validate/foo.py",
                "demisto_sdk/commands/common/tools.py",
            ],
            sample_config,
        )
        assert result.tier == "recommended"
        assert not result.matched_must
        assert len(result.matched_recommended) == 2

    def test_skip_beats_must(self, sample_config: GateConfig) -> None:
        """A test file under a Must path should not trigger the gate."""
        result = classify(
            [
                "demisto_sdk/commands/content_graph/objects/tests/pack_test.py",
                "demisto_sdk/commands/content_graph/objects/pack.md",
            ],
            sample_config,
        )
        assert result.tier == "skip_only"
        assert result.matched_must == []
        assert len(result.matched_skip) == 2

    def test_only_unmatched_files_yields_none(self, sample_config: GateConfig) -> None:
        result = classify(["some/other/file.py", "toplevel_file.txt"], sample_config)
        assert result.tier == "none"
        assert result.matched_must == []
        assert result.matched_recommended == []
        assert result.matched_skip == []
        assert len(result.unmatched) == 2

    def test_mixed_skip_and_recommended_is_recommended(
        self, sample_config: GateConfig
    ) -> None:
        result = classify(
            [
                "demisto_sdk/commands/validate/foo.py",
                "demisto_sdk/commands/validate/tests/foo_test.py",
                "docs/CHANGELOG.md",
            ],
            sample_config,
        )
        assert result.tier == "recommended"
        assert result.matched_recommended == ["demisto_sdk/commands/validate/foo.py"]
        assert len(result.matched_skip) == 2

    def test_blank_lines_are_ignored(self, sample_config: GateConfig) -> None:
        result = classify(
            ["", "  ", "demisto_sdk/commands/common/docker_helper.py"],
            sample_config,
        )
        assert result.tier == "must"
        assert len(result.matched_must) == 1

    def test_docker_prefix_pattern(self, sample_config: GateConfig) -> None:
        # `docker**` should also match nested files.
        result = classify(
            ["demisto_sdk/commands/common/docker_helper/utils.py"],
            sample_config,
        )
        assert result.tier == "must"


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

    def test_must_with_passed_label_ok(self) -> None:
        decision = decide(self._cls("must"), labels=[LABEL_PASSED])
        assert decision.exit_code == 0
        assert decision.status == "ok"
        assert decision.comment_body is not None

    def test_must_with_skipped_label_ok(self) -> None:
        decision = decide(self._cls("must"), labels=[LABEL_SKIPPED])
        assert decision.exit_code == 0
        assert decision.status == "ok"

    def test_recommended_no_label_warns(self) -> None:
        decision = decide(self._cls("recommended"), labels=[])
        assert decision.exit_code == 0
        assert decision.status == "warn"
        assert decision.comment_body is not None
        assert "recommended" in decision.comment_body.lower()

    def test_recommended_with_label_ok(self) -> None:
        decision = decide(self._cls("recommended"), labels=[LABEL_PASSED])
        assert decision.exit_code == 0
        assert decision.status == "ok"

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
        d = Decision(exit_code=1, status="fail", comment_body="x", delete_comment=False)
        assert d.exit_code == 1
        assert d.status == "fail"
        assert d.comment_body == "x"
        assert d.delete_comment is False


# ---------------------------------------------------------------------------
# Real config file
# ---------------------------------------------------------------------------


REAL_CONFIG = Path(__file__).resolve().parents[4] / ".github" / "nightly-gate-paths.yml"


class TestRealConfig:
    """Smoke tests against the actual `.github/nightly-gate-paths.yml`."""

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
            "demisto_sdk/commands/content_graph/objects/pack.py",
            "demisto_sdk/commands/content_graph/parsers/integration_parser.py",
            "demisto_sdk/commands/content_graph/common.py",
            "demisto_sdk/commands/content_graph/neo4j_service.py",
            "demisto_sdk/commands/validate/private_content_manager.py",
            "demisto_sdk/commands/validate/validators/GR_validators/GR105_x.py",
            "demisto_sdk/commands/common/docker_helper.py",
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
