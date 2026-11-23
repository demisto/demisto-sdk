"""
Classify files changed in a pull request against the SDK Nightly Gate
path configuration and enforce the gating policy.

This script is invoked by the `.github/workflows/nightly-gate.yml`
workflow. It:

1. Reads the path configuration from `.github/nightly-gate-paths.yml`.
2. Reads the list of changed files from a file (one path per line),
   typically produced by `git diff --name-only <base_sha>...<head_sha>`.
3. Classifies the change set into one of four tiers: `must`,
   `recommended`, `none`, or `skip_only`.
4. Determines the required action given the PR's current labels.
5. Writes GitHub Actions outputs (via the `GITHUB_OUTPUT` file) so the
   workflow can decide whether to fail, warn, or pass, and what
   comment to post.

The classifier is intentionally kept small and dependency-light (only
`ruamel.yaml`, which is already a project dependency). Glob patterns
are compiled to regex with support for `**` (recursive) and `*`
(single segment) so the script does not require `pathspec` or
`wcmatch` to be installed.

Config model
------------
The gate supports two config shapes:

* **Modern (preferred):** `must: ['**']` plus a `must_exclude` list of
  paths that should be downgraded to `recommended`, plus a `skip` list
  of paths that are ignored entirely. Rationale: SDK changes are
  nightly-relevant by default; the exclude list encodes the rare
  exceptions.
* **Legacy:** explicit `must` and `recommended` lists (both taking
  gitignore-style globs), plus `skip`. Kept working for backwards
  compatibility with older `.github/nightly-gate-paths.yml` snapshots.

When `must_exclude` is non-empty, the modern precedence applies:

    skip > must_exclude > must

Otherwise the classifier falls back to the legacy precedence:

    skip > must > recommended
"""

from __future__ import annotations

import argparse
import enum
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from ruamel.yaml import YAML

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Label the author adds when the SDK nightly run passed for this branch.
LABEL_PASSED = "nightly-run-passed"

#: Label the author adds when the SDK nightly run was intentionally skipped
#: (only meaningful for the `recommended` tier, or as an explicit override
#: for the `must` tier with reviewer approval).
LABEL_SKIPPED = "nightly-run-skipped"

#: Hidden marker used to identify the sticky comment posted by the workflow.
#: Kept as a public constant so the workflow can grep for the exact same
#: string when it needs to update or delete the comment.
COMMENT_MARKER = "<!-- nightly-gate-bot -->"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GateConfig:
    """Path globs for each tier, as loaded from the YAML config.

    * ``must``          -> globs of paths that require a nightly run
                           (defaults to ``['**']`` under the modern model).
    * ``must_exclude``  -> globs downgraded from ``must`` to
                           ``recommended`` (modern model only).
    * ``recommended``   -> legacy explicit-list mode. Ignored when
                           ``must_exclude`` is non-empty.
    * ``skip``          -> globs ignored entirely by the gate.
    """

    must: list[str] = field(default_factory=list)
    must_exclude: list[str] = field(default_factory=list)
    recommended: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)


@dataclass
class Classification:
    """Result of classifying a set of changed files against the config."""

    tier: str  # one of: "must", "recommended", "none", "skip_only"
    matched_must: list[str] = field(default_factory=list)
    matched_recommended: list[str] = field(default_factory=list)
    matched_skip: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Glob matching
# ---------------------------------------------------------------------------


#: Table of gitignore-style glob tokens and the regex fragments they
#: translate to. Order matters: multi-character tokens must precede
#: their single-character prefixes so ``**`` is not tokenized as two
#: ``*``. Each entry is ``(token, replacement)`` where ``replacement``
#: is a callable so it can look at surrounding context (only ``**/``
#: and ``/**/`` need this to collapse the surrounding slash).
# NOTE on alternation order: multi-character tokens must come before
# single-character ones so ``**`` is never split into two ``*``.
# ``/`` is its own token (rather than being absorbed into ``literal``)
# so ``/**/`` cannot be pre-consumed as ``literal(/) + double_star(**)
# + literal(/)`` - that would lose the "zero-directory" collapsing
# semantics required by e.g. ``a/**/b`` matching ``a/b``.
_GLOB_TOKENIZER = re.compile(
    r"""
      (?P<double_star_dir>    /\*\*/  )   # /**/ - zero-or-more path segments
    | (?P<lead_double_star>   ^\*\*/  )   # leading **/ - optional prefix
    | (?P<double_star>        \*\*    )   # bare ** - match anything
    | (?P<star>               \*      )   # * - single path segment
    | (?P<question>           \?      )   # ? - single non-slash char
    | (?P<slash>              /       )   # / - literal path separator
    | (?P<literal>            [^*?/]+ )   # everything else, escaped verbatim
    """,
    re.VERBOSE,
)

