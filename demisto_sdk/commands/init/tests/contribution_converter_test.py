import inspect
import os
import re
import shutil
from difflib import Differ
from os.path import join
from pathlib import Path
from typing import Optional, Union
from zipfile import ZipFile

import pytest
import urllib3
from _pytest.fixtures import FixtureRequest
from _pytest.tmpdir import TempPathFactory, _mk_tmp
from pytest_mock import MockerFixture

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATIONS_DIR,
    INTEGRATIONS_README_FILE_NAME,
    LAYOUT,
    LAYOUTS_CONTAINER,
    LAYOUTS_DIR,
    PACKS_DIR,
    PACKS_README_FILE_NAME,
    PLAYBOOKS_DIR,
    SCRIPTS_DIR,
)
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_child_directories
from demisto_sdk.commands.content_graph.common import PACK_METADATA_FILENAME
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_script,
)
from demisto_sdk.commands.init.contribution_converter import (
    ContributionConverter,
    get_previous_nonempty_line,
)
from TestSuite.contribution import Contribution
from TestSuite.repo import Repo

yaml = YAML_Handler()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
CONTRIBUTION_TESTS = Path(DEMISTO_SDK_PATH, "commands", "init", "tests", "test_files")

RELEASE_NOTES_COPY = "demisto_sdk/commands/init/tests/RN/1_0_1-formatted.md"
SOURCE_RELEASE_NOTES_FILE = "demisto_sdk/commands/init/tests/RN/1_0_1.md"
EXPECTED_RELEASE_NOTES = "demisto_sdk/commands/init/tests/RN/1_0_1_expected.md"
NEW_ENTITY_SOURCE_RELEASE_NOTES_FILE = (
    "demisto_sdk/commands/init/tests/RN_ENTITY/1_0_1.md"
)
NEW_ENTITY_RELEASE_NOTES_COPY = (
    "demisto_sdk/commands/init/tests/RN_ENTITY/1_0_1-formatted.md"
)
EXPECTED_NEW_ENTITY_RELEASE_NOTES = (
    "demisto_sdk/commands/init/tests/RN_ENTITY/1_0_1_expected.md"
)

name_reformatting_test_examples = [
    ("PACKYAYOK", "PACKYAYOK"),
    ("PackYayOK", "PackYayOK"),
    ("pack yay ok!", "PackYayOk"),
    ("PackYayOK", "PackYayOK"),
    ("-pack-yay-ok--", "Pack-Yay-Ok"),
    ("PackYayOK", "PackYayOK"),
    (
        "The quick brown fox, jumps over the lazy dog!",
        "TheQuickBrownFox_JumpsOverTheLazyDog",
    ),
    (
        "The quick`*+.brown fox, ;jumps over @@the lazy dog!",
        "TheQuick_BrownFox_JumpsOver_TheLazyDog",
    ),
    (
        "ThE quIck`*+.brown fox, ;jumps ovER @@the lazy dog!",
        "ThEQuIck_BrownFox_JumpsOvER_TheLazyDog",
    ),
]


def util_open_file(path):
    with open(path) as f:
        return f.read()


@pytest.fixture
def contrib_converter(tmp_path: Path, git_repo: Repo):
    return ContributionConverter(
        contribution="contribution.zip",
        name="",
        pack_dir_name="",
        base_dir=git_repo.path,
        working_dir_path=str(tmp_path),
    )


@pytest.fixture
def create_test_packs(request: FixtureRequest, tmp_path_factory: TempPathFactory):
    """Create TmpPack objects for each pack name passed in the request.param"""
    if isinstance(request.param, (list, tuple)):
        tmp_packs = []
        for pack_name in request.param:
            pack_dir = tmp_path_factory.mktemp(pack_name)
            pack = TmpPack(pack_dir)
            tmp_packs.append(pack)
        return tmp_packs
    # otherwise assume it's a string
    pack_dir = tmp_path_factory.mktemp(request.param)
    return TmpPack(pack_dir)


def get_function_name() -> str:
    """
    Returns the function name
    """
    return inspect.currentframe().f_back.f_code.co_name


class TmpPack(os.PathLike):
    def __init__(self, pack_dir):
        self.pack_dir = pack_dir

        self.default_integration_name = "defaultintegration"
        self.integration_cnt = 0
        self.integration_dir = self.pack_dir / "Integrations"

        self.default_script_name = "defaultscript"
        self.script_dir = self.pack_dir / "Scripts"
        self.script_cnt = 0

    def create_file(self, path, contents: Optional[str] = None):
        file_path = self.pack_dir / path
        file_contents = contents if contents else path
        file_path.write_text(file_contents)

    def create_integration(self, name: Optional[str], contents: Optional[str] = None):
        if not self.integration_dir.exists():
            self.integration_dir.mkdir()
        if name:
            integration_name = name
        else:
            integration_name = f"{self.default_integration_name}-{self.integration_cnt}"
            self.integration_cnt += 1
        integration_package_dir = self.integration_dir / integration_name
        integration_package_dir.mkdir()
        integration_files_to_make = {
            f"{integration_name}.py",
            f"{integration_name}.yml",
            f"{integration_name}_image.png",
            f"{integration_name}_description.md",
        }
        file_contents = contents if contents else integration_name
        for integration_file in integration_files_to_make:
            integration_file_path = integration_package_dir / integration_file
            integration_file_path.write_text(file_contents)

    def create_script(self, name: Optional[str], contents: Optional[str] = None):
        if not self.script_dir.exists():
            self.script_dir.mkdir()
        if name:
            script_name = name
        else:
            script_name = f"{self.default_script_name}-{self.script_cnt}"
            self.script_cnt += 1
        script_package_dir = self.script_dir / script_name
        script_package_dir.mkdir()
        script_files_to_make = {
            f"{script_name}.py",
            f"{script_name}.yml",
            f"{script_name}_image.png",
            f"{script_name}_description.md",
        }
        file_contents = contents if contents else script_name
        for script_file in script_files_to_make:
            script_file_path = script_package_dir / script_file
            script_file_path.write_text(file_contents)

    def __fspath__(self):
        return str(self.pack_dir)

    def __str__(self):
        return str(self.pack_dir)


def create_contribution_converter(
    request: FixtureRequest, tmp_path_factory: TempPathFactory
) -> ContributionConverter:
    tmp_dir = _mk_tmp(request, tmp_path_factory)
    return ContributionConverter(
        contribution="contrib.zip", name=request.param, base_dir=str(tmp_dir)
    )


@pytest.fixture
def contribution_converter(
    request: FixtureRequest, tmp_path_factory: TempPathFactory
) -> ContributionConverter:
    """Mocking tmp_path"""
    return create_contribution_converter(request, tmp_path_factory)


def rename_file_in_zip(
    path_to_zip: Union[os.PathLike, str],
    original_file_name: str,
    updated_file_name: str,
):
    """Utility to rename a file in a zip file

    Useful for renaming files in an example contribution zip file to test specific cases.
    If the zipped file includes directories, make sure the filenames take that into account.

    Args:
        path_to_zip (Union[os.PathLike, str]): The zip file containing a file which needs renaming
        original_file_name (str): The file which will be renamed
        updated_file_name (str): The name the original file will be renamed to
    """
    modded_zip_file = os.path.join(
        os.path.dirname(path_to_zip), "Edit" + Path(path_to_zip).name
    )
    tmp_zf = ZipFile(modded_zip_file, "w")
    with ZipFile(path_to_zip, "r") as zf:
        for item in zf.infolist():
            if item.filename == original_file_name:
                with tmp_zf.open(updated_file_name, "w") as out_file:
                    out_file.write(zf.read(item.filename))
            else:
                tmp_zf.writestr(item, zf.read(item.filename))
    os.replace(modded_zip_file, path_to_zip)


