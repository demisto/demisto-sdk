import os
from pathlib import Path

from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from TestSuite.test_tools import ChangeCWD

FIND_DEPENDENCIES_CMD = "find-dependencies"

EMPTY_ID_SET = {
    "scripts": [],
    "integrations": [],
    "playbooks": [],
    "TestPlaybooks": [],
    "Classifiers": [],
    "Dashboards": [],
    "IncidentFields": [],
    "IncidentTypes": [],
    "IndicatorFields": [],
    "IndicatorTypes": [],
    "Layouts": [],
    "Reports": [],
    "Widgets": [],
    "Mappers": [],
    "GenericTypes": [],
    "GenericFields": [],
    "GenericModules": [],
    "GenericDefinitions": [],
    "Lists": [],
    "Jobs": [],
    "Wizards": [],
}


def mock_is_external_repo(mocker, is_external_repo_return):
    return mocker.patch(
        "demisto_sdk.commands.find_dependencies.find_dependencies.is_external_repository",
        return_value=is_external_repo_return,
    )


class TestFindDependencies:  # Use classes to speed up test - multi threaded py pytest
    def test_integration_find_dependencies_sanity(self, mocker, repo, monkeypatch):
        """
        Given
        - Valid pack folder

        When
        - Running find-dependencies on it.

        Then
        - Ensure find-dependencies passes.
        - Ensure no error occurs.
        - Ensure debug file is created.
        """

        mock_is_external_repo(mocker, False)
        # Note: if DEMISTO_SDK_ID_SET_REFRESH_INTERVAL is set it can fail the test
        mocker.patch.dict(os.environ, {"DEMISTO_SDK_ID_SET_REFRESH_INTERVAL": "-1"})
        pack = repo.create_pack("FindDependencyPack")
        integration = pack.create_integration("integration")
        integration.create_default_integration()
        mocker.patch(
            "demisto_sdk.commands.find_dependencies.find_dependencies.update_pack_metadata_with_dependencies",
        )

        # Change working dir to repo
        with ChangeCWD(integration.repo_path):
            # Circle froze on 3.7 dut to high usage of processing power.
            # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
            # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
            # and not the maximum amount.
            import demisto_sdk.commands.common.update_id_set as uis

            mocker.patch.object(uis, "cpu_count", return_value=1)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [
                    FIND_DEPENDENCIES_CMD,
                    "-i",
                    str(Path("Packs") / pack._pack_path.name),
                ],
                catch_exceptions=False,
            )
        assert all(
            [
                current_str in result.output
                for current_str in [
                    "# Pack ID: FindDependencyPack",
                    "### Scripts",
                    "### Playbooks",
                    "### Layouts",
                    "### Incident Fields",
                    "### Indicator Types",
                    "### Integrations",
                    "### Incident Types",
                    "### Classifiers",
                    "### Mappers",
                    "### Widgets",
                    "### Dashboards",
                    "### Reports",
                    "### Generic Types",
                    "### Generic Fields",
                    "### Generic Modules",
                    "### Jobs",
                    "All level dependencies are: []",
                ]
            ]
        )
        # last log is regarding all the deps
        assert result.exit_code == 0

    def test_integration_find_dependencies_sanity_with_id_set(self, repo, mocker):
        """
        Given
        - Valid pack folder

        When
        - Running find-dependencies on it.

        Then
        - Ensure find-dependencies passes.
        - Ensure no error occurs.
        """

        mock_is_external_repo(mocker, False)
        pack = repo.create_pack("FindDependencyPack")
        integration = pack.create_integration("integration")
        id_set = EMPTY_ID_SET.copy()
        id_set["integrations"].append(
            {
                "integration": {
                    "name": integration.name,
                    "file_path": integration.path,
                    "commands": [
                        "test-command",
                    ],
                    "pack": "FindDependencyPack",
                }
            }
        )
        repo.id_set.write_json(id_set)

        with ChangeCWD(integration.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [
                    FIND_DEPENDENCIES_CMD,
                    "-i",
                    "Packs/" + Path(repo.packs[0].path).name,
                    "-idp",
                    repo.id_set.path,
                    "--no-update",
                ],
            )

            assert all(
                [
                    current_str in result.output
                    for current_str in [
                        "Found dependencies result for FindDependencyPack pack:",
                        "{}",
                    ]
                ]
            )
            assert result.exit_code == 0

    def test_integration_find_dependencies_not_a_pack(self, repo):
        """
        Given
        - Valid pack folder

        When
        - Running find-dependencies on it.

        Then
        - Ensure find-dependencies passes.
        - Ensure no error occurs.
        """
        pack = repo.create_pack("FindDependencyPack")
        integration = pack.create_integration("integration")
        id_set = EMPTY_ID_SET.copy()
        id_set["integrations"].append(
            {
                "integration": {
                    "name": integration.name,
                    "file_path": integration.path,
                    "commands": [
                        "test-command",
                    ],
                    "pack": "FindDependencyPack",
                }
            }
        )

        repo.id_set.write_json(id_set)

        # Change working dir to repo
        with ChangeCWD(integration.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [
                    FIND_DEPENDENCIES_CMD,
                    "-i",
                    "Packs/NotValidPack",
                    "-idp",
                    repo.id_set.path,
                    "--no-update",
                ],
            )
        assert "Couldn't find any items for pack 'NotValidPack'" in result.output

    def test_integration_find_dependencies_with_dependency(
        self, repo, mocker, monkeypatch
    ):
        """
        Given
        - Valid repo with 2 pack folders where pack2 (script) depends on pack1 (integration).

        When
        - Running find-dependencies on it.

        Then
        - Ensure find-dependencies passes.
        - Ensure dependency is printed.
        """

        mock_is_external_repo(mocker, False)
        pack1 = repo.create_pack("FindDependencyPack1")
        integration = pack1.create_integration("integration1")
        integration.create_default_integration()
        pack2 = repo.create_pack("FindDependencyPack2")
        script = pack2.create_script("script1")
        script.create_default_script()
        id_set = EMPTY_ID_SET.copy()
        id_set["scripts"].append(
            {
                "Script1": {
                    "name": script.name,
                    "file_path": script.path,
                    "deprecated": False,
                    "depends_on": ["test-command"],
                    "pack": "FindDependencyPack2",
                }
            }
        )
        id_set["integrations"].append(
            {
                "integration1": {
                    "name": integration.name,
                    "file_path": integration.path,
                    "commands": [
                        "test-command",
                    ],
                    "pack": "FindDependencyPack1",
                }
            }
        )

        repo.id_set.write_json(id_set)

        # Change working dir to repo
        with ChangeCWD(integration.repo_path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(
                app,
                [
                    FIND_DEPENDENCIES_CMD,
                    "-i",
                    "Packs/" + Path(pack2.path).name,
                    "-idp",
                    repo.id_set.path,
                    # TODO Remove
                    # "--console_log_threshold",
                    # "DEBUG",
                ],
            )

        assert "# Pack ID: FindDependencyPack2" in result.output
        assert "All level dependencies are:" in result.output
        assert (
            "Found dependencies result for FindDependencyPack2 pack:" in result.output
        )
        assert ('"display_name": "FindDependencyPack1"') in result.output
        assert result.exit_code == 0

    def test_wrong_path(self, pack, mocker):
        with ChangeCWD(pack.repo_path):
            runner = CliRunner(mix_stderr=False)
            pack.create_integration()
            path = os.path.join("Packs", Path(pack.path).name, "Integrations")
            result = runner.invoke(app, [FIND_DEPENDENCIES_CMD, "-i", path])
            assert result.exit_code == 1
            assert "must be formatted as 'Packs/<some pack name>" in result.output