_GLOB_REPLACEMENTS: dict[str, str] = {
    # "a/**/b" -> "a(?:/.*)?/b" so both "a/b" and "a/x/y/b" match.
    "double_star_dir": r"(?:/.*)?/",
    # "**/foo" at start -> "(?:.*/)?foo".
    "lead_double_star": r"(?:.*/)?",
    # Bare "**" at end or unusual middle position: match anything.
    "double_star": r".*",
    # Single "*": match anything within a path segment.
    "star": r"[^/]*",
    # Single "?": match one char that is not a path separator.
    "question": r"[^/]",
    # Literal "/" - no escaping needed, but must be a distinct token.
    "slash": "/",
}


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a gitignore-style glob into a compiled regex.

    Supports:

    * ``**`` - matches any number of characters including path
      separators (recursive descent). When it appears as a whole path
      segment (``a/**/b`` or ``**/b``), the surrounding ``/`` is
      collapsed so ``a/b`` (zero-directory) also matches - matching
      gitignore semantics.
    * ``*``  - matches any character except ``/`` (single path segment).
    * ``?``  - matches a single character except ``/``.
    * All other regex metacharacters are escaped verbatim.

    The returned regex is anchored (``^...$``) and case-sensitive, to
    match POSIX file semantics used by git on Linux CI runners.

    Implementation note: this stays a small hand-rolled translator on
    purpose. ``fnmatch`` has no concept of ``**`` and treats ``*`` as
    "any character including /", which is the wrong semantics for
    gitignore-style path globs. ``glob`` walks the real filesystem,
    which we do not have (paths come from ``git diff --name-only``).
    ``pathlib.PurePosixPath.full_match`` supports ``**`` but only
    landed in Python 3.13, and the project targets 3.10+.
    """
    parts: list[str] = ["^"]
    for match in _GLOB_TOKENIZER.finditer(pattern):
        kind = match.lastgroup
        assert kind is not None  # every char is covered by the alternation
        token = match.group(kind)
        if kind == "literal":
            parts.append(re.escape(token))
        else:
            parts.append(_GLOB_REPLACEMENTS[kind])
    parts.append("$")
    return re.compile("".join(parts))


def _compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    """Compile a list of glob patterns into regexes."""
    return [_glob_to_regex(p) for p in patterns]


def _matches_any(path: str, compiled: list[re.Pattern[str]]) -> bool:
    """Return True if ``path`` matches any of the compiled patterns."""
    return any(rx.match(path) for rx in compiled)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify(files: Iterable[str], config: GateConfig) -> Classification:
    """Classify a set of changed files against the gate configuration.

    Two modes are supported:

    * **Modern** (``must_exclude`` is non-empty). Per-file precedence:
      ``skip > must_exclude (-> recommended) > must``. A file that is
      not skipped and not excluded is `must` (which typically comes
      from ``must: ['**']``).
    * **Legacy** (``must_exclude`` is empty). Per-file precedence:
      ``skip > must > recommended``, matching the old semantics.

    Overall tier is the highest hit across all non-skipped files:
        * ``must``        - at least one file matches a Must glob.
        * ``recommended`` - no Must hits, at least one Recommended hit.
        * ``skip_only``   - every changed file matched a Skip glob.
        * ``none``        - files were considered but nothing matched
                            (no gate applies).
    """
    skip_rx = _compile_patterns(config.skip)
    must_rx = _compile_patterns(config.must)
    must_exclude_rx = _compile_patterns(config.must_exclude)
    rec_rx = _compile_patterns(config.recommended)

    modern_mode = bool(config.must_exclude)

    result = Classification(tier="none")

    for raw in files:
        path = raw.strip()
        if not path:
            continue

        # Skip always wins.
        if _matches_any(path, skip_rx):
            result.matched_skip.append(path)
            continue

        if modern_mode:
            # Modern: must_exclude downgrades to recommended, otherwise
            # anything matching `must` (usually `**`) is a must-hit.
            if _matches_any(path, must_exclude_rx):
                result.matched_recommended.append(path)
                continue
            if _matches_any(path, must_rx):
                result.matched_must.append(path)
                continue
            # Nothing matched (only possible if `must` is not `**`).
            result.unmatched.append(path)
            continue

        # Legacy: explicit lists per tier.
        if _matches_any(path, must_rx):
            result.matched_must.append(path)
            continue

        if _matches_any(path, rec_rx):
            result.matched_recommended.append(path)
            continue

        result.unmatched.append(path)

    # Decide the overall tier.
    if result.matched_must:
        result.tier = "must"
    elif result.matched_recommended:
        result.tier = "recommended"
    elif result.matched_skip and not result.unmatched:
        result.tier = "skip_only"
    else:
        result.tier = "none"

    return result


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class DecisionStatus(str, enum.Enum):
    """Enumerated outcome states surfaced by :func:`decide`.

    Inherits from :class:`str` so existing string comparisons
    (``decision.status == "fail"``, ``in ("fail", "warn")``, JSON
    serialization) continue to work unchanged - the enum values ARE
    strings. Python 3.11+ ships :class:`enum.StrEnum` which would be
    slightly nicer, but the project targets 3.10+.
    """

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    NOOP = "noop"


@dataclass
class Decision:
    """Final decision for the workflow step."""

    exit_code: int
    status: DecisionStatus
    comment_body: str | None
    delete_comment: bool = False


def decide(classification: Classification, labels: Iterable[str]) -> Decision:
    """Given a classification and the PR's labels, decide the outcome.

    Rules:
        * tier == 'must' + `nightly-run-passed`   -> ok (ack comment)
        * tier == 'must' + `nightly-run-skipped`  -> ok, but the ack
          comment gently pushes back: the file *does* warrant a nightly
          run; author may want to reconsider. Does NOT fail the check.
        * tier == 'must' + no label               -> fail
        * tier == 'recommended' + label           -> ok (ack comment)
        * tier == 'recommended' + no label        -> warn (reminder)
        * tier in {'none', 'skip_only'}           -> noop
          (workflow deletes any stale comment)
    """
    # Normalize once so we can look up which specific label satisfied
    # the gate (needed for the "skipped anyway" acknowledgement).
    normalized_labels = {lbl.lower() for lbl in labels}
    has_passed = LABEL_PASSED in normalized_labels
    has_skipped = LABEL_SKIPPED in normalized_labels
    has_label = has_passed or has_skipped
    # `passed` wins over `skipped` when both are set, since the pipeline
    # actually ran.
    satisfying_label = LABEL_PASSED if has_passed else LABEL_SKIPPED

    # Structural-pattern-match on the (tier, has_label) decision table.
    # Each `case` below is one row of that table, which reads much closer
    # to the docstring's rule list than the previous nested if/else.
    match classification.tier, has_label:
        case "must", True:
            return Decision(
                exit_code=0,
                status=DecisionStatus.OK,
                comment_body=_render_ok_comment(
                    classification, tier="must", label=satisfying_label
                ),
            )
        case "must", False:
            return Decision(
                exit_code=1,
                status=DecisionStatus.FAIL,
                comment_body=_render_fail_comment(classification),
            )
        case "recommended", True:
            return Decision(
                exit_code=0,
                status=DecisionStatus.OK,
                comment_body=_render_ok_comment(
                    classification,
                    tier="recommended",
                    label=satisfying_label,
                ),
            )
        case "recommended", False:
            return Decision(
                exit_code=0,
                status=DecisionStatus.WARN,
                comment_body=_render_warn_comment(classification),
            )
        case _:
            # tier in {'none', 'skip_only'}: nothing to enforce; remove
            # any stale comment left over from previous runs.
            return Decision(
                exit_code=0,
                status=DecisionStatus.NOOP,
                comment_body=None,
                delete_comment=True,
            )


# ---------------------------------------------------------------------------
# Comment rendering
# ---------------------------------------------------------------------------


def _render_file_list(files: list[str], limit: int = 25) -> str:
    """Render a bulleted list of files, truncating if very long."""
    shown = files[:limit]
    # Strip trailing backslashes / whitespace from each path. Without this
    # a stray `\` (which GitHub renders as a hard line-break) can leak in
    # from the changed-files transport and show up inside each code span.
    lines = [f"- `{f.rstrip(chr(92)).strip()}`" for f in shown]
    if len(files) > limit:
        lines.append(f"- _(and {len(files) - limit} more)_")
    return "\n".join(lines)


#: Reusable footer explaining the Content-build escape hatch. Emitted on
#: every non-ack comment so authors know they have an alternative to a
#: full nightly run when the change is small (e.g. one new validator).
# Rendered inside every fail / warn / skipped-anyway comment. Kept in a
# `<details>` block so the primary "what do I need to do" instructions
# stay above the fold and this longer explanation is opt-in.
_CONTENT_BUILD_ALTERNATIVE = f"""\
<details>
<summary><strong>Alternative:</strong> run a Content build instead of the full SDK Nightly (click to expand)</summary>

