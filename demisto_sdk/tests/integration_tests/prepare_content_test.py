from pathlib import Path

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
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
                main,
                [PREPARE_CONTENT_CMD, "-i", f"{integration.path}", "-a"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of the '-a' or '-i' parameters must be provided."
            )

            # Verify that not passing either of -a and -i raises an exception.
            result = runner.invoke(
                main,
                [PREPARE_CONTENT_CMD, "-o", "output-path"],
                catch_exceptions=True,
            )
            assert (
                result.exception.args[0]
                == "Exactly one of the '-a' or '-i' parameters must be provided."
            )

            # Verify that specifying an output path of a file and passing multiple inputs raises an exception
            result = runner.invoke(
                main,
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
        self, pack: Pack, collector_key: str
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
        pack.pack_metadata.update({"support": "partner"})
        yml = {
            "commonfields": {"id": name, "version": -1},
            "name": name,
            "display": name,
            "description": description,
            "category": "category",
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
                main,
                [PREPARE_CONTENT_CMD, "-i", f"{integration.path}"],
                catch_exceptions=True,
            )

        unified_integration = get_file(Path(integration.path) / "integration-test.yml")
        assert result.exit_code == 0
        assert (
            unified_integration["detaileddescription"]
            == f"**This integration is supported by Palo Alto Networks.**\n***\n{description}"
        )
