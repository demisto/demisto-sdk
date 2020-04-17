from os.path import join
from subprocess import PIPE, run

from demisto_sdk.commands.common.git_tools import git_path

DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
MAIN_MODULE_PATH = join(DEMISTO_SDK_PATH, "__main__.py")
PYTHON_CMD = "python"
VALIDATE_CMD = "validate"
PACK_INTEGRATION_PATH = "Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"


def test_integration_validate():
    results = run(
        [PYTHON_CMD, MAIN_MODULE_PATH, VALIDATE_CMD, "-p", PACK_INTEGRATION_PATH],
        stderr=PIPE,
        stdout=PIPE,
        encoding='utf-8',
        cwd=join(DEMISTO_SDK_PATH, "tests", "test_files", "content_repo_example")
    )
    stdout = results.stdout
    assert "Starting validating files structure" in stdout
    assert f"Validating {PACK_INTEGRATION_PATH}" in stdout
    assert "The docker image tag is not the latest, please update it" in stdout
    assert f"{PACK_INTEGRATION_PATH}: You're not using latest docker for the file, " \
           "please update to latest version." in stdout
    assert "The files were found as invalid, the exact error message can be located above" in stdout
    assert results.stderr == ""