If your change is scoped (e.g. a single new validator or a small bug \
fix), you can run a **Content build against this SDK branch** instead \
of the full SDK Nightly pipeline. When your change is a new validator, \
make sure it is registered in the Content repo's \
`validation_config.toml` so the Content build's `run-validations` job \
picks it up via `demisto-sdk validate -a` (the `-a` "all files" mode is \
what `run-validations` uses; a `-g` "git-diff" run will not exercise \
your new validator on unchanged files). Once the Content build is \
green, add the **`{LABEL_PASSED}`** label to satisfy this gate.

</details>"""


def _render_fail_comment(cls: Classification) -> str:
    return f"""{COMMENT_MARKER}
### 🚫 SDK Nightly required

This PR modifies files that require the **SDK Nightly** pipeline to \
be run before it can be merged:

{_render_file_list(cls.matched_must)}

**Required action:**

1. Run the SDK Nightly pipeline against this branch.
2. Add a link to the nightly run in this PR's description.
3. Add the **`{LABEL_PASSED}`** label once the run has passed \
(or **`{LABEL_SKIPPED}`** if you have a documented reason not to run \
it, with reviewer approval).

{_CONTENT_BUILD_ALTERNATIVE}

This check will re-run automatically when a label is added or removed.
"""


def _render_warn_comment(cls: Classification) -> str:
    return f"""{COMMENT_MARKER}
