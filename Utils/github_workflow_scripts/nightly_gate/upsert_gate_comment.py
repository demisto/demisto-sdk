"""
Upsert (create / update / dedupe / delete) the SDK Nightly Gate sticky
comment on a pull request.

This script replaces a ~70-line ``run: |`` bash block in
``.github/workflows/nightly-gate.yml`` that used ``gh api`` + ``jq`` +
``mapfile`` to talk to the GitHub REST API. Reasons to prefer Python:

* Every branch is now unit-testable with mocked HTTP.
* No dependency on the ``gh`` CLI being installed on the runner (only
  the standard library and a ``GITHUB_TOKEN`` env var).
* Shell-quoting and multiline-body handling stop being footguns.

Behavior contract (identical to the previous shell version):

1. Load the "sticky" marker (``COMMENT_MARKER``) from
   :mod:`check_nightly_gate` so both scripts stay in lock-step.
2. List every issue comment on the PR and keep the ones whose body
   contains the marker. Order = creation order (oldest first), which
   is the order the GitHub API already returns.
3. If ``--delete`` is passed: delete every marker comment (no-op if
   there are none) and exit 0.
4. Else if ``--body`` is empty: exit 0 without touching the PR.
5. Else:

   * If there is at least one existing marker comment: PATCH the
     **oldest** one in-place (stable URL) and DELETE every extra
     duplicate to enforce the "exactly one gate comment" invariant.
   * Otherwise: POST a fresh comment.

Environment variables (all required unless noted):

    GITHUB_TOKEN        - PAT / GITHUB_TOKEN with `pull-requests: write`.
    GITHUB_REPOSITORY   - ``owner/repo`` slug (auto-set by GitHub Actions).
    PR_NUMBER           - Numeric PR number.
    GITHUB_API_URL      - Base URL (auto-set on Actions; defaults to
                          ``https://api.github.com`` for local runs).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Iterable

from Utils.github_workflow_scripts.nightly_gate.check_nightly_gate import (
    COMMENT_MARKER,
)

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

#: Media type recommended by GitHub for REST v3.
_GITHUB_ACCEPT = "application/vnd.github+json"

#: API version pin, per GitHub's best-practice guidance.
_GITHUB_API_VERSION = "2022-11-28"


class GitHubHTTPError(RuntimeError):
    """Raised when the GitHub API returns a non-2xx response."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(
            f"GitHub API {method} {url} failed with HTTP {status}: {body}"
        )
        self.method = method
        self.url = url
        self.status = status
        self.body = body


