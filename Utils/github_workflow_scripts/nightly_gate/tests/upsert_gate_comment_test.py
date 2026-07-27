"""
Unit tests for ``upsert_gate_comment.py``.

The tests use a fake ``opener`` (the injection seam accepted by every
HTTP helper) so no real network calls are made. Each assertion targets
one branch of the behavior contract documented in the module docstring:

* delete-all when ``--delete`` is passed
* delete-noop when ``--delete`` is passed but no marker comment exists
* skip when the body is empty and delete is False
* update-oldest + dedupe-rest when marker comments already exist
* create-new when no marker comment exists yet
* pagination via the ``Link: rel="next"`` header
"""

from __future__ import annotations

import io
import json
from typing import Any, Callable

import pytest

from Utils.github_workflow_scripts.nightly_gate.check_nightly_gate import (
    COMMENT_MARKER,
)
from Utils.github_workflow_scripts.nightly_gate.upsert_gate_comment import (
    GitHubHTTPError,
    _next_link,
    upsert_sticky_comment,
)

API = "https://api.github.com"
REPO = "demisto/demisto-sdk"
PR = 1234
TOKEN = "fake-token"


# ---------------------------------------------------------------------------
# Fake HTTP layer
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for the object ``urlopen`` returns."""

    def __init__(
        self,
        status: int,
        body: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._body = body.encode("utf-8")
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _FakeOpener:
    """Records every request and returns queued responses.

    Each element of ``responses`` is either a ``_FakeResponse`` or a
    callable ``(request) -> _FakeResponse`` for dynamic behavior.
    Calls beyond the queue length raise :class:`AssertionError` so
    accidental extra API calls surface as test failures.
    """

    def __init__(
        self,
        responses: list[_FakeResponse | Callable[[Any], _FakeResponse]],
    ) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(self, request: Any) -> _FakeResponse:
        method = request.get_method()
        url = request.full_url
        payload: dict[str, Any] | None = None
        if request.data is not None:
            payload = json.loads(request.data.decode("utf-8"))
        self.calls.append((method, url, payload))

        if not self._responses:
            raise AssertionError(
                f"Unexpected extra HTTP call: {method} {url} payload={payload!r}"
            )
        nxt = self._responses.pop(0)
        return nxt(request) if callable(nxt) else nxt


def _comment(comment_id: int, body: str) -> dict[str, Any]:
    return {"id": comment_id, "body": body}


def _list_response(
    comments: list[dict[str, Any]],
    next_url: str | None = None,
) -> _FakeResponse:
    headers = {}
    if next_url:
        headers["Link"] = f'<{next_url}>; rel="next"'
    return _FakeResponse(200, json.dumps(comments), headers)


# ---------------------------------------------------------------------------
# Branch: create-new
# ---------------------------------------------------------------------------


class TestCreateBranch:
    def test_creates_new_comment_when_none_exist(self) -> None:
        opener = _FakeOpener(
            [
                _list_response([_comment(11, "unrelated")]),
                _FakeResponse(201, "{}"),
            ]
        )
        logs: list[str] = []
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="hello world",
            delete=False,
            opener=opener,
            log=logs.append,
        )

        assert len(opener.calls) == 2
        get_call, post_call = opener.calls
        assert get_call[0] == "GET"
        assert get_call[1].startswith(f"{API}/repos/{REPO}/issues/{PR}/comments")
        assert post_call == (
            "POST",
            f"{API}/repos/{REPO}/issues/{PR}/comments",
            {"body": "hello world"},
        )
        assert any("Creating new gate comment" in line for line in logs)


# ---------------------------------------------------------------------------
# Branch: update-oldest + dedupe-rest
# ---------------------------------------------------------------------------


class TestUpdateBranch:
    def test_updates_oldest_and_deletes_duplicates(self) -> None:
        # Two existing marker comments (dupe scenario) + one unrelated.
        comments = [
            _comment(101, "unrelated body"),
            _comment(202, f"first marker {COMMENT_MARKER} body"),
            _comment(303, f"second marker {COMMENT_MARKER} body"),
        ]
        opener = _FakeOpener(
            [
                _list_response(comments),
                _FakeResponse(200, "{}"),  # PATCH
                _FakeResponse(204, ""),  # DELETE of the dup
            ]
        )
        logs: list[str] = []
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="fresh body",
            delete=False,
            opener=opener,
            log=logs.append,
        )

        assert len(opener.calls) == 3
        _, patch_call, delete_call = opener.calls
        assert patch_call == (
            "PATCH",
            f"{API}/repos/{REPO}/issues/comments/202",
            {"body": "fresh body"},
        )
        assert delete_call == (
            "DELETE",
            f"{API}/repos/{REPO}/issues/comments/303",
            None,
        )
        assert any("Updating existing gate comment 202" in line for line in logs)
        assert any("Deduplicating" in line for line in logs)

    def test_single_existing_comment_is_updated_without_deletes(self) -> None:
        opener = _FakeOpener(
            [
                _list_response([_comment(42, f"{COMMENT_MARKER} old body")]),
                _FakeResponse(200, "{}"),  # PATCH only
            ]
        )
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="new body",
            delete=False,
            opener=opener,
        )
        methods = [call[0] for call in opener.calls]
        assert methods == ["GET", "PATCH"]


# ---------------------------------------------------------------------------
# Branch: delete-all
# ---------------------------------------------------------------------------


class TestDeleteBranch:
    def test_delete_removes_every_marker_comment(self) -> None:
        comments = [
            _comment(1, f"{COMMENT_MARKER} a"),
            _comment(2, "unrelated"),
            _comment(3, f"{COMMENT_MARKER} b"),
        ]
        opener = _FakeOpener(
            [
                _list_response(comments),
                _FakeResponse(204, ""),  # delete #1
                _FakeResponse(204, ""),  # delete #3
            ]
        )
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="",
            delete=True,
            opener=opener,
        )
        methods_and_urls = [(c[0], c[1]) for c in opener.calls]
        assert methods_and_urls == [
            ("GET", f"{API}/repos/{REPO}/issues/{PR}/comments?per_page=100"),
            ("DELETE", f"{API}/repos/{REPO}/issues/comments/1"),
            ("DELETE", f"{API}/repos/{REPO}/issues/comments/3"),
        ]

    def test_delete_is_noop_when_no_marker_comments(self) -> None:
        opener = _FakeOpener(
            [
                _list_response([_comment(1, "unrelated")]),
            ]
        )
        logs: list[str] = []
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="",
            delete=True,
            opener=opener,
            log=logs.append,
        )
        assert [c[0] for c in opener.calls] == ["GET"]
        assert any("nothing to do" in line for line in logs)


# ---------------------------------------------------------------------------
# Branch: empty-body skip
# ---------------------------------------------------------------------------


class TestSkipBranch:
    def test_empty_body_without_delete_only_lists_and_returns(self) -> None:
        opener = _FakeOpener(
            [
                _list_response([_comment(9, f"{COMMENT_MARKER} still here")]),
            ]
        )
        logs: list[str] = []
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="",
            delete=False,
            opener=opener,
            log=logs.append,
        )
        # Only the GET happened - no PATCH/POST/DELETE.
        assert [c[0] for c in opener.calls] == ["GET"]
        assert any("skipping" in line for line in logs)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    def test_link_header_is_followed(self) -> None:
        page2 = f"{API}/repos/{REPO}/issues/{PR}/comments?per_page=100&page=2"
        opener = _FakeOpener(
            [
                _list_response([_comment(1, "unrelated")], next_url=page2),
                _list_response([_comment(2, f"{COMMENT_MARKER} on page 2")]),
                _FakeResponse(200, "{}"),  # PATCH on the found comment
            ]
        )
        upsert_sticky_comment(
            api_base=API,
            repo=REPO,
            pr_number=PR,
            token=TOKEN,
            body="body",
            delete=False,
            opener=opener,
        )
        assert [c[0] for c in opener.calls] == ["GET", "GET", "PATCH"]
        # Second GET must have used the URL from the Link header.
        assert opener.calls[1][1] == page2


class TestNextLink:
    def test_parses_next_link(self) -> None:
        header = (
            '<https://api.example/x?page=2>; rel="next", '
            '<https://api.example/x?page=5>; rel="last"'
        )
        assert _next_link(header) == "https://api.example/x?page=2"

    def test_returns_none_when_no_next(self) -> None:
        assert _next_link('<https://api.example/x?page=5>; rel="last"') is None

    def test_returns_none_for_empty_header(self) -> None:
        assert _next_link("") is None


# ---------------------------------------------------------------------------
# HTTP error surfacing
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_http_error_from_urlopen_is_converted(self) -> None:
        import urllib.error

        def _raise(_request: Any) -> _FakeResponse:
            raise urllib.error.HTTPError(
                url=f"{API}/repos/{REPO}/issues/{PR}/comments",
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=io.BytesIO(b'{"message":"nope"}'),
            )

        opener = _FakeOpener([_raise])
        with pytest.raises(GitHubHTTPError) as excinfo:
            upsert_sticky_comment(
                api_base=API,
                repo=REPO,
                pr_number=PR,
                token=TOKEN,
                body="anything",
                delete=False,
                opener=opener,
            )
        assert excinfo.value.status == 403
        assert "nope" in excinfo.value.body