### ⚠️ SDK Nightly recommended

This PR modifies files where running the **SDK Nightly** pipeline is \
recommended:

{_render_file_list(cls.matched_recommended)}

**Please decide:**

* If you ran the nightly and it passed, add a link to the run in the \
PR description and apply the **`{LABEL_PASSED}`** label.
* If you consciously chose not to run it, apply the \
**`{LABEL_SKIPPED}`** label so reviewers know it was skipped on \
purpose.

{_CONTENT_BUILD_ALTERNATIVE}

This check is non-blocking, but reviewers may request one of the \
labels before merging. It will re-evaluate automatically when a \
label is added or removed.
"""


def _render_ok_comment(
    cls: Classification, tier: str, label: str = LABEL_PASSED
) -> str:
    """Render the "gate satisfied" acknowledgement comment.

    ``label`` is the label that satisfied the gate. When a must-tier PR
    is satisfied by ``nightly-run-skipped`` (rather than
    ``nightly-run-passed``), we still let the check pass but the comment
    explicitly flags the trade-off so the author and reviewers can
    reconsider before merging.
    """
    # Structural-pattern-match on (tier, label) so each of the four
    # cells of the 2x2 render table (must/recommended x passed/skipped)
    # is one `case` that reads top-to-bottom in the source. Anything
    # other than `LABEL_SKIPPED` is treated as `LABEL_PASSED` per the
    # existing behavior (label defaults to `LABEL_PASSED` at the
    # signature).
    match tier, label:
        case "must", label_val if label_val == LABEL_SKIPPED:
            # "Skipped anyway" - do NOT fail, but push back explicitly.
            files_block = _render_file_list(cls.matched_must)
            header = "### ⚠️ SDK Nightly skipped for a required change"
            body = (
                f"This PR touches files that **require** a nightly run, "
                f"and the **`{LABEL_SKIPPED}`** label has been applied "
                f"to bypass the requirement. The check is passing so it "
                f"does not block merge, but **please reconsider**: the "
                f"changed files are on the nightly-required list because "
                f"regressions in them are historically hard to catch "
                f"without a full nightly run.\n\n"
                f"If a full nightly run is genuinely disproportionate, "
                f"the Content-build alternative below is usually enough "
                f"to satisfy reviewers - if it applies to your change, "
                f"switch the label to **`{LABEL_PASSED}`** after the "
                f"Content build is green.\n\n"
                f"{_CONTENT_BUILD_ALTERNATIVE}"
            )
        case "must", _:
            files_block = _render_file_list(cls.matched_must)
            header = "### ✅ SDK Nightly acknowledged (required)"
            body = (
                f"This PR touches files that **require** a nightly run. "
                f"The **`{LABEL_PASSED}`** label is present, so this "
                f"check is satisfied."
            )
        case _, label_val if label_val == LABEL_SKIPPED:
            files_block = _render_file_list(cls.matched_recommended)
            header = "### ✅ SDK Nightly acknowledged (recommended, skipped)"
            body = (
                f"This PR touches files where nightly is **recommended**. "
                f"The **`{LABEL_SKIPPED}`** label is present, so this "
                f"check is satisfied and no nightly run is expected."
            )
        case _:
            files_block = _render_file_list(cls.matched_recommended)
            header = "### ✅ SDK Nightly acknowledged (recommended)"
            body = (
                f"This PR touches files where nightly is **recommended**. "
                f"The **`{LABEL_PASSED}`** label is present, so this "
                f"check is satisfied."
            )

    return f"""{COMMENT_MARKER}
{header}

