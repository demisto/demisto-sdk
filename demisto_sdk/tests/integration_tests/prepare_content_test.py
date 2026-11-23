import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.common.constants import SUPPORT_LEVEL_HEADER
from demisto_sdk.commands.common.tools import get_file
from TestSuite.pack import Pack
from TestSuite.test_tools import ChangeCWD

PREPARE_CONTENT_CMD = "prepare-content"


class TestPrepareContent:
    def test_prepare_content_inputs(self, repo):
        """
        Given
        - The prepare-content command

        When
        - Passing both the -i and -a parameters.
        - Not passing neither -i nor -a parameters.
        - Providing mulitple inputs with -i and an output path of a file.

        Then
        - Ensure an error message is raised.
        """
        pack = repo.create_pack("PackName")
        integration = pack.create_integration("dummy-integration")
        integration.create_default_integration()

        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)

            # Verify that passing both -a and -i raises an exception.
            result = runner.invoke(
                app,
                [PREPARE_CONTENT_CMD, "-i", f"{integration.path}", "-a"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of '-a' or '-i' must be provided."
            )

            # Verify that not passing either of -a and -i raises an exception.
            result = runner.invoke(
                app,
                [PREPARE_CONTENT_CMD, "-o", "output-path"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of '-a' or '-i' must be provided."
            )

            # Verify that specifying an output path of a file and passing multiple inputs raises an exception
            result = runner.invoke(
                app,
                [
                    PREPARE_CONTENT_CMD,
                    "-i",
                    f"{integration.path},{integration.path}",
                    "-o",
                    "output-path.yml",
                ],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "When passing multiple inputs, the output path should be a directory "
                "and not a file."
            )


class TestPrepareContentIntegration:
    @pytest.mark.parametrize(
        "collector_key", ["isfetchevents", "isfetcheventsandassets"]
    )
    def test_unify_integration__detailed_description_partner_collector(
        self, mocker, pack: Pack, collector_key: str
    ):
        """
        Given:
         - partner pack with an integration that is a collector.

        When:
         - running prepare content on that collector.

        Then:
         - validate that the string "This integration is supported by Palo Alto Networks" is added in to the start
           of the description file.
        """
        name = "test"
        description = f"this is an integration {name}"
        pack.pack_metadata.update(
            {"support": "partner", "created": "2023-10-24T11:49:45Z"}
        )
        yml = {
            "commonfields": {"id": name, "version": -1},
            "name": name,
            "display": name,
            "description": description,
            "category": "category",
            "provider": name,
            "script": {
                "type": "python",
                "subtype": "python3",
                "script": "",
                "isfetchevents": True,
                "commands": [],
            },
            "configuration": [],
            SUPPORT_LEVEL_HEADER: "xsoar",
        }
        integration = pack.create_integration(name, yml=yml, description=description)
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [PREPARE_CONTENT_CMD, "-i", f"{integration.path}"],
                catch_exceptions=True,
            )

        unified_integration = get_file(Path(integration.path) / "integration-test.yml")
        assert result.exit_code == 0
        assert (
            unified_integration["detaileddescription"]
            == f"**This integration is supported by Palo Alto Networks.**\n***\n{description}"
        )


def test_pack_prepare_content(mocker, git_repo, monkeypatch):
    """
    Given:
        - A pack with a pack metadata where some fields are set

    When:
        - Calling prepare-content on the pack

    Then:
        - Ensure the pack is prepared correctly, with the fields from the pack metadata

    """

    pack: Pack = git_repo.create_pack("PackName")
    pack.set_data(hybrid=True, price=3)
    with ChangeCWD(pack.repo_path):
        with TemporaryDirectory() as dir:
            monkeypatch.setenv("DEMISTO_SDK_CONTENT_PATH", dir)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [PREPARE_CONTENT_CMD, "-i", f"{pack.path}"],
                catch_exceptions=True,
            )
    assert result.exit_code == 0
    # unzip the pack
    pack_zip = Path(pack.path) / f"{pack.name}.zip"
    shutil.unpack_archive(pack_zip, Path(pack.path) / "unzipped_pack")
    # check that the pack was prepared correctly
    metadata_path = Path(pack.path) / "unzipped_pack" / "metadata.json"
    assert metadata_path.exists()
    metadata = get_file(metadata_path)
    assert metadata["hybrid"]
    assert metadata["price"] == 3