def test_convert_contribution_zip_updated_pack(tmp_path, mocker):
    """
    Create a fake contribution zip file and test that it is converted to a Pack correctly.
    The pack already exists, checking the update flow.

    Args:
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file.

    Given
    - A contribution zip file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    - The contribution is an update to an existing pack
    Then
    - Ensure integration are componentized and in valid directory structure
    - Ensure that readme file has not been changed.

    """
    mocker.patch.object(GitUtil, "added_files", return_value=set())
    mocker.patch.object(GitUtil, "modified_files", return_value=set())
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    repo_dir = tmp_path / "content_repo"
    repo_dir.mkdir()
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = repo_dir / "target_dir"
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / "contrib_zip"
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    repo = Repo(repo_dir)
    mocker.patch(
        "demisto_sdk.commands.init.contribution_converter.CONTENT_PATH", repo.path
    )
    pack = repo.create_pack("TestPack")
    integration = pack.create_integration("integration0")
    integration.create_default_integration()
    contrib_zip = Contribution(target_dir, "ContribTestPack", repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()
    name = "Test Pack"
    contribution_path = contrib_zip.created_zip_filepath
    description = "test pack description here"
    author = "Octocat Smith"
    contrib_converter_inst = ContributionConverter(
        name=name,
        contribution=contribution_path,
        description=description,
        author=author,
        create_new=False,
        base_dir=repo.path,
    )
    contrib_converter_inst.convert_contribution_to_pack()
    converted_pack_path = repo_dir / "Packs" / "TestPack"
    assert converted_pack_path.exists()
    integrations_path = converted_pack_path / "Integrations"
    sample_integration_path = integrations_path / "integration0"
    integration_yml = sample_integration_path / "integration0.yml"
    integration_py = sample_integration_path / "integration0.py"
    integration_description = sample_integration_path / "integration0_description.md"
    integration_image = sample_integration_path / "integration0_image.png"
    integration_readme_md = sample_integration_path / PACKS_README_FILE_NAME
    unified_yml = integrations_path / "integration-integration0.yml"
    unified_yml_in_sample = sample_integration_path / "integration-integration0.yml"
    integration_files = [
        integration_yml,
        integration_py,
        integration_description,
        integration_image,
        integration_readme_md,
    ]
    for integration_file in integration_files:
        assert integration_file.exists()
    # In a new pack that part will exist.

    assert not unified_yml.exists()
    assert not unified_yml_in_sample.exists()


def test_convert_contribution_zip_outputs_structure(
    tmp_path: Path, mocker: MockerFixture, git_repo: Repo
):
    """Create a fake contribution zip file and test that it is converted to a Pack correctly

    Args:
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    - The zipfile contains a unified script file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure the unified yaml files of the integration and script have been removed from the output created by
      converting the contribution zip file
    """
    pack_name = "ContribTestPack"
    integration_name = "Sample"
    script_name = "SampleScript"

    # ### Mock the content graph ### #

    class MockedContentGraphInterface:
        output_path = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def search(self, path):
            # Simulate the graph search
            return [mock_script()]

    mocker.patch(
        "demisto_sdk.commands.generate_docs.generate_script_doc.ContentGraphInterface",
        return_value=MockedContentGraphInterface(),
    )
    mocker.patch(
        "demisto_sdk.commands.generate_docs.generate_script_doc.update_content_graph",
        return_value=[],
    )

    # ### SETUP ### #
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / "contrib_zip"
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
    contrib_zip = Contribution(target_dir, pack_name, git_repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # rename script-script0.yml unified to automation-script0.yml
    # this naming is aligned to how the server exports scripts in contribution zips
    rename_file_in_zip(
        contrib_zip.created_zip_filepath,
        "automation/script-script0.yml",
        "automation/automation-script0.yml",
    )

    # Convert Zip
    name = "Contrib Test Pack"
    contribution_path = contrib_zip.created_zip_filepath
    description = "test pack description here"
    author = "Octocat Smith"
    contrib_converter_inst = ContributionConverter(
        name=name,
        pack_dir_name=pack_name,
        contribution=contribution_path,
        description=description,
        author=author,
        working_dir_path=str(tmp_path),
    )
    contrib_converter_inst.convert_contribution_to_pack()

    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    assert (tmp_path / INTEGRATIONS_DIR).exists()
    assert (tmp_path / INTEGRATIONS_DIR / integration_name).exists()
    assert (
        tmp_path / INTEGRATIONS_DIR / integration_name / f"{integration_name}_image.png"
    ).exists()
    assert (
        tmp_path / INTEGRATIONS_DIR / integration_name / f"{integration_name}.py"
    ).exists()
    assert (
        tmp_path / INTEGRATIONS_DIR / integration_name / f"{integration_name}.yml"
    ).exists()
    assert (
        tmp_path / INTEGRATIONS_DIR / integration_name / INTEGRATIONS_README_FILE_NAME
    ).exists()
    assert (
        tmp_path
        / INTEGRATIONS_DIR
        / integration_name
        / f"{integration_name}_description.md"
    ).exists()
    assert not (tmp_path / INTEGRATIONS_DIR / "integration-integration0.yml").exists()
    assert not (
        tmp_path / INTEGRATIONS_DIR / integration_name / "integration-integration0.yml"
    ).exists()

    assert (tmp_path / SCRIPTS_DIR / script_name / f"{script_name}.py").exists()
    assert (tmp_path / SCRIPTS_DIR / script_name / f"{script_name}.yml").exists()
    assert (
        tmp_path / SCRIPTS_DIR / script_name / INTEGRATIONS_README_FILE_NAME
    ).exists()

    assert tmp_path / PLAYBOOKS_DIR / "playbook-SamplePlaybook.yml"
    assert tmp_path / PLAYBOOKS_DIR / "playbook-SamplePlaybook_README.md"

    assert (tmp_path / CLASSIFIERS_DIR / "classifier-mapper-fakemapper.json").exists()
    assert (tmp_path / CLASSIFIERS_DIR / "classifier-fakeclassifier.json").exists()

    assert (tmp_path / LAYOUTS_DIR / "layout-fakelayout.json").exists()
    assert (
        tmp_path / LAYOUTS_DIR / "layoutscontainer-fakelayoutscontainer.json"
    ).exists()

    assert (
        tmp_path / INCIDENT_TYPES_DIR / "incident-type-fakeincidenttype.json"
    ).exists()

    assert (
        tmp_path / INCIDENT_FIELDS_DIR / "incident-field-fakeincidentfield.json"
    ).exists()

    assert (
        tmp_path / INDICATOR_FIELDS_DIR / "incident-field-fakeindicatorfield.json"
    ).exists()

    assert (tmp_path / PACK_METADATA_FILENAME).exists()
    assert (tmp_path / PACKS_README_FILE_NAME).exists()
    assert (tmp_path / ".secrets-ignore").exists()
    assert (tmp_path / ".pack-ignore").exists()


def test_convert_contribution_zip(
    tmp_path: Path, mocker: MockerFixture, git_repo: Repo
):
    """Create a fake contribution zip file and test that it is converted to a Pack correctly

    Args:
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    - The zipfile contains a unified script file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure script and integration are componentized and in valid directory structure
    - Ensure readme_files is not empty and the generated docs exists.
    """
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / "contrib_zip"
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    mocker.patch(
        "demisto_sdk.commands.init.contribution_converter.CONTENT_PATH", git_repo.path
    )

    contrib_zip = Contribution(target_dir, "ContribTestPack", git_repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    # rename script-script0.yml unified to automation-script0.yml
    # this naming is aligned to how the server exports scripts in contribution zips
    rename_file_in_zip(
        contrib_zip.created_zip_filepath,
        "automation/script-script0.yml",
        "automation/automation-script0.yml",
    )

    name = "Contrib Test Pack"
    contribution_path = contrib_zip.created_zip_filepath
    description = "test pack description here"
    author = "Octocat Smith"
    contrib_converter_inst = ContributionConverter(
        name=name,
        contribution=contribution_path,
        description=description,
        author=author,
        base_dir=git_repo.path,
    )
    contrib_converter_inst.convert_contribution_to_pack()

    converted_pack_path = Path(git_repo.path) / PACKS_DIR / "ContribTestPack"
    assert converted_pack_path.exists()

    scripts_path = converted_pack_path / "Scripts"
    sample_script_path = scripts_path / "SampleScript"
    script_yml = sample_script_path / "SampleScript.yml"
    script_py = sample_script_path / "SampleScript.py"
    script_readme_md = sample_script_path / PACKS_README_FILE_NAME
    unified_script_in_sample = sample_script_path / "automation-script0.yml"
    unified_script = scripts_path / "automation-script0.yml"

    assert scripts_path.exists()
    assert sample_script_path.exists()
    assert script_yml.exists()
    assert script_py.exists()
    assert script_readme_md.exists()
    assert not unified_script_in_sample.exists()
    assert not unified_script.exists()

    integrations_path = converted_pack_path / "Integrations"
    sample_integration_path = integrations_path / "Sample"
    integration_yml = sample_integration_path / "Sample.yml"
    integration_py = sample_integration_path / "Sample.py"
    integration_description = sample_integration_path / "Sample_description.md"
    integration_image = sample_integration_path / "Sample_image.png"
    integration_readme_md = sample_integration_path / PACKS_README_FILE_NAME
    unified_yml = integrations_path / "integration-integration0.yml"
    unified_yml_in_sample = sample_integration_path / "integration-integration0.yml"
    integration_files = [
        integration_yml,
        integration_py,
        integration_description,
        integration_image,
        integration_readme_md,
    ]
    for integration_file in integration_files:
        assert integration_file.exists()
    assert not unified_yml.exists()
    assert not unified_yml_in_sample.exists()

    playbooks_path = converted_pack_path / "Playbooks"
    playbook_yml = playbooks_path / "playbook-SamplePlaybook.yml"
    playbook_readme_md = playbooks_path / "playbook-SamplePlaybook_README.md"

    assert playbooks_path.exists()
    assert playbook_yml.exists()
    assert playbook_readme_md.exists()

    layouts_path = converted_pack_path / "Layouts"
    sample_layoutscontainer = (
        layouts_path / f"{LAYOUTS_CONTAINER}-fakelayoutscontainer.json"
    )
    sample_layout = layouts_path / f"{LAYOUT}-fakelayout.json"

    assert layouts_path.exists()
    assert sample_layoutscontainer.exists()
    assert sample_layout.exists()

    assert set(contrib_converter_inst.readme_files) == {
        str(playbook_readme_md),
        str(integration_readme_md),
        str(script_readme_md),
    }


def test_convert_contribution_zip_with_args(
    tmp_path: Path, mocker: MockerFixture, git_repo: Repo
):
    """Convert a contribution zip to a pack and test that the converted pack's 'pack_metadata.json' is correct

    Args:
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    When
    - The contrib_converter class instance is instantiated with the 'name' argument of 'Test Pack'
    - The contrib_converter class instance is instantiated with the 'description' argument
      of 'test pack description here'
    - The contrib_converter class instance is instantiated with the 'author' argument of 'Octocat Smith'
    - The contrib_converter class instance is instantiated with the 'gh_user' argument of 'octocat'
    Then
    - Ensure pack with directory name of 'TestPack' is created
    - Ensure that the pack's 'pack_metadata.json' file's 'name' field is 'Test Pack'
    - Ensure that the pack's 'pack_metadata.json' file's 'description' field is 'test pack description here'
    - Ensure that the pack's 'pack_metadata.json' file's 'author' field is 'Octocat Smith'
    - Ensure that the pack's 'pack_metadata.json' file's 'githubUser' field a list containing only 'octocat'
    - Ensure that the pack's 'pack_metadata.json' file's 'email' field is the empty string
    """
    mocker.patch.object(git_repo.git_util, "added_files", return_value=set())
    mocker.patch.object(git_repo.git_util, "modified_files", return_value=set())

    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = Path(str(tmp_path), "target_dir")
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = Path(str(tmp_path), "contrib_zip")
    contribution_zip_dir.mkdir()

    mocker.patch(
        "demisto_sdk.commands.init.contribution_converter.CONTENT_PATH", git_repo.path
    )
    contrib_zip = Contribution(target_dir, "ContribTestPack", git_repo)
    # contrib_zip.create_zip(contribution_zip_dir)
    contrib_zip.create_zip(contribution_zip_dir)

    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    name = "Test Pack"
    contribution_path = contrib_zip.created_zip_filepath
    description = "test pack description here"
    author = "Octocat Smith"
    gh_user = "octocat"
    contrib_converter_inst = ContributionConverter(
        name=name,
        contribution=contribution_path,
        description=description,
        author=author,
        gh_user=gh_user,
        base_dir=git_repo.path,
    )
    contrib_converter_inst.convert_contribution_to_pack()

    converted_pack_path = git_repo._packs_path / "TestPack"
    assert converted_pack_path.exists()

    pack_metadata_path = converted_pack_path / "pack_metadata.json"
    assert pack_metadata_path.exists()
    with open(pack_metadata_path) as pack_metadata:
        metadata = json.load(pack_metadata)
        assert metadata.get("name", "") == name
        assert metadata.get("description", "") == description
        assert metadata.get("author", "") == author
        assert metadata.get("githubUser", []) == [gh_user]
        assert metadata.get("marketplaces", []) == ["xsoar", "marketplacev2"]
        assert not metadata.get("email")


@pytest.mark.parametrize(
    "input_name,expected_output_name", name_reformatting_test_examples
)
def test_format_pack_dir_name(contrib_converter, input_name, expected_output_name):
    """Test the 'format_pack_dir_name' method with various inputs

    Args:
        contrib_converter (fixture): An instance of the ContributionConverter class
        input_name (str): A 'name' argument value to test
        expected_output_name (str): The value expected to be returned by passing 'input_name'
            to the 'format_pack_dir_name' method

    Scenario: Creating a new pack from a contribution zip file

    Given
    - A pack name

    When
    - The pack name is passed to the 'format_pack_dir_name' method

    Then
    - Ensure the reformatted pack name returned by the method matches the expected output
    - Ensure the reformatted pack name returned by the method contains only valid characters
        (alphanumeric, underscore, and dash with no whitespace)
    """
    output_name = contrib_converter.format_pack_dir_name(input_name)
    assert output_name == expected_output_name
    assert not re.search(
        r"\s", output_name
    ), 'Whitespace was found in the returned value from executing "format_pack_dir_name"'
    err_msg = "Characters other than alphanumeric, underscore, and dash were found in the output"
    assert all([char.isalnum() or char in {"_", "-"} for char in output_name]), err_msg
    if len(output_name) > 1:
        first_char = output_name[0]
        if first_char.isalpha():
            assert (
                first_char.isupper()
            ), "The output's first character should be capitalized"
    assert not output_name.startswith(
        ("-", "_")
    ), "The output's first character must be alphanumeric"
    assert not output_name.endswith(
        ("-", "_")
    ), "The output's last character must be alphanumeric"


def test_convert_contribution_dir_to_pack_contents(tmp_path: Path, repo: Repo):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - The pack's original content contains incident field files and appears like so

        ├── IncidentFields
        │   └── incidentfield-SomeIncidentField.json

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── IncidentFields
        │   └── incidentfield-SomeIncidentField.json
        ├── incidentfield
        │   └── incidentfield-SomeIncidentField.json

    Then
    - Ensure the file '.../incidentfield/incidentfield-SomeIncidentField.json' is moved to
        '.../IncidentFields/incidentfield-SomeIncidentField.json' and overwrites the existing file
    """

    incident_field_data = {"field": "old_value"}

    tmp_unzipped_path = tmp_path / "incidentfield"
    tmp_unzipped_ic_path = tmp_unzipped_path / "SomeIncidentField.json"

    tmp_renamed_path = tmp_path / INCIDENT_FIELDS_DIR
    tmp_renamed_ic_path = tmp_renamed_path / "SomeIncidentField.json"

    tmp_unzipped_path.mkdir()
    tmp_unzipped_ic_path.touch()

    with tmp_unzipped_ic_path.open("w") as ic:
        json.dump(incident_field_data, ic)

    converter = ContributionConverter(
        contribution="",
        working_dir_path=str(tmp_path),
        base_dir=repo.path,
    )

    converter.convert_contribution_dir_to_pack_contents(str(tmp_unzipped_path))

    assert json.loads(tmp_renamed_ic_path.read_text()) == incident_field_data
    assert not tmp_unzipped_path.exists()


directories_set_2 = {
    "IndicatorTypes",
    "Layouts",
    "IndicatorFields",
    "Classifiers",
    "IncidentFields",
}

indicatorfield_and_incidentfield_check = (
    os.path.join(
        CONTRIBUTION_TESTS,
        get_function_name(),
        "contribution_indicatorfield_and_incidentfield.zip",
    ),
    directories_set_2,
)


def test_rearranging_before_conversion_indicator_fields(repo: Repo):
    """
    Given a zip file, fixes the wrong server mapping in both indicator fields.

    Scenario: Simulate converting a contribution zip file.

    Given
    - zip_path (str): A contribution zip file
    - expected_directories (set): A set of directories that we expect now after patching to be
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure the mapping is correct now
    - Ensure (at first test/check) in case the original directory becomes empty, then it is deleted

    """

    zip_path = os.path.join(
        CONTRIBUTION_TESTS, get_function_name(), "contribution_indicatorfield_only.zip"
    )
    expected = [INDICATOR_TYPES_DIR, LAYOUTS_DIR, INDICATOR_FIELDS_DIR, CLASSIFIERS_DIR]
    expected.sort()

    contribution_converter = ContributionConverter(
        contribution=zip_path, base_dir=repo.path
    )
    contribution_converter.convert_contribution_to_pack()
    unpacked_contribution_dirs = get_child_directories(
        contribution_converter.pack_dir_path
    )

    actual = [Path(d).name for d in unpacked_contribution_dirs]
    actual.sort()
    assert actual == expected


def test_rearranging_before_conversion_indicator_and_incident_fields(repo: Repo):
    """
    Given a zip file, fixes the wrong server mapping in both indicator and incident fields.
    Scenario: Simulate converting a contribution zip file.

    Given
    - zip_path (str): A contribution zip file
    - expected_directories (set): A set of directories that we expect now after patching to be
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure the mapping is correct now
    - Ensure (at first test/check) in case the original directory becomes empty, then it is deleted

    """

    zip_path = os.path.join(
        CONTRIBUTION_TESTS,
        get_function_name(),
        "contribution_indicatorfield_and_incidentfield.zip",
    )
    expected = [
        INDICATOR_TYPES_DIR,
        LAYOUTS_DIR,
        INCIDENT_FIELDS_DIR,
        INDICATOR_FIELDS_DIR,
        CLASSIFIERS_DIR,
    ]
    expected.sort()

    contribution_converter = ContributionConverter(
        contribution=zip_path, base_dir=repo.path
    )
    contribution_converter.convert_contribution_to_pack()
    unpacked_contribution_dirs = get_child_directories(
        contribution_converter.pack_dir_path
    )

    actual = [Path(d).name for d in unpacked_contribution_dirs]
    actual.sort()
    assert actual == expected


@pytest.mark.parametrize(
    "input_script, output_version",
    [
        (
            "This is a test script\n the script contains a pack version\n ### pack version: 3.4.5  TEST TEST",
            "3.4.5",
        ),
        (
            "This is a test script\n the script does not contain a pack version\n ### TEST TEST",
            "0.0.0",
        ),
        (
            "This is a test js script\n the script does not contain a pack version\n // pack version: 3.4.5 TEST TEST",
            "3.4.5",
        ),
        ("", "0.0.0"),
    ],
)
def test_extract_pack_version(input_script: str, output_version: str, repo: Repo):
    """
    Given:
    - A text with/without the pack version in it.

    When:
    - Running extract_pack_version function.

    Then:
    - Ensure that pack version was extracted correctly.

    """
    contribution_converter = ContributionConverter(
        contribution="contrib.zip", base_dir=repo.path
    )
    assert contribution_converter.extract_pack_version(input_script) == output_version


def test_create_contribution_items_version_note(repo: Repo):
    contribution_converter = ContributionConverter(
        contribution="contrib.zip", base_dir=repo.path
    )
    contribution_converter.contribution_items_version = {
        "CortexXDRIR": {"contribution_version": "1.2.2", "latest_version": "1.2.4"},
        "XDRScript": {"contribution_version": "1.2.2", "latest_version": "1.2.4"},
    }
    contribution_converter.create_contribution_items_version_note()
    assert (
        contribution_converter.contribution_items_version_note
        == """> **Warning**
> The changes in the contributed files were not made on the most updated pack versions
> | **Item Name** | **Contribution Pack Version** | **Latest Pack Version**
> | --------- | ------------------------- | -------------------
> | CortexXDRIR | 1.2.2 | 1.2.4
> | XDRScript | 1.2.2 | 1.2.4
>
> **For the Reviewer:**
> 1. Currently the diff you see on Github is between the contribution original version and the contribution changes since the contribution was made on an outdated version.
> 2. You will see the diff between the contribution changes and Content master only after you fix all conflicts.
> 3. Fix conflicts only after completing the review process and once the contributor has finished resubmitting changes.
> For more details see Confluence page [link](https://confluence-dc.paloaltonetworks.com/display/DemistoContent/Conducting+Code+Review).
"""
    )


@pytest.mark.parametrize("contribution_converter", ["TestPack"], indirect=True)
class TestEnsureUniquePackDirName:
    def test_ensure_unique_pack_dir_name_no_conflict(self, contribution_converter):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There does not already exist a pack directory with the proposed name

        Then
        - Ensure the pack directory name returned by the method matches the expected output - should be unchanged
        """
        pack_name = "TestPack"
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        print(f"crb_crvrt.pack_dir_path={crb_crvrt.pack_dir_path}")  # noqa: T201
        assert os.path.isdir(crb_crvrt.pack_dir_path)

    def test_ensure_unique_pack_dir_name_with_conflict(self, contribution_converter):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There already exists a pack directory with the proposed name

        Then
        - Ensure the pack directory name returned by the method matches the expected output, which is that a
          version number should have been added
        """
        pack_name = "TestPack"
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        assert os.path.isdir(crb_crvrt.pack_dir_path)
        new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(pack_name)
        assert new_pack_dir_name != pack_name
        assert new_pack_dir_name == pack_name + "V2"

    def mock_format_manager(*args):
        return args

    @pytest.mark.parametrize("new_pack", [True, False])
    def test_format_converted_pack(
        self, contribution_converter, mocker: MockerFixture, new_pack
    ):
        """Test the 'format_converted_pack' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Formatting the added/modified files by including the untracked files in a non-interactive mode

        Given
        - ContributionConverter class

        When
        - Running the format_converted_pack method to format the files

        Then
        - Ensure that we format the untracked files as well and the interactive flag is set to false
        """
        contribution_converter.create_new = new_pack
        result = mocker.patch(
            "demisto_sdk.commands.init.contribution_converter.format_manager",
            side_efect=self.mock_format_manager(),
        )
        contribution_converter.format_converted_pack()

        assert result.call_args[1].get("include_untracked") is False
        assert result.call_args[1].get("interactive") is False

    def test_ensure_unique_pack_dir_name_with_conflict_and_version_suffix(
        self, contribution_converter
    ):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There already exists a pack directory with the proposed name
        - The proposed name ends with a version suffix, e.g. 'V2'

        Then
        - Ensure the pack directory name returned by the method matches the expected output, which is that the
          version number should have been incremented
        """
        pack_name = "TestPack"
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        assert os.path.isdir(crb_crvrt.pack_dir_path)
        new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(pack_name)
        assert new_pack_dir_name != pack_name
        assert new_pack_dir_name == pack_name + "V2"
        os.makedirs(os.path.join(crb_crvrt.packs_dir_path, new_pack_dir_name))
        incremented_new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(
            new_pack_dir_name
        )
        assert incremented_new_pack_dir_name == pack_name + "V3"


class TestReleaseNotes:
    @pytest.fixture(autouse=True)
    def rn_file_copy(self):
        yield shutil.copyfile(SOURCE_RELEASE_NOTES_FILE, RELEASE_NOTES_COPY)
        Path(RELEASE_NOTES_COPY).unlink(missing_ok=True)

    @pytest.fixture(autouse=True)
    def new_entity_rn_file_copy(self):
        yield shutil.copyfile(
            NEW_ENTITY_SOURCE_RELEASE_NOTES_FILE, NEW_ENTITY_RELEASE_NOTES_COPY
        )
        Path(NEW_ENTITY_RELEASE_NOTES_COPY).unlink(missing_ok=True)

    @pytest.mark.parametrize(
        "index, expected_result",
        [
            (0, ""),
            (1, ""),
            (2, ""),
            (3, "#### Integrations\n"),
            (4, ""),
            (5, "##### Core REST API\n"),
            (6, ""),
            (7, "- %%UPDATE_RN%%\n"),
            (9, "#### Scripts\n"),
            (11, "##### New: DemistoUploadFileToIncident\n"),
        ],
    )
    def test_get_previous_nonempty_line(self, index: int, expected_result: str):
        """Test the 'get_previous_nonempty_line' method

        Given
        - An index and a lines array.

        When
        - Running get_previous_nonempty_line.

        Then
        - Ensure the correct previous line (which is not a new line) was returned.
        """
        lines = [
            "\n",
            "#### Integrations\n",
            "\n",
            "##### Core REST API\n",
            "\n",
            "- %%UPDATE_RN%%\n",
            "\n",
            "#### Scripts\n",
            "\n",
            "##### New: DemistoUploadFileToIncident\n",
            "\n",
            "some description\n",
            "##### New: DemistoCreateList_1\n",
            "\n",
            "- New: Create a new list (Available from Cortex XSOAR 6.8.0).\n",
        ]

        assert get_previous_nonempty_line(lines, index) == expected_result

    def test_replace_RN_template_with_value(
        self, mocker: MockerFixture, contrib_converter, rn_file_copy
    ):
        """Test the 'replace_RN_template_with_value' method
        Scenario:
            Adding the user's release note text to the rn file that was generated by the UpdateRN class.
            Detected content item has less object than git detected.

        Given
        - A pack's release note file path

        When
        - The contribution was made to an existing pack.

        Then
        - Ensure the RN file template text was modified with the user's input
        """
        contrib_converter.release_notes = (
            "#### Integrations\n##### CrowdStrikeMalquery\n- release note entry number "
            "#1\n- release note entry number #2\n\n#### Playbooks\n##### "
            "CrowdStrikeMalquery - Multidownload and Fetch\n- changed this playbook\n- "
            "Updated another thing\n\n"
        )
        contrib_converter.detected_content_items = [
            {
                "id": "CrowdStrikeMalquery_copy",
                "name": "CrowdStrikeMalquery_copy",
                "source_id": "CrowdStrikeMalquery",
                "source_name": "CrowdStrikeMalquery",
                "source_file_name": "Packs/CrowdStrikeMalquery/Integrations/CrowdStrikeMalquery/CrowdStrikeMalquery.yml",
            }
        ]

        mocker.patch(
            "demisto_sdk.commands.init.contribution_converter.get_display_name",
            return_value="CrowdStrike Malquery",
        )
        contrib_converter.replace_RN_template_with_value(RELEASE_NOTES_COPY)

        assert util_open_file(RELEASE_NOTES_COPY) == util_open_file(
            EXPECTED_RELEASE_NOTES
        )
        assert True

    def test_replace_RN_new_entity_in_existing_pack(
        self, contrib_converter, new_entity_rn_file_copy
    ):
        """Test the 'replace_RN_template_with_value' method
        Scenario:
            Adding the user's release note text to the rn file that was generated by the UpdateRN class.
            New entities were added to existing pack

        Given
        - A pack's release note file path

        When
        - The contribution was made to an existing pack with new entities.

        Then
        - Ensure the RN file template text was modified with the user's input
        """
        contrib_converter.release_notes = (
            "#### IncidentFields\n##### TestingIncidentEntity\n- Testing incident "
            "Entity.\n\n#### Layouts\n##### TestingLayoutEntity\n- Testing Layout "
            "Entity.\n\n#### Scripts\n##### TestingScriptEntity\n- Testing Script "
            "Entity.\n\n"
        )
        contrib_converter.detected_content_items = []

        contrib_converter.replace_RN_template_with_value(NEW_ENTITY_RELEASE_NOTES_COPY)

        assert util_open_file(NEW_ENTITY_RELEASE_NOTES_COPY) == util_open_file(
            EXPECTED_NEW_ENTITY_RELEASE_NOTES
        )

    def test_format_user_input(
        self, mocker: MockerFixture, contrib_converter, rn_file_copy
    ):
        """Test the 'format_user_input' method
        Given
        - A pack's release note file path

        When
        - The contribution was made to an existing pack.

        Then
        - Ensure the dictionary being built contains the relevant data with the content item display name if exists.
        """
        contrib_converter.release_notes = (
            "#### Integrations\n##### CrowdStrikeMalquery\n- release note entry number "
            "#1\n- release note entry number #2\n\n#### Playbooks\n##### "
            "CrowdStrikeMalquery - Multidownload and Fetch\n- changed this playbook\n- "
            "Updated another thing\n\n"
        )
        contrib_converter.detected_content_items = [
            {
                "id": "a8026480-a286-46c7-8c44-b5161a37009d",
                "name": "CrowdStrikeMalquery - Multidownload and Fetch_copy",
                "source_id": "CrowdStrikeMalquery - Multidownload and Fetch",
                "source_name": "CrowdStrikeMalquery - Multidownload and Fetch",
                "source_file_name": "Packs/CrowdStrikeMalquery/Playbooks/CrowdStrikeMalquery_-_GenericPolling_"
                "-_Multidownload_and_Fetch.yml",
            },
            {
                "id": "CrowdStrikeMalquery_copy",
                "name": "CrowdStrikeMalquery_copy",
                "source_id": "CrowdStrikeMalquery",
                "source_name": "CrowdStrikeMalquery",
                "source_file_name": "Packs/CrowdStrikeMalquery/Integrations/CrowdStrikeMalquery/CrowdStrikeMalquery.yml",
            },
        ]
        expected_rn_per_content_item = {
            "CrowdStrike Malquery": "- release note entry number #1\n- release note entry number #2\n",
            "CrowdStrikeMalquery - Multidownload and Fetch": "- changed this playbook\n- Updated another thing\n",
        }
        mocker.patch(
            "demisto_sdk.commands.init.contribution_converter.get_display_name",
            side_effect=[
                "CrowdStrike Malquery",
                "CrowdStrikeMalquery - Multidownload and Fetch",
            ],
        )
        rn_per_content_item = contrib_converter.format_user_input()
        assert expected_rn_per_content_item == rn_per_content_item


class TestReadmes:
    repo_dir_name = "content_repo"
    existing_pack_name = "HelloWorld"
    new_pack_name = "HelloWorldNew"
    existing_integration_name = "HelloWorld"
    new_integration_name = "HelloWorldNew"
    script_name = "script0"
    author = "Kobbi Gal"
    gh_user = "kgal-pan"

    def _get_function_name(self) -> str:
        return inspect.currentframe().f_back.f_code.co_name

    def test_process_existing_pack_existing_integration_readme(
        self, tmp_path: Path, mocker: MockerFixture, git_repo: Repo
    ):
        """
        Test for an existing integration in an existing pack
        to ensure the README is updated correctly.

        The zip and content mapping JSON used in this test were taken from
        the GCP bucket.

        Given
        - A contribution zip file.
        - A contributed content mapping JSON.

        When
        - A new command was added to an existing Pack and Integration

        Then
        - The integration README should be updated with the new command.
        """

        import demisto_sdk.commands.init.contribution_converter as cc

        cc.CONTENT_PATH = git_repo.path

        # Read integration python, yml code and README to create mock integration
        py_code_path = Path(CONTRIBUTION_TESTS, "common", "integration.py")
        py_code = py_code_path.read_text()

        readme_path = Path(CONTRIBUTION_TESTS, "common", PACKS_README_FILE_NAME)
        readme = readme_path.read_text()

        yml_code_path = Path(CONTRIBUTION_TESTS, "common", "integration.yml")
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        git_repo.create_pack(self.existing_pack_name)
        git_repo.packs[0].create_integration(
            name=self.existing_integration_name,
            code=py_code,
            readme=readme,
            yml=yml_code,
        )

        # Read the contribution content mapping
        with open(
            os.path.join(
                CONTRIBUTION_TESTS,
                get_function_name(),
                "existing_pack_add_integration_cmd.json",
            ),
            "r",
        ) as j:
            contributed_content_mapping = json.load(j)
            contributed_content_items = contributed_content_mapping.get(
                self.existing_pack_name, {}
            ).get("detected_content_items", [])

        contribution_temp_dir = tmp_path / "contribution"
        contribution_temp_dir.mkdir()
        # Create a contribution converter instance
        contrib_converter = ContributionConverter(
            name=self.existing_pack_name,
            description="Test contrib-management process_pack",
            contribution=os.path.join(
                CONTRIBUTION_TESTS,
                get_function_name(),
                "existing_pack_add_integration_cmd.zip",
            ),
            author=self.author,
            gh_user=self.gh_user,
            create_new=False,
            pack_dir_name=self.existing_pack_name,
            update_type="revision",
            release_notes="",
            detected_content_items=contributed_content_items,
            working_dir_path=str(contribution_temp_dir),
        )

        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        # Convert the contribution to a pack
        contrib_converter.convert_contribution_to_pack()

        # Copy generated README
        # TODO
        shutil.copyfile(
            src=contribution_temp_dir
            / INTEGRATIONS_DIR
            / self.existing_integration_name
            / INTEGRATIONS_README_FILE_NAME,
            dst=git_repo.packs[0].integrations[0].readme.path,
        )
        modified_readme = Path(contrib_converter.readme_files[0])

        # Ensure that the modified README path is in the content repo
        assert Path(git_repo.path) in modified_readme.parents

        actual_integration_yml_path = Path(
            contribution_temp_dir
            / INTEGRATIONS_DIR
            / self.existing_integration_name
            / f"{self.existing_integration_name}.yml"
        )

        with actual_integration_yml_path.open("r") as stream:
            actual_integration_yml = yaml.load(stream)

        actual_integration_python = Path(
            contribution_temp_dir
            / INTEGRATIONS_DIR
            / self.existing_integration_name
            / f"{self.existing_integration_name}.py"
        )

        # Verify the copied integration Python code, YAML and README are different than the one found in the
        # original integration path
        assert modified_readme.read_text() != readme
        assert "helloworld-new-cmd" in modified_readme.read_text()

        assert actual_integration_yml != yml_code
        assert (
            actual_integration_yml["script"]["commands"][4]["name"]
            == "helloworld-new-cmd"
        )

        assert actual_integration_python.read_text() != py_code
        assert "helloworld-new-cmd" in actual_integration_python.read_text()

    def test_process_existing_pack_new_integration_readme(
        self, tmp_path: Path, git_repo: Repo, mocker: MockerFixture
    ):
        """
        Test for a new integration in an existing pack
        to ensure the README is updated correctly.

        The zip and content mapping JSON used in this test were taken from
        the GCP bucket.

        Given:
        - A contribution zip file.

        When:
        - A new Integration was added to an existing Pack.

        Then:
        - A new Integration README should be generated.
        """

        import demisto_sdk.commands.init.contribution_converter as cc

        cc.CONTENT_PATH = git_repo.path

        git_repo.create_pack(self.existing_pack_name)

        contribution_temp_dir = tmp_path / "contribution"
        contribution_temp_dir.mkdir()
        # Create a contribution converter instance
        contrib_converter = ContributionConverter(
            name=self.existing_pack_name,
            description="Test contrib-management process_pack",
            contribution=os.path.join(
                CONTRIBUTION_TESTS,
                get_function_name(),
                "existing_pack_new_integration.zip",
            ),
            author=self.author,
            gh_user=self.gh_user,
            create_new=False,
            pack_dir_name=self.existing_pack_name,
            update_type="revision",
            release_notes="",
            working_dir_path=str(contribution_temp_dir),
        )

        # Convert the contribution to a pack
        contrib_converter.convert_contribution_to_pack()

        # Check that the generated readme doesn't exist
        # It doesn't exist because it's a new integration
        # and hasn't yet been copied at this point to the content path
        generated_readme = Path(contrib_converter.readme_files[0])
        assert not generated_readme.exists()

    def test_process_new_pack(
        self, tmp_path: Path, git_repo: Repo, mocker: MockerFixture
    ):
        """
        Test for a new Integration added to a new Pack.
        The Pack and the Integration READMEs should be generated.

        Given:
        - A contributon zip.

        When:
        - A new Integration in a new Pack is requested.

        Then:
        - A Pack README should be generated.
        - An Integration README should be generated.
        """

        # Read integration python, yml code and README to create mock integration
        # and Pack
        py_code_path = Path(CONTRIBUTION_TESTS, "common", "integration.py")
        py_code = py_code_path.read_text()

        readme_path = Path(CONTRIBUTION_TESTS, "common", PACKS_README_FILE_NAME)
        readme = readme_path.read_text()

        yml_code_path = Path(CONTRIBUTION_TESTS, "common", "integration.yml")
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        git_repo.create_pack(self.existing_pack_name)
        git_repo.packs[0].create_integration(
            name=self.existing_integration_name,
            code=py_code,
            readme=readme,
            yml=yml_code,
        )

        contribution_temp_dir = tmp_path / "contribution"
        contribution_temp_dir.mkdir()

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        contrib_converter = ContributionConverter(
            name=self.new_pack_name,
            author=self.author,
            description="Test new Integration and Pack",
            contribution=os.path.join(
                CONTRIBUTION_TESTS, get_function_name(), "new_pack_new_integration.zip"
            ),
            gh_user=self.gh_user,
            create_new=True,
            working_dir_path=str(contribution_temp_dir),
            base_dir=git_repo.path,
        )

        # Convert the contribution to a pack
        contrib_converter.convert_contribution_to_pack()

        # Check new Pack README exists
        assert Path(contrib_converter.working_dir_path, PACKS_README_FILE_NAME).exists()

        # Check new Integration README exists
        assert Path(contrib_converter.readme_files[0]).exists()

    def test_process_existing_pack_modified_cmd_conf_added_cmd_up_to_date(
        self, git_repo: Repo, tmp_path: Path, mocker: MockerFixture
    ):
        """
        A test to simulate a contribution for an existing Pack (SplunkPy)
        when the contributed Pack is up-to-date with content latest.

        Given:
        - A content repo.
        - A contribution zip

        When:
        - The contributed content is up-to-date with master.
        - A new configuration option was added.
        - A new command was added.
        - A command argument and output were modified.

        Then:
        - The configuration should be added to the setup section of the README.
        - The added command should be appended to the README.
        - The modified argument and output should be reflected in the README.
        """

        pack_name = integration_name = "SplunkPy"

        pack = git_repo.create_pack(pack_name)

        yml_code_path = Path(
            CONTRIBUTION_TESTS, self._get_function_name(), f"{integration_name}.yml"
        )
        with yml_code_path.open("r") as stream:
            yml_code = yaml.load(stream)

        readme_path = Path(
            CONTRIBUTION_TESTS, self._get_function_name(), INTEGRATIONS_README_FILE_NAME
        )

        pack.create_integration(
            integration_name, yml=yml_code, readme=readme_path.read_text()
        )

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(tools, "is_external_repository", return_value=True)
        mocker.patch.object(
            TextFile,
            "read_from_git_path",
            side_effect=[yml_code_path.read_text(), readme_path.read_text()],
        )

        mapping = Path(
            CONTRIBUTION_TESTS, self._get_function_name(), "content_mapping.json"
        )
        with mapping.open("r") as m:
            detected_content_items = (
                json.load(m).get(pack_name).get("detected_content_items")
            )

        contrib_zip = os.path.join(
            CONTRIBUTION_TESTS, self._get_function_name(), "pack.zip"
        )
        converter = ContributionConverter(
            contribution=contrib_zip,
            create_new=False,
            working_dir_path=str(tmp_path),
            pack_dir_name=pack_name,
            detected_content_items=detected_content_items,
        )

        converter.convert_contribution_to_pack()

        differ = Differ()
        original_readme = readme_path.read_text().splitlines()
        actual_readme = (
            Path(
                converter.working_dir_path,
                INTEGRATIONS_DIR,
                integration_name,
                INTEGRATIONS_README_FILE_NAME,
            )
            .read_text()
            .splitlines()
        )

        added_lines = [
            line
            for line in list(differ.compare(original_readme, actual_readme))
            if line.startswith("+ ")
        ]
        assert (
            "+     | Debug logging enabled | Test configuration | False |"
            in added_lines
        )
        assert (
            "+ | limit | Maximum number of records to return. Default is 100. | Optional | "
            in added_lines
        )
        assert "+ | new_arg | New argument for testing. | Optional | " in added_lines
        assert "+ | Splunk.Test | string | Test output | " in added_lines
        assert "+ ### splunkt-test-cmd" in added_lines
        assert "#### Required Permissions" not in added_lines


class TestFixupDetectedContentItems:
    def test_fixup_detected_content_items_automation(self, tmp_path, git_repo: Repo):
        """
        Scenario: Modify a contribution zip file's content files to use source file info (for relevant files)

        Given
        - The contribution zip file contains a file under the "automation" directory called "automation-ok.yml"
        - The contribution zip contains a file "pack_metadata.json"

        When
        - The id field of "automation-ok.yml" is "ee41bb51-ad90-4740-8824-d364e936200b"
        - The name field of "automation-ok.yml" is "ok"
        - The source id of the content item that "automation-ok.yml" is based on is "TotallyAwesome"
        - The source name of the content item that "automation-ok.yml" is based on is "Totally Awesome"
        - The source file path of the content item that "automation-ok.yml" is base on is
          "Packs/AwesomePack/Scripts/TotallyAwesome/TotallyAwesome.yml"

        Then
        - Ensure that "automation-ok.yml" is renamed to "automation-TotallyAwesome.yml"
        - Ensure the name field of "automation-TotallyAwesome.yml" has been changed to "Totally Awesome"
        - Ensure the id field of "automation-TotallyAwesome.yml" has been changed to "TotallyAwesome"
        """
        path_to_test_zip = os.path.join(
            CONTRIBUTION_TESTS,
            get_function_name(),
            "test_fixup_detected_content_items_automation.zip",
        )
        tmp_destination = tmp_path / "ok_contribution_pack.zip"
        tmp_zip = shutil.copy(path_to_test_zip, tmp_destination)

        file_id = "ee41bb51-ad90-4740-8824-d364e936200b"
        file_name = "ok"
        original_id = "TotallyAwesome"
        original_name = "Totally Awesome"
        detected_content_items = [
            {
                "id": file_id,
                "name": file_name,
                "source_id": original_id,
                "source_name": original_name,
                "source_file_name": "Packs/AwesomePack/Scripts/TotallyAwesome/TotallyAwesome.yml",
            }
        ]
        ryaml = YAML_Handler()
        # verify original zip
        with ZipFile(tmp_zip, "r") as test_zip:
            with test_zip.open("automation/automation-ok.yml", "r") as script_yml:
                data_obj = ryaml.load(script_yml)
                assert data_obj.get("commonfields", {}).get("id", "") == file_id
                assert data_obj.get("name", "") == file_name

        converter = ContributionConverter(
            detected_content_items=detected_content_items,
            contribution=path_to_test_zip,
            working_dir_path=str(tmp_path),
            base_dir=git_repo.path,
        )

        (
            modified_zip_file_path,
            source_mapping,
        ) = converter.fixup_detected_content_items()

        # verify source mapping
        expected_base_name = expected_containing_dir_name = "TotallyAwesome"
        expected_modified_fn = "automation-TotallyAwesome.yml"
        assert expected_modified_fn in source_mapping.keys()
        assert (
            source_mapping.get(expected_modified_fn, {}).get("base_name", "")
            == expected_base_name
        )
        assert (
            source_mapping.get(expected_modified_fn, {}).get("containing_dir_name", "")
            == expected_containing_dir_name
        )

        # verify modified zip
        expected_modified_file_path = "automation/automation-TotallyAwesome.yml"
        with ZipFile(modified_zip_file_path, "r") as modified_zip:
            with modified_zip.open(expected_modified_file_path, "r") as script_yml:
                data_obj = ryaml.load(script_yml)
                assert data_obj.get("commonfields", {}).get("id", "") == original_id
                assert data_obj.get("name", "") == original_name

    def test_fixup_detected_content_items_servicenow(self, tmp_path, git_repo: Repo):
        """
        Scenario: Modify a contribution zip file's content files to use source file info (for relevant files)

        Given
        - The contribution zip file contains a json file which caused an error when trying to write the modified
          version of the file to the modified zip file.

        When
        - The problematic file is "incidenttype-ServiceNowTicket.json"
        - The id field (as contributed) of the problematic file is "ServiceNow Ticket_copy"
        - The name field (as contributed) of "incidenttype-ServiceNowTicket.json" is "ServiceNow Ticket_copy"
        - The source id of the content item that "incidenttype-ServiceNowTicket.json" is based on is "ServiceNow Ticket"
        - The source name of the content item that "incidenttype-ServiceNowTicket.json" is based on is "ServiceNow Ticket"
        - The source file path of the content item that "incidenttype-ServiceNowTicket.json" is based on is
          "Packs/ServiceNow/IncidentTypes/incidenttype-ServiceNowTicket.json"

        Then
        - Ensure that no errors occur when running "fixup_detected_content_items" on the contribution zip (which
          contains the json file that raised errors in the past)
        - Ensure the name field of "incidenttype-ServiceNowTicket.json" has been changed to "Totally Awesome"
        - Ensure the id field of "incidenttype-ServiceNowTicket.json" has been changed to "TotallyAwesome"
        """
        path_to_test_zip = os.path.join(
            CONTRIBUTION_TESTS,
            get_function_name(),
            "uploads_edb61840-4575-406b-93ed-c20d30200c70_pack.zip",
        )
        tmp_destination = tmp_path / "uploads_edb.zip"
        tmp_zip = shutil.copy(path_to_test_zip, tmp_destination)

        detected_content_items = [
            {
                "id": "94f6943b-d3dd-4d5a-85ea-f4e72d46d458",
                "name": "ServiceNowIncidentStatus_copy",
                "source_id": "ServiceNowIncidentStatus",
                "source_name": "ServiceNowIncidentStatus",
                "source_file_name": "Packs/ServiceNow/Scripts/ServiceNowIncidentStatus/ServiceNowIncidentStatus.yml",
            },
            {
                "id": "ServiceNow v2_copy",
                "name": "ServiceNow v2_copy",
                "source_id": "ServiceNow v2",
                "source_name": "ServiceNow v2",
                "source_file_name": "Packs/ServiceNow/Integrations/ServiceNowv2/ServiceNowv2.yml",
            },
            {
                "id": "ServiceNow Ticket_copy",
                "name": "ServiceNow Ticket_copy",
                "source_id": "ServiceNow Ticket",
                "source_name": "ServiceNow Ticket",
                "source_file_name": "Packs/ServiceNow/IncidentTypes/incidenttype-ServiceNowTicket.json",
            },
        ]
        contribution_zip_metadata_id = "f6995816-2013-435f-8121-ca32cc03de52"
        contribution_zip_metadata_name = "Servicenow"

        ryaml = YAML_Handler()
        # verify original zip
        id_as_contributed = [
            content_item.get("id", "") for content_item in detected_content_items
        ]
        names_as_contributed = [
            content_item.get("name", "") for content_item in detected_content_items
        ]
        with ZipFile(tmp_zip, "r") as test_zip:
            for item in test_zip.infolist():
                if item.filename.endswith(".yml"):
                    data_worker = ryaml
                elif item.filename.endswith(".json"):
                    data_worker = json
                else:
                    continue
                with test_zip.open(item, "r") as df:
                    data_obj = data_worker.load(df)
                content_id = (
                    data_obj["commonfields"].get("id", "")
                    if "commonfields" in data_obj.keys()
                    else data_obj.get("id", "")
                )
                content_name = data_obj.get("name", "")
                assert (
                    content_id in id_as_contributed
                    or content_id == contribution_zip_metadata_id
                )
                assert (
                    content_name in names_as_contributed
                    or content_name == contribution_zip_metadata_name
                )

        converter = ContributionConverter(
            detected_content_items=detected_content_items,
            contribution=path_to_test_zip,
            working_dir_path=str(tmp_path),
            base_dir=git_repo.path,
        )

        (
            modified_zip_file_path,
            source_mapping,
        ) = converter.fixup_detected_content_items()
        # # verify source mapping
        expected_modified_file_names = [
            "automation-ServiceNowIncidentStatus.yml",
            "integration-ServiceNowv2.yml",
            "incidenttype-ServiceNowTicket.json",
        ]
        assert set(expected_modified_file_names) == set(source_mapping.keys())

        expected_data_per_file = {
            "automation-ServiceNowIncidentStatus.yml": {
                "base_name": "ServiceNowIncidentStatus",
                "containing_dir_name": "ServiceNowIncidentStatus",
            },
            "incidenttype-ServiceNowTicket.json": {
                "base_name": "ServiceNowTicket.json",
                "containing_dir_name": "IncidentTypes",
            },
            "integration-ServiceNowv2.yml": {
                "base_name": "ServiceNowv2",
                "containing_dir_name": "ServiceNowv2",
            },
        }
        for modified_file_name in expected_modified_file_names:
            expected_base_name = expected_data_per_file[modified_file_name].get(
                "base_name", ""
            )
            expected_containing_dir_name = expected_data_per_file[
                modified_file_name
            ].get("containing_dir_name", "")
            base_name = source_mapping.get(modified_file_name, {}).get("base_name", "")
            containing_dir_name = source_mapping.get(modified_file_name, {}).get(
                "containing_dir_name", ""
            )
            assert base_name == expected_base_name
            assert containing_dir_name == expected_containing_dir_name

        # # verify modified zip
        expected_modified_file_paths_to_source_values = {
            "automation/automation-ServiceNowIncidentStatus.yml": {
                "source_id": "ServiceNowIncidentStatus",
                "source_name": "ServiceNowIncidentStatus",
            },
            "incidenttype/incidenttype-ServiceNowTicket.json": {
                "source_id": "ServiceNow Ticket",
                "source_name": "ServiceNow Ticket",
            },
            "integration/integration-ServiceNowv2.yml": {
                "source_id": "ServiceNow v2",
                "source_name": "ServiceNow v2",
            },
        }
        with ZipFile(modified_zip_file_path, "r") as modified_zip:
            for (
                expected_modified_file_path
            ) in expected_modified_file_paths_to_source_values.keys():
                with modified_zip.open(
                    expected_modified_file_path, "r"
                ) as content_item_file:
                    expected_source_id = expected_modified_file_paths_to_source_values[
                        expected_modified_file_path
                    ].get("source_id", "")
                    expected_source_name = (
                        expected_modified_file_paths_to_source_values[
                            expected_modified_file_path
                        ].get("source_name", "")
                    )
                    if (
                        os.path.splitext(expected_modified_file_path)[-1].lower()
                        == "json"
                    ):
                        data_obj = json.load(content_item_file)
                        assert data_obj.get("id", "") == expected_source_id
                        assert data_obj.get("name", "") == expected_source_name
                    else:
                        data_obj = ryaml.load(content_item_file.read())
                        content_item_id = data_obj.get("commonfields", {}).get(
                            "id", ""
                        ) or data_obj.get("id", "")
                        assert content_item_id == expected_source_id
                        assert data_obj.get("name", "") == expected_source_name

    def test_fixup_detected_content_items_integration(self, repo: Repo, tmp_path: Path):
        """
        Scenario: Modify a contribution zip file's content files to use source file info (for relevant files)

        Given
        - The contribution zip file contains a file under the "integration" directory called
          "integration-AbuseIPDB_copy.yml"
        - The contribution zip contains a file "pack_metadata.json"

        When
        - The id field of "integration-AbuseIPDB_copy.yml" is "AbuseIPDB_copy"
        - The name field of "integration-AbuseIPDB_copy.yml" is "AbuseIPDB_copy"
        - The source id of the content item that "integration-AbuseIPDB_copy.yml" is based on is "AbuseIPDB"
        - The source name of the content item that "integration-AbuseIPDB_copy.yml" is based on is "AbuseIPDB"
        - The source file path of the content item that "integration-AbuseIPDB_copy.yml" is base on is
          "Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.yml"

        Then
        - Ensure that "integration-AbuseIPDB_copy.yml" is renamed to "integration-AbuseDB.yml"
        - Ensure the name field of "integration-AbuseDB.yml" has been changed to "AbuseIPDB"
        - Ensure the id field of "integration-AbuseDB.yml" has been changed to "AbuseIPDB"
        - Ensure the display field of "integration-AbuseDB.yml" has been changed to "AbuseIPDB"
        """
        path_to_test_zip = (
            CONTRIBUTION_TESTS
            / get_function_name()
            / "contentpack-abuse_Contribution_Pack.zip"
        )
        tmp_zip = shutil.copy(str(path_to_test_zip), tmp_path)

        repo.create_pack("AbuseDB").create_integration("AbuseDB")

        file_id = "AbuseIPDB_copy"
        file_name = "AbuseIPDB_copy"
        original_id = "AbuseIPDB"
        original_name = "AbuseIPDB"
        detected_content_items = [
            {
                "id": file_id,
                "name": file_name,
                "source_id": original_id,
                "source_name": original_name,
                "source_file_name": "Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.yml",
            }
        ]
        ryaml = YAML_Handler()
        # verify original zip
        with ZipFile(tmp_zip, "r") as test_zip:
            with test_zip.open(
                "integration/integration-AbuseIPDB_copy.yml", "r"
            ) as integration_yml:
                data_obj = ryaml.load(integration_yml)
                assert data_obj.get("commonfields", {}).get("id", "") == file_id
                assert data_obj.get("name", "") == file_name
                assert data_obj.get("display", "") == file_name

        converter = ContributionConverter(
            detected_content_items=detected_content_items,
            contribution=tmp_zip,
            working_dir_path=str(tmp_path),
            base_dir=repo.path,
        )

        (
            modified_zip_file_path,
            source_mapping,
        ) = converter.fixup_detected_content_items()

        # verify source mapping
        expected_base_name = expected_containing_dir_name = "AbuseDB"
        expected_modified_fn = "integration-AbuseDB.yml"
        assert expected_modified_fn in source_mapping.keys()
        assert (
            source_mapping.get(expected_modified_fn, {}).get("base_name", "")
            == expected_base_name
        )
        assert (
            source_mapping.get(expected_modified_fn, {}).get("containing_dir_name", "")
            == expected_containing_dir_name
        )

        # verify modified zip
        expected_modified_file_path = "integration/integration-AbuseDB.yml"
        with ZipFile(modified_zip_file_path, "r") as modified_zip:
            with modified_zip.open(expected_modified_file_path, "r") as integration_yml:
                data_obj = ryaml.load(integration_yml)
                assert data_obj.get("commonfields", {}).get("id", "") == original_id
                assert data_obj.get("name", "") == original_name
                assert data_obj.get("display", "") == expected_base_name


class TestGetSourceIntegrationDisplayField:
    valid_path = "Packs/FakePack/Integrations/FakeIntegration/FakeIntegration.yml"

    def test_get_source_integration_display_field_valid(self, tmp_path: Path):
        """
        Scenario: Get a source integration's display field value

        Given
        - The path to the source integration yaml file

        When
        - The file is valid
        - The file contains the display field with a value of "Fake Integration"

        Then
        - Ensure calling the 'get_source_integration_display_field' function on the path returns "Fake Integration"
        """

        # setup
        path_to_file = tmp_path
        path_split = self.valid_path.split("/")
        for path_part in path_split[:-1]:
            path_to_file = path_to_file / path_part
            path_to_file.mkdir()
        path_to_file = path_to_file / path_split[-1]

        display_field_value = "Fake Integration"
        data_obj = {"display": display_field_value}
        ryaml = yaml
        with path_to_file.open("w") as df:
            ryaml.dump(data_obj, df)

        # assertions
        converter = ContributionConverter(
            "contrib.zip", "contrib", working_dir_path=str(tmp_path)
        )
        fetched_display_field = converter.get_source_integration_display_field(
            str(path_to_file)
        )
        assert fetched_display_field == display_field_value

    def test_get_source_integration_display_field_valid_but_no_field(
        self, tmp_path: Path
    ):
        """
        Scenario: Get a source integration's display field value

        Given
        - The path to the source integration yaml file

        When
        - The file is valid
        - The file does not contain the "display" field (at the top level)

        Then
        - Ensure calling the 'get_source_integration_display_field' function on the path returns None
        """

        # setup
        path_to_file = tmp_path
        path_split = self.valid_path.split("/")
        for path_part in path_split[:-1]:
            path_to_file = path_to_file / path_part
            path_to_file.mkdir()
        path_to_file = path_to_file / path_split[-1]

        data_obj = {"name": "FakeName"}
        ryaml = yaml
        with path_to_file.open("w") as df:
            ryaml.dump(data_obj, df)

        # assertions
        converter = ContributionConverter(
            "contrib.zip",
            "contrib",
            working_dir_path=str(tmp_path),
        )
        fetched_display_field = converter.get_source_integration_display_field(
            str(path_to_file)
        )
        assert not fetched_display_field

    def test_get_source_integration_display_field_invalid_file_type(
        self, tmp_path: Path
    ):
        """
        Scenario: Get a source integration's display field value

        Given
        - The path to the source integration yaml file

        When
        - The path points to a directory (not a file)

        Then
        - Ensure calling the 'get_source_integration_display_field' function on the path returns None
        """

        # setup
        path_to_file = tmp_path
        path_split = self.valid_path.split("/")
        for path_part in path_split:
            path_to_file = path_to_file / path_part
            path_to_file.mkdir()

        # assertions
        converter = ContributionConverter(
            "contrib.zip",
            "contrib",
            working_dir_path=str(tmp_path),
        )
        fetched_display_field = converter.get_source_integration_display_field(
            str(path_to_file)
        )
        assert not fetched_display_field

    def test_get_source_integration_display_field_invalid_no_file(self, tmp_path: Path):
        """
        Scenario: Get a source integration's display field value

        Given
        - The path to the source integration yaml file

        When
        - The file pointed to by the path does not exist

        Then
        - Ensure calling the 'get_source_integration_display_field' function on the path returns None
        """

        # setup
        path_to_file = tmp_path
        path_split = self.valid_path.split("/")
        for path_part in path_split[:-1]:
            path_to_file = path_to_file / path_part
            path_to_file.mkdir()
        path_to_file = path_to_file / path_split[-1]

        # assertions
        converter = ContributionConverter(
            "contrib.zip",
            "contrib",
            working_dir_path=str(tmp_path),
        )
        fetched_display_field = converter.get_source_integration_display_field(
            str(path_to_file)
        )
        assert not fetched_display_field

    def test_get_source_integration_display_field_invalid_not_yaml(
        self, tmp_path: Path
    ):
        """
        Scenario: Get a source integration's display field value

        Given
        - The path to the source integration file

        When
        - The file is not a yaml (wrong file type extension)
        - The file contains the display field with a value of "Fake Integration"

        Then
        - Ensure calling the 'get_source_integration_display_field' function on the path returns None
        """

        # setup
        path_to_file = tmp_path
        path_split = self.valid_path.split("/")
        for path_part in path_split[:-1]:
            path_to_file = path_to_file / path_part
            path_to_file.mkdir()
        path_to_file = path_to_file / path_split[-1].replace(".yml", ".txt")

        display_field_value = "Fake Integration"
        data_obj = {"display": display_field_value}
        ryaml = yaml
        with path_to_file.open("w") as df:
            ryaml.dump(data_obj, df)

        # assertions
        converter = ContributionConverter(
            "contrib.zip",
            "contrib",
            working_dir_path=str(tmp_path),
        )
        fetched_display_field = converter.get_source_integration_display_field(
            str(path_to_file)
        )
        assert not fetched_display_field