def _github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> tuple[int, str, dict[str, str]]:
    """Perform a single HTTP call against the GitHub REST API.

    Returns a ``(status, body_text, headers)`` triple. Raises
    :class:`GitHubHTTPError` on any non-2xx response.

    ``opener`` is an injection seam for unit tests. In production it
    defaults to :func:`urllib.request.urlopen`.
    """
    data: bytes | None = None
    headers = {
        "Accept": _GITHUB_ACCEPT,
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        "User-Agent": "demisto-sdk-nightly-gate",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(  # noqa: S310 (URL is a constant API host)
        url, data=data, headers=headers, method=method
    )
    do_open = opener or urllib.request.urlopen
    try:
        with do_open(request) as response:
            body = response.read().decode("utf-8", errors="replace")
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            return response.status, body, resp_headers
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise GitHubHTTPError(method, url, exc.code, err_body) from exc


def _paginate_comments(
    api_base: str,
    repo: str,
    pr_number: int,
    token: str,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> Iterable[dict[str, Any]]:
    """Yield every issue comment on the PR, following ``Link: rel=next``.

    GitHub returns issue comments in creation order (oldest first),
    which is exactly what the "keep the oldest, dedupe the rest"
    invariant needs, so we do not re-sort.
    """
    url: str | None = (
        f"{api_base}/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    )
    while url:
        status, body, headers = _github_request("GET", url, token, opener=opener)
        if status != 200:
            raise GitHubHTTPError("GET", url, status, body)
        for comment in json.loads(body):
            yield comment
        url = _next_link(headers.get("link", ""))


def _next_link(link_header: str) -> str | None:
    """Parse the ``Link`` header and return the URL for ``rel="next"``."""
    if not link_header:
        return None
    for part in link_header.split(","):
        segments = [seg.strip() for seg in part.split(";")]
        if len(segments) < 2:
            continue
        url_seg, *params = segments
        if not (url_seg.startswith("<") and url_seg.endswith(">")):
            continue
        for param in params:
            if param == 'rel="next"':
                return url_seg[1:-1]
    return None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _find_marker_comment_ids(
    api_base: str,
    repo: str,
    pr_number: int,
    token: str,
    marker: str,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> list[int]:
    """Return the IDs of every PR comment whose body contains ``marker``.

    Order is oldest -> newest (as returned by GitHub), so callers can
    keep ``ids[0]`` and delete the rest to enforce the "exactly one
    sticky comment" invariant.
    """
    return [
        int(comment["id"])
        for comment in _paginate_comments(
            api_base, repo, pr_number, token, opener=opener
        )
        if marker in (comment.get("body") or "")
    ]


def _delete_comment(
    api_base: str,
    repo: str,
    comment_id: int,
    token: str,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> None:
    url = f"{api_base}/repos/{repo}/issues/comments/{comment_id}"
    _github_request("DELETE", url, token, opener=opener)


def _update_comment(
    api_base: str,
    repo: str,
    comment_id: int,
    body: str,
    token: str,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> None:
    url = f"{api_base}/repos/{repo}/issues/comments/{comment_id}"
    _github_request("PATCH", url, token, payload={"body": body}, opener=opener)


def _create_comment(
    api_base: str,
    repo: str,
    pr_number: int,
    body: str,
    token: str,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> None:
    url = f"{api_base}/repos/{repo}/issues/{pr_number}/comments"
    _github_request("POST", url, token, payload={"body": body}, opener=opener)


def upsert_sticky_comment(
    *,
    api_base: str,
    repo: str,
    pr_number: int,
    token: str,
    body: str,
    delete: bool,
    marker: str = COMMENT_MARKER,
    opener: Callable[[urllib.request.Request], Any] | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """Public entry point. Encapsulates every branch of the shell script
    it replaces.

    See the module docstring for the behavior contract.
    """
    existing_ids = _find_marker_comment_ids(
        api_base, repo, pr_number, token, marker, opener=opener
    )
    log(
        f"Found {len(existing_ids)} existing gate comment(s) "
        f"on PR #{pr_number}."
    )

    if delete:
        # Files no longer touch any gated path (e.g. author reverted the
        # change). Clean up EVERY stale gate comment so the PR is left
        # with none.
        if not existing_ids:
            log("No gated files and no existing comment - nothing to do.")
            return
        for comment_id in existing_ids:
            log(f"Deleting gate comment {comment_id}")
            _delete_comment(api_base, repo, comment_id, token, opener=opener)
        return

    if not body:
        log("No comment body produced by classifier; skipping.")
        return

    if existing_ids:
        # Keep the OLDEST comment (first in the list) so its URL is
        # stable across runs, edit it in place, and delete every extra
        # duplicate. This enforces "exactly one gate comment".
        keep_id = existing_ids[0]
        log(f"Updating existing gate comment {keep_id}")
        _update_comment(api_base, repo, keep_id, body, token, opener=opener)
        duplicates = existing_ids[1:]
        if duplicates:
            log(
                f"Deduplicating: removing {len(duplicates)} stale "
                "duplicate comment(s)."
            )
            for comment_id in duplicates:
                log(f"Deleting gate comment {comment_id}")
                _delete_comment(
                    api_base, repo, comment_id, token, opener=opener
                )
        return

    log("Creating new gate comment")
    _create_comment(api_base, repo, pr_number, body, token, opener=opener)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body",
        default=None,
        help=(
            "Markdown body for the sticky comment. Overrides the "
            "COMMENT_BODY environment variable when given. If both are "
            "empty AND --delete/DELETE_COMMENT is not set, the script "
            "exits 0 without touching the PR."
        ),
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help=(
            "Delete every existing gate comment on the PR (used when the "
            "classifier decides the PR no longer touches gated paths). "
            "Also enabled when the DELETE_COMMENT env var is 'true'."
        ),
    )
    return parser.parse_args(argv)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Environment variable {name!r} is required.")
    return value


def _env_flag(name: str) -> bool:
    """Interpret a workflow-supplied string env var as a boolean."""
    return os.environ.get(name, "").strip().lower() == "true"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    token = _require_env("GITHUB_TOKEN")
    repo = _require_env("GITHUB_REPOSITORY")
    pr_number_str = _require_env("PR_NUMBER")
    try:
        pr_number = int(pr_number_str)
    except ValueError as exc:
        raise SystemExit(
            f"PR_NUMBER must be an integer, got: {pr_number_str!r}"
        ) from exc

    api_base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip(
        "/"
    )

    # Environment variables are the primary transport from the workflow
    # (multi-line-safe, no shell-quoting risk). CLI flags override for
    # local debugging.
    body = args.body if args.body is not None else os.environ.get(
        "COMMENT_BODY", ""
    )
    delete = args.delete or _env_flag("DELETE_COMMENT")

    upsert_sticky_comment(
        api_base=api_base,
        repo=repo,
        pr_number=pr_number,
        token=token,
        body=body,
        delete=delete,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