def test_replace_marketplace_references__end_to_end(git_repo, monkeypatch):
    """
    Given:
        - A pack with various content items (scripts, playbooks, classifiers, integrations) containing the word "Cortex XSOAR" in the yml and code.

    When:
        - Calling prepare-content on the pack with the MarketplaceV2 argument.

    Then:
        - Ensure the word "Cortex XSOAR" is replaced with "Cortex" in the content items.
    """
    original_content = {
        "description": "This is a Cortex XSOAR v1 example.",
        "details": "Cortex XSOAR should be replaced.",
        "nested": {
            "key": "Cortex XSOAR in nested dict",
            "list": ["Cortex XSOAR in list", "Another Cortex XSOAR example"],
        },
    }
    expected_description = "This is a Cortex example."
    expected_details = "Cortex should be replaced."
    expected_nested_key = "Cortex in nested dict"
    expected_nested_list = ["Cortex in list", "Another Cortex example"]

    pack: Pack = git_repo.create_pack("PackName")

    # Update the pack readme
    pack.readme.write_text("Cortex XSOAR in readme")

    # Create a script
    script = pack.create_script("MyScript2")
    script.create_default_script()
    script.yml.update(original_content)
    script.code.write('print("Cortex XSOAR in code")')

    # Create a playbook
    playbook = pack.create_playbook("dummy-playbook")
    playbook.create_default_playbook()
    playbook.yml.update(original_content)

    # Create a classifier
    classifier = pack.create_classifier("dummy-classifier")
    classifier.update(original_content)

    # Create an integration
    integration = pack.create_integration("dummy-integration")
    integration.create_default_integration()
    integration.yml.update(original_content)
    integration.code.write('print("Cortex XSOAR in code")')

    with ChangeCWD(pack.repo_path):
        with TemporaryDirectory() as dir:
            monkeypatch.setenv("DEMISTO_SDK_CONTENT_PATH", dir)
            runner = CliRunner(mix_stderr=False)
            runner.invoke(
                app, [PREPARE_CONTENT_CMD, "-i", f"{pack.path}", "-mp", "marketplacev2"]
            )

    # Unzip the pack
    pack_zip = Path(pack.path) / f"{pack.name}.zip"
    shutil.unpack_archive(pack_zip, Path(pack.path) / "unzipped_pack")

    # Check the readme
    readme_path = Path(pack.path) / "unzipped_pack" / "README.md"
    readme_content = readme_path.read_text()
    assert "Cortex in readme" in readme_content

    # Check script
    script_path = Path(pack.path) / "unzipped_pack" / "Scripts"
    script_yml = get_file(script_path / "script-MyScript2.yml")
    assert script_yml["description"] == expected_description
    assert script_yml["details"] == expected_details
    assert script_yml["nested"]["key"] == expected_nested_key
    assert script_yml["nested"]["list"] == expected_nested_list
    assert 'print("Cortex in code")' in script_yml["script"]

    # Check playbook
    playbook_path = Path(pack.path) / "unzipped_pack" / "Playbooks"
    playbook_yml = get_file(playbook_path / "playbook-dummy-playbook.yml")
    assert playbook_yml["description"] == expected_description
    assert playbook_yml["details"] == expected_details
    assert playbook_yml["nested"]["key"] == expected_nested_key
    assert playbook_yml["nested"]["list"] == expected_nested_list

    # Check classifier
    classifier_path = Path(pack.path) / "unzipped_pack" / "Classifiers"
    classifier_json = get_file(classifier_path / "classifier-dummy-classifier.json")
    assert classifier_json["description"] == expected_description
    assert classifier_json["details"] == expected_details
    assert classifier_json["nested"]["key"] == expected_nested_key
    assert classifier_json["nested"]["list"] == expected_nested_list

    # Check integration
    integration_path = Path(pack.path) / "unzipped_pack" / "Integrations"
    integration_yml = get_file(integration_path / "integration-dummy-integration.yml")
    assert integration_yml["description"] == expected_description
    assert integration_yml["details"] == expected_details
    assert integration_yml["nested"]["key"] == expected_nested_key
    assert integration_yml["nested"]["list"] == expected_nested_list
    assert 'print("Cortex in code")' in integration_yml["script"]["script"]
