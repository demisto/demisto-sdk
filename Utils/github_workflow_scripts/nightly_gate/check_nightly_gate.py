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
"""

from __future__ import annotations

import argparse
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
#: (only meaningful for the `recommended` tier).
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
    """Path globs for each tier, as loaded from the YAML config."""

    must: list[str] = field(default_factory=list)
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


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a gitignore-style glob into a compiled regex.

    Supports:

    * ``**`` — matches any number of characters including path
      separators (recursive descent). When it appears as a whole path
      segment (e.g. ``a/**/b``), the surrounding ``/`` is consumed so
      that ``a/b`` also matches.
    * ``*``  — matches any character except ``/`` (single path segment).
    * ``?``  — matches a single character except ``/``.
    * All other regex metacharacters are escaped.

    The returned regex is anchored (``^...$``) and case-sensitive, to
    match POSIX file semantics used by git on Linux CI runners.
    """
    # Special-case bare `**` -> match anything (including empty).
    if pattern == "**":
        return re.compile(r"^.*$")

    # We tokenize by walking the string so we can handle `**` before `*`.
    i = 0
    out: list[str] = ["^"]
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            # Look ahead for `**`.
            if i + 1 < n and pattern[i + 1] == "*":
                # `**` -> match anything (including `/`). If the pattern
                # is `a/**/b`, we want `a/b` to match too, so we consume
                # the trailing `/` if we're at the start of a segment.
                # Consume an immediately-preceding "/" that we just wrote
                # and an immediately-following "/", collapsing to `(?:.*/)?`.
                trailing_slash = i + 2 < n and pattern[i + 2] == "/"
                preceding_slash = out and out[-1] == "/"
                if preceding_slash and trailing_slash:
                    # Rewrite "a/**/b" -> "a(?:/.*)?/b" so both "a/b"
                    # and "a/x/y/b" match.
                    out.pop()  # drop the "/"
                    out.append(r"(?:/.*)?/")
                    i += 3  # skip **/
                elif trailing_slash:
                    # "**/foo" at start -> optional prefix.
                    out.append(r"(?:.*/)?")
                    i += 3
                else:
                    # Bare `**` at end or in middle without trailing "/".
                    out.append(r".*")
                    i += 2
            else:
                # Single `*` -> match anything except `/`.
                out.append(r"[^/]*")
                i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return re.compile("".join(out))


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

    Precedence (per file):
        skip > must > recommended > none

    Overall tier is the highest hit across all non-skipped files:
        * ``must``        - at least one file matches a Must glob.
        * ``recommended`` - no Must hits, at least one Recommended hit.
        * ``skip_only``   - every changed file matched a Skip glob.
        * ``none``        - files were considered but nothing matched
                            (no gate applies).
    """
    skip_rx = _compile_patterns(config.skip)
    must_rx = _compile_patterns(config.must)
    rec_rx = _compile_patterns(config.recommended)

    result = Classification(tier="none")

    for raw in files:
        path = raw.strip()
        if not path:
            continue

        if _matches_any(path, skip_rx):
            result.matched_skip.append(path)
            continue

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


@dataclass
class Decision:
    """Final decision for the workflow step."""

    exit_code: int
    status: str  # "ok" | "warn" | "fail" | "noop"
    comment_body: str | None
    delete_comment: bool = False


def decide(classification: Classification, labels: Iterable[str]) -> Decision:
    """Given a classification and the PR's labels, decide the outcome.

    Rules:
        * tier == 'must' + label present  -> ok (post ack comment)
        * tier == 'must' + no label       -> fail (post required-action comment)
        * tier == 'recommended' + label   -> ok (post ack comment)
        * tier == 'recommended' + no lbl  -> warn (post reminder comment)
        * tier in {'none', 'skip_only'}   -> noop (delete any existing comment)
    """
    label_set = {lbl.lower() for lbl in labels}
    has_label = LABEL_PASSED in label_set or LABEL_SKIPPED in label_set

    if classification.tier == "must":
        if has_label:
            return Decision(
                exit_code=0,
                status="ok",
                comment_body=_render_ok_comment(classification, tier="must"),
            )
        return Decision(
            exit_code=1,
            status="fail",
            comment_body=_render_fail_comment(classification),
        )

    if classification.tier == "recommended":
        if has_label:
            return Decision(
                exit_code=0,
                status="ok",
                comment_body=_render_ok_comment(classification, tier="recommended"),
            )
        return Decision(
            exit_code=0,
            status="warn",
            comment_body=_render_warn_comment(classification),
        )

    # tier == 'none' or 'skip_only': nothing to enforce; remove any
    # stale comment from previous runs.
    return Decision(exit_code=0, status="noop", comment_body=None, delete_comment=True)


# ---------------------------------------------------------------------------
# Comment rendering
# ---------------------------------------------------------------------------


def _render_file_list(files: list[str], limit: int = 25) -> str:
    """Render a bulleted list of files, truncating if very long."""
    shown = files[:limit]
    lines = [f"- `{f}`" for f in shown]
    if len(files) > limit:
        lines.append(f"- _(and {len(files) - limit} more)_")
    return "\n".join(lines)


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

This check is non-blocking, but reviewers may request one of the \
labels before merging. It will re-evaluate automatically when a \
label is added or removed.
"""


def _render_ok_comment(cls: Classification, tier: str) -> str:
    if tier == "must":
        header = "### ✅ SDK Nightly acknowledged (required)"
        files_block = _render_file_list(cls.matched_must)
        tier_note = "This PR touches files that **require** a nightly run."
    else:
        header = "### ✅ SDK Nightly acknowledged (recommended)"
        files_block = _render_file_list(cls.matched_recommended)
        tier_note = "This PR touches files where nightly is **recommended**."

    return f"""{COMMENT_MARKER}
{header}

{tier_note} A `{LABEL_PASSED}` or `{LABEL_SKIPPED}` label is present, \
so this check is satisfied.

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
        recommended=list(raw.get("recommended") or []),
        skip=list(raw.get("skip") or []),
    )


def load_changed_files(path: Path) -> list[str]:
    """Load the list of changed files from a newline-delimited file."""
    with path.open("r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


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
            "Empty string means no labels."
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
    labels = [lbl.strip() for lbl in args.labels.split(",") if lbl.strip()]

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
            "\n_This check re-runs automatically when a label is "
            "added or removed - no push required._"
        )

    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
