from pathlib import Path

from demisto_sdk.commands.xsoar_linter import xsoar_linter
from demisto_sdk.commands.xsoar_linter.xsoar_linter import (
    ProcessResults,
    process_file,
    xsoar_linter_manager,
)


def test_process_file(graph_repo):
    """
    Given:
        An integration whose code has a print (error E9002).

    When:
        Calling process_file.

    Then:
        Assert the error is caught in the hook line format, and the return code is 1.
    """
    pack = graph_repo.create_pack("pack")
    integration = pack.create_integration(
        "integration", code='def main():\n    print("x")\n'
    )
    res = process_file(Path(integration.path))
    print_errors = [
        error
        for error in res.errors
        if error.endswith(
            ":2:4: E9002 main: Print is found, Please remove all prints from the code."
        )
    ]
    assert res.return_code == 1
    assert len(print_errors) == 1
    assert print_errors[0] in res.errors_and_warnings.splitlines()
    assert res.skipped_file == ""


def test_process_file_skip_parse_file(graph_repo):
    """
    Given:
        An integration whose code starts with `# xsoar-lint: skip-parse-file` and cannot be parsed.

    When:
        Calling process_file.

    Then:
        Assert there are no errors, the return code is 0, and the skipped file path is recorded.
    """
    pack = graph_repo.create_pack("pack")
    integration = pack.create_integration(
        "integration",
        code="# xsoar-lint: skip-parse-file\ndef broken(:\n    pass\n",
    )
    res = process_file(Path(integration.path))
    assert res.return_code == 0
    assert res.errors == []
    assert res.errors_and_warnings == ""
    assert res.skipped_file.endswith("integration.py")


class InProcessPool:
    """Runs pool.map in the current process, so mocks and patches apply."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def map(self, func, items):
        return [func(item) for item in items]


def test_xsoar_linter_manager(mocker):
    """
    Given:
        One file to lint.

    When:
        Calling xsoar_linter_manager.

    Then:
        Assert process_file runs once, and the start/finish log lines show the file count and the duration.
    """
    mocker.patch.object(xsoar_linter.multiprocessing, "Pool", InProcessPool)
    worker = mocker.patch.object(
        xsoar_linter, "process_file", return_value=ProcessResults()
    )
    logger_info = mocker.patch.object(xsoar_linter.logger, "info")

    assert xsoar_linter_manager([Path("a.py")]) == 0

    assert worker.call_count == 1
    messages = [call.args[0] for call in logger_info.call_args_list]
    assert any(
        message.startswith("[xsoar-lint] starting on 1 file(s)") for message in messages
    )
    assert any(
        message.startswith("[xsoar-lint] finished 1 file(s) in ")
        and "errors=0, warnings=0, failed files=0, skipped=0." in message
        for message in messages
    )
    assert not any(message.startswith("[xsoar-lint] skipped ") for message in messages)


def test_xsoar_linter_manager_logs_skipped_files(mocker):
    """
    Given:
        Two files, one of them skipped by `# xsoar-lint: skip-parse-file`.

    When:
        Calling xsoar_linter_manager.

    Then:
        Assert one info line names the skipped file, the finish line shows skipped=1,
        and the run passes.
    """
    mocker.patch.object(xsoar_linter.multiprocessing, "Pool", InProcessPool)
    mocker.patch.object(
        xsoar_linter,
        "process_file",
        side_effect=[
            ProcessResults(skipped_file="Packs/A/Integrations/A/A.py"),
            ProcessResults(),
        ],
    )
    logger_info = mocker.patch.object(xsoar_linter.logger, "info")

    assert xsoar_linter_manager([Path("A.yml"), Path("B.yml")]) == 0

    messages = [call.args[0] for call in logger_info.call_args_list]
    assert (
        "[xsoar-lint] skipped Packs/A/Integrations/A/A.py ('# xsoar-lint: skip-parse-file')."
        in messages
    )
    assert (
        len(
            [
                message
                for message in messages
                if message.startswith("[xsoar-lint] skipped ")
            ]
        )
        == 1
    )
    assert any(
        message.startswith("[xsoar-lint] finished 2 file(s) in ")
        and "failed files=0, skipped=1." in message
        for message in messages
    )
