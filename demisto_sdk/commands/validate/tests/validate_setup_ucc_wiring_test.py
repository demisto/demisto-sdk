"""
Tests that the ``validate -a`` command correctly wires the new
``--connectors-content-path`` / ``-ccp`` flag into a
:class:`UnifiedConnectorContentManager` (alongside the existing
``--private-content-path`` handling), using ``contextlib.ExitStack``.

These are targeted *wiring* tests: they call ``validate_setup.validate``
directly (bypassing the Typer CLI parser) with all options pre-populated,
and mock the heavy collaborators. This lets us assert precisely:

- when only ``connectors_content_path`` is set, ``UnifiedConnectorContentManager``
  is entered and exited exactly once, and ``PrivateContentManager`` is
  never constructed;
- when only ``private_content_path`` is set, the reverse is true;
- when both are set, both managers are entered *and* exited in LIFO order;
- when neither is set, no manager is used at all.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.validate import validate_setup

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_ucc(tmp_path: Path) -> Path:
    """A fake UCC repo with a single connector so the flag's ``exists`` check
    passes."""
    ucc = tmp_path / "ucc"
    (ucc / "connectors" / "datadog").mkdir(parents=True)
    (ucc / "connectors" / "datadog" / "connector.yaml").write_text("name: datadog\n")
    return ucc


@pytest.fixture
def fake_content_private(tmp_path: Path) -> Path:
    """A fake content-private repo with an empty Packs/ dir."""
    priv = tmp_path / "content-private"
    (priv / "Packs").mkdir(parents=True)
    return priv


@pytest.fixture
def wire_mocks(mocker):
    """
    Common mock scaffolding: prevent the real validate flow from doing anything
    heavy, and expose recording MagicMocks for the two managers so tests can
    inspect enter/exit ordering.
    """
    mocker.patch.object(
        validate_setup, "is_sdk_defined_working_offline", return_value=False
    )
    mocker.patch.object(validate_setup, "is_external_repository", return_value=False)
    mocker.patch.object(validate_setup, "validate_paths", return_value=None)
    mocker.patch.object(
        validate_setup, "update_command_args_from_config_file", return_value=None
    )
    mocker.patch.object(
        validate_setup,
        "determine_execution_mode",
        return_value=ExecutionMode.ALL_FILES,
    )
    mocker.patch.object(validate_setup, "warn_on_ignored_flags", return_value=None)
    mocker.patch.object(validate_setup, "run_new_validation", return_value=0)
    mocker.patch.object(validate_setup, "run_old_validation", return_value=0)

    # Record enter/exit call order across both managers on a shared list so
    # LIFO assertions are trivial.
    call_log: list[str] = []

    def make_mock_manager(label: str) -> MagicMock:
        m = MagicMock(name=f"{label}Instance")

        def _enter(*_args, **_kwargs):
            call_log.append(f"{label}.enter")
            return m

        def _exit(*_args, **_kwargs):
            call_log.append(f"{label}.exit")
            return False

        m.__enter__ = MagicMock(side_effect=_enter)
        m.__exit__ = MagicMock(side_effect=_exit)
        return m

    priv_instance = make_mock_manager("Priv")
    ucc_instance = make_mock_manager("UCC")

    priv_cls = mocker.patch.object(
        validate_setup, "PrivateContentManager", return_value=priv_instance
    )
    ucc_cls = mocker.patch.object(
        validate_setup,
        "UnifiedConnectorContentManager",
        return_value=ucc_instance,
    )

    return {
        "call_log": call_log,
        "priv_cls": priv_cls,
        "priv_instance": priv_instance,
        "ucc_cls": ucc_cls,
        "ucc_instance": ucc_instance,
    }


def _default_validate_kwargs() -> dict:
    """
    Return the full ``validate()`` kwargs dict with sane defaults matching the
    typer option defaults. Overriding fields per test is straightforward.

    We use ``dict`` (not typer.Options) because we're calling the function
    directly, so we need the resolved default *values*, not the ``OptionInfo``
    sentinels typer produces at parse time.
    """
    return {
        "file_paths": None,
        "no_conf_json": False,
        "id_set": False,
        "id_set_path": None,
        "graph": False,
        "prev_ver": None,
        "no_backward_comp": False,
        "use_git": False,
        "post_commit": False,
        "staged": False,
        "include_untracked": False,
        "validate_all": True,  # -a
        "input": None,
        "skip_pack_release_notes": False,
        "print_ignored_errors": False,
        "print_ignored_files": False,
        "no_docker_checks": False,
        "silence_init_prints": False,
        "skip_pack_dependencies": False,
        "create_id_set": False,
        "json_file": None,
        "skip_schema_check": False,
        "debug_git": False,
        "print_pykwalify": False,
        "quiet_bc_validation": False,
        "allow_skipped": False,
        "no_multiprocessing": False,
        "run_specific_validations": None,
        "allow_ignore_all_errors": False,
        "category_to_run": None,
        "handling_private_repositories": False,
        "fix": False,
        "config_path": None,
        "private_content_path": None,
        "connectors_content_path": None,
        "ignore_support_level": False,
        "run_old_validate": False,
        "skip_new_validate": False,
        "run_connectors_validation": False,
        "create_graph_from_scratch": False,
        "ignore": None,
        "console_log_threshold": None,
        "file_log_threshold": None,
        "log_file_path": None,
    }


def _make_ctx(kwargs: dict) -> MagicMock:
    """
    Fabricate a minimal ``typer.Context`` shim that ``validate()`` reads:
    - ``ctx.params`` returns the kwargs dict (used at lines that consult flags).
    - ``ctx.obj.configuration.env_dir`` returns a string path so the
      ``sys.path.append`` call doesn't blow up.
    """
    ctx = MagicMock(spec=typer.Context)
    ctx.params = kwargs
    fake_sdk = MagicMock(name="FakeSDK")
    fake_sdk.configuration.env_dir = "/tmp/nonexistent-sdk-env-dir"
    ctx.obj = fake_sdk
    return ctx


def _invoke_validate(kwargs: dict) -> int:
    """
    Call the (undecorated) ``validate`` function directly and translate the
    ``typer.Exit`` it raises into an exit code.

    ``validate_setup.validate`` is wrapped by ``@logging_setup_decorator``.
    ``functools.wraps`` means the wrapper preserves ``__wrapped__`` giving us
    access to the raw function.
    """
    func = getattr(validate_setup.validate, "__wrapped__", validate_setup.validate)
    ctx = _make_ctx(kwargs)
    try:
        func(ctx, **kwargs)
    except typer.Exit as e:
        return e.exit_code
    return 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateAllWithConnectorsContentPath:
    def test_only_ccp_uses_only_ucc_manager(
        self,
        wire_mocks,
        fake_ucc: Path,
    ) -> None:
        """
        Given: ``validate_all=True`` and ``connectors_content_path=<ucc>``
               (no ``private_content_path``).
        Then:  UnifiedConnectorContentManager is constructed and its context
               entered/exited exactly once. PrivateContentManager is NOT
               constructed.
        """
        kwargs = _default_validate_kwargs()
        kwargs["connectors_content_path"] = fake_ucc

        exit_code = _invoke_validate(kwargs)
        assert exit_code == 0

        wire_mocks["ucc_cls"].assert_called_once()
        ucc_kwargs = wire_mocks["ucc_cls"].call_args.kwargs
        assert ucc_kwargs["connectors_content_path"] == fake_ucc

        wire_mocks["priv_cls"].assert_not_called()

        assert wire_mocks["call_log"] == ["UCC.enter", "UCC.exit"]

    def test_only_private_uses_only_private_manager(
        self,
        wire_mocks,
        fake_content_private: Path,
    ) -> None:
        """
        Given: only ``private_content_path`` is set.
        Then:  Only PrivateContentManager is used.
        """
        kwargs = _default_validate_kwargs()
        kwargs["private_content_path"] = fake_content_private

        exit_code = _invoke_validate(kwargs)
        assert exit_code == 0

        wire_mocks["priv_cls"].assert_called_once()
        priv_kwargs = wire_mocks["priv_cls"].call_args.kwargs
        assert priv_kwargs["private_content_path"] == fake_content_private

        wire_mocks["ucc_cls"].assert_not_called()
        assert wire_mocks["call_log"] == ["Priv.enter", "Priv.exit"]

    def test_both_flags_nest_managers_in_lifo_order(
        self,
        wire_mocks,
        fake_ucc: Path,
        fake_content_private: Path,
    ) -> None:
        """
        Given: both ``private_content_path`` and ``connectors_content_path``.
        Then:  Both managers are entered (priv first, ucc second) and exited
               in LIFO order (ucc first, priv second).
        """
        kwargs = _default_validate_kwargs()
        kwargs["private_content_path"] = fake_content_private
        kwargs["connectors_content_path"] = fake_ucc

        exit_code = _invoke_validate(kwargs)
        assert exit_code == 0

        wire_mocks["priv_cls"].assert_called_once()
        wire_mocks["ucc_cls"].assert_called_once()
        assert wire_mocks["call_log"] == [
            "Priv.enter",
            "UCC.enter",
            "UCC.exit",
            "Priv.exit",
        ]

    def test_no_flags_uses_no_manager(self, wire_mocks) -> None:
        """
        Given: ``validate_all=True`` with neither external-repo flag.
        Then:  Neither manager is instantiated (regression guard).
        """
        kwargs = _default_validate_kwargs()
        exit_code = _invoke_validate(kwargs)
        assert exit_code == 0

        wire_mocks["priv_cls"].assert_not_called()
        wire_mocks["ucc_cls"].assert_not_called()
        assert wire_mocks["call_log"] == []

    def test_ccp_used_in_use_git_mode(
        self,
        mocker,
        wire_mocks,
        fake_ucc: Path,
    ) -> None:
        """
        Given: ``connectors_content_path`` is set and execution mode is
               ``USE_GIT`` (``-g``, not ``-a``).
        Then:  The UCC manager IS constructed and entered/exited once, so that
               the UCC repo can be git-diffed (mirroring the existing
               content-private ``-g`` support). PrivateContentManager is NOT
               constructed.
        """
        # Override the execution-mode fixture default.
        mocker.patch.object(
            validate_setup,
            "determine_execution_mode",
            return_value=ExecutionMode.USE_GIT,
        )

        kwargs = _default_validate_kwargs()
        kwargs["validate_all"] = False
        kwargs["use_git"] = True
        kwargs["connectors_content_path"] = fake_ucc

        exit_code = _invoke_validate(kwargs)
        assert exit_code == 0

        wire_mocks["ucc_cls"].assert_called_once()
        ucc_kwargs = wire_mocks["ucc_cls"].call_args.kwargs
        assert ucc_kwargs["connectors_content_path"] == fake_ucc

        wire_mocks["priv_cls"].assert_not_called()
        assert wire_mocks["call_log"] == ["UCC.enter", "UCC.exit"]
