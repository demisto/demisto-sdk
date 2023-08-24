from demisto_sdk.commands.format.format_module import format_manager
from TestSuite.test_tools import ChangeCWD


def test_format_venv_in_dir(mocker, repo):
    """
    Given:
        - .venv dir inside the path given to format, with an invalid file
    When:
        - Running format -i
    Then:
        - ignore the .venv directory.
    """
    pack = repo.create_pack("SomePack1")
    pack._venv_dir = pack._pack_path / ".venv"
    pack._venv_dir.mkdir()
    pack._create_text_based(
        name="generic_file.py", content="print('hello'", dir_path=pack._venv_dir
    )
    pack.create_integration(name="SomeIntegration")
    format_file_call = mocker.patch(
        "demisto_sdk.commands.format.format_module.run_format_on_file",
        return_value=("ok", None, None),
    )

    with ChangeCWD(repo.path):
        assert format_manager(input=str(pack._pack_path)) == 0

    assert format_file_call.called
    for call_args in format_file_call.call_args_list:
        assert ".venv" not in call_args.kwargs["input"]