{body}

<details>
<summary>Files considered</summary>

{files_block}
</details>
"""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_config(path: Path) -> GateConfig:
    """Load and validate the gate configuration YAML."""
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError(
            f"Expected a YAML mapping at the top level of {path}, "
            f"got {type(raw).__name__}"
        )
    return GateConfig(
        must=list(raw.get("must") or []),
        must_exclude=list(raw.get("must_exclude") or []),
        recommended=list(raw.get("recommended") or []),
        skip=list(raw.get("skip") or []),
    )


def load_changed_files(path: Path) -> list[str]:
    """Load the list of changed files from a newline-delimited file."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_github_output(pairs: dict[str, str]) -> None:
    """Append key=value pairs to the ``GITHUB_OUTPUT`` file, if set.

    Multi-line values are written using the heredoc syntax GitHub
    Actions requires so that Markdown comment bodies survive intact.
    """
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        # Local invocation: just echo to stdout for debugging.
        for k, v in pairs.items():
            print(f"[github-output] {k}={v!r}")
        return

    with open(output_path, "a", encoding="utf-8") as fh:
        for key, value in pairs.items():
            if "\n" in value:
                # Heredoc form; use a delimiter that is extremely
                # unlikely to appear in the value.
                delim = f"NIGHTLY_GATE_EOF_{key.upper()}"
                fh.write(f"{key}<<{delim}\n{value}\n{delim}\n")
            else:
                fh.write(f"{key}={value}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_labels(labels_json: str, labels_csv: str) -> list[str]:
    """Return the effective label list, preferring the JSON form.

    ``labels_json`` is expected to be the raw output of
    ``toJSON(github.event.pull_request.labels.*.name)`` in a GitHub
    Actions workflow (a JSON array of strings). When non-empty it is
    used exclusively - this avoids the shell-level CSV munging that
    breaks on labels containing commas or whitespace.

    ``labels_csv`` is the legacy comma-separated fallback so existing
    CLI callers (and tests) keep working unchanged.
    """
    if labels_json.strip():
        try:
            parsed = json.loads(labels_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--labels-json is not valid JSON: {exc}") from exc
        if not isinstance(parsed, list) or not all(
            isinstance(item, str) for item in parsed
        ):
            raise SystemExit(
                "--labels-json must be a JSON array of strings, " f"got: {parsed!r}"
            )
        return [item.strip() for item in parsed if item.strip()]
    return [lbl.strip() for lbl in labels_csv.split(",") if lbl.strip()]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".github/nightly-gate-paths.yml"),
        help="Path to the gate configuration YAML.",
    )
    parser.add_argument(
        "--changed-files",
        type=Path,
        required=True,
        help="Path to a newline-delimited file of changed paths.",
    )
    parser.add_argument(
        "--labels",
        default="",
        help=(
            "Comma-separated list of labels currently on the PR. "
            "Empty string means no labels. Ignored if --labels-json is given."
        ),
    )
    parser.add_argument(
        "--labels-json",
        default="",
        help=(
            "JSON array of labels currently on the PR (e.g. the raw output "
            "of `toJSON(github.event.pull_request.labels.*.name)` in a "
            "GitHub Actions workflow). Preferred over --labels because it "
            "handles labels containing commas or whitespace correctly."
        ),
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print the classification+decision as JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    config = load_config(args.config)
    files = load_changed_files(args.changed_files)
    labels = _parse_labels(args.labels_json, args.labels)

    classification = classify(files, config)
    decision = decide(classification, labels)

    if args.print_json:
        print(
            json.dumps(
                {
                    "classification": asdict(classification),
                    "decision": {
                        "exit_code": decision.exit_code,
                        "status": decision.status,
                        "delete_comment": decision.delete_comment,
                    },
                },
                indent=2,
            )
        )

    _emit_log_summary(classification, decision, labels)
    _emit_step_summary(classification, decision, labels)

    write_github_output(
        {
            "tier": classification.tier,
            "status": decision.status,
            "delete_comment": "true" if decision.delete_comment else "false",
            "comment_body": decision.comment_body or "",
            "matched_must": "\n".join(classification.matched_must),
            "matched_recommended": "\n".join(classification.matched_recommended),
        }
    )

    return decision.exit_code


# ---------------------------------------------------------------------------
# Human-readable log output
# ---------------------------------------------------------------------------


def _emit_log_summary(
    classification: Classification,
    decision: Decision,
    labels: list[str],
) -> None:
    """Print a human-readable block into the workflow log.

    Uses GitHub Actions ``::group::`` / ``::error::`` / ``::notice::``
    workflow commands so the important information is visible in the
    log stream *and* pinned to the run's annotations panel.
    """
    labels_display = ", ".join(labels) if labels else "(none)"

    # A collapsible group makes the block scan-friendly in the log.
    print("::group::SDK Nightly Gate result", file=sys.stderr)
    print(f"Tier          : {classification.tier}", file=sys.stderr)
    print(f"Status        : {decision.status}", file=sys.stderr)
    print(f"PR labels     : {labels_display}", file=sys.stderr)
    print(
        f"Must hits     : {len(classification.matched_must)}",
        file=sys.stderr,
    )
    for f in classification.matched_must:
        print(f"  - {f}", file=sys.stderr)
    print(
        f"Recommended   : {len(classification.matched_recommended)}",
        file=sys.stderr,
    )
    for f in classification.matched_recommended:
        print(f"  - {f}", file=sys.stderr)
    print("::endgroup::", file=sys.stderr)

    if decision.status == "fail":
        # `::error::` pins a red annotation to the top of the run page
        # so the author sees it without scrolling.
        first_hit = (
            classification.matched_must[0]
            if classification.matched_must
            else "(unknown)"
        )
        n = len(classification.matched_must)
        others = f" (+{n - 1} more)" if n > 1 else ""
        msg = (
            f"SDK Nightly required: this PR changes '{first_hit}'"
            f"{others}, which is on the Must list. Run the SDK "
            f"Nightly pipeline against this branch and add the "
            f"'{LABEL_PASSED}' label (or '{LABEL_SKIPPED}' with "
            f"reviewer approval). See the PR comment posted by "
            f"'nightly-gate-bot' for the full list and instructions. "
            f"This check re-runs when a label is added or removed."
        )
        # `::error::` messages must be single-line.
        print(f"::error title=SDK Nightly Gate failed::{msg}", file=sys.stderr)
    elif decision.status == "warn":
        first_hit = (
            classification.matched_recommended[0]
            if classification.matched_recommended
            else "(unknown)"
        )
        n = len(classification.matched_recommended)
        others = f" (+{n - 1} more)" if n > 1 else ""
        msg = (
            f"SDK Nightly recommended: this PR changes '{first_hit}'"
            f"{others}, which is on the Recommended list. Please add "
            f"'{LABEL_PASSED}' (after running the nightly and pasting "
            f"the link in the PR description) or '{LABEL_SKIPPED}' if "
            f"you chose not to run it."
        )
        print(
            f"::warning title=SDK Nightly recommended::{msg}",
            file=sys.stderr,
        )
    else:
        print(
            f"::notice title=SDK Nightly Gate::status={decision.status} "
            f"tier={classification.tier}",
            file=sys.stderr,
        )


def _emit_step_summary(
    classification: Classification,
    decision: Decision,
    labels: list[str],
) -> None:
    """Write a Markdown summary to ``$GITHUB_STEP_SUMMARY``.

    This appears in a dedicated 'Summary' panel on the Actions run
    page - much more visible than log lines.
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines: list[str] = []
    if decision.status == "fail":
        lines.append("## 🚫 SDK Nightly Gate: FAILED\n")
        lines.append(
            "This PR modifies files that **require** the SDK Nightly "
            "pipeline to be run before it can be merged.\n"
        )
    elif decision.status == "warn":
        lines.append("## ⚠️ SDK Nightly Gate: recommended\n")
        lines.append(
            "This PR modifies files where the SDK Nightly pipeline "
            "is **recommended** but not required.\n"
        )
    elif decision.status == "ok":
        lines.append("## ✅ SDK Nightly Gate: acknowledged\n")
        lines.append(
            f"A `{LABEL_PASSED}` or `{LABEL_SKIPPED}` label is "
            "present; the gate is satisfied.\n"
        )
    else:  # noop
        lines.append("## ✅ SDK Nightly Gate: not applicable\n")
        lines.append("No gated files were changed in this PR.\n")

    lines.append(f"- **Tier:** `{classification.tier}`")
    lines.append(f"- **Status:** `{decision.status}`")
    lines.append(
        f"- **PR labels:** "
        f"{', '.join(f'`{label}`' for label in labels) if labels else '_(none)_'}"
    )

    if classification.matched_must:
        lines.append("\n### Must-tier files touched")
        for f in classification.matched_must:
            lines.append(f"- `{f}`")

    if classification.matched_recommended:
        lines.append("\n### Recommended-tier files touched")
        for f in classification.matched_recommended:
            lines.append(f"- `{f}`")

    if decision.status in ("fail", "warn"):
        lines.append("\n### What to do")
        lines.append("1. Run the **SDK Nightly** pipeline against this branch.")
        lines.append("2. Paste the link to the nightly run in the PR description.")
        lines.append(
            f"3. Add the **`{LABEL_PASSED}`** label once it passes "
            f"(or **`{LABEL_SKIPPED}`** if you have a documented "
            "reason not to run it, with reviewer approval)."
        )
        lines.append(
            "\n**Alternative:** for scoped changes (e.g. a single new "
            "validator), a **Content build against this SDK branch** is "
            "usually enough. New validators must be registered in the "
            "Content repo's `validation_config.toml` so the Content "
            "build's `run-validations` job exercises them via "
            "`demisto-sdk validate -a`."
        )
        lines.append(
            "\n_This check re-runs automatically when a label is "
            "added or removed - no push required._"
        )

    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
