import json
import os

from click.testing import CliRunner

from demisto_sdk.__main__ import main
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions

CREATE_ID_SET_CMD = "create-id-set"


class TestCreateIdSet:  # Use classes to speed up test - multi threaded py pytest
    @staticmethod
    def open_json_file(file_path):
        with open(file_path) as json_file:
            return json.load(json_file)

    def test_create_id_set_with_excluded_items(self, mocker, repo):
        """
        Given
            - Running create-id-set command

        When
            - some items should be excluded from the id set duo to mismatch in the marketplaces

        Then
            - Ensure create-id-set passes.
            - Ensure no error occurs.
            - Ensure items are being excluded from the id set
        """
        import demisto_sdk.commands.create_id_set.create_id_set as cis
        import demisto_sdk.commands.find_dependencies.find_dependencies as find_dependencies
        from demisto_sdk.tests.test_files.create_id_set import (
            excluded_items_by_pack, excluded_items_by_type,
            packs_dependencies_results)

        mock_id_set = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/unfiltered_id_set.json')
        id_set_after_manual_removal = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/id_set_after_manual_removal.json')

        mocker.patch.object(cis, 'get_id_set', return_value=mock_id_set)
        mocker.patch.object(find_dependencies, "get_packs_dependent_on_given_packs",
                            side_effect=[(packs_dependencies_results.data, {}), ({}, {})])
        mocker.patch.object(cis, 're_create_id_set', return_value=(id_set_after_manual_removal,
                                                                   excluded_items_by_pack.data,
                                                                   excluded_items_by_type.data))

        # Change working dir to repo
        with ChangeCWD(repo.path):
            # Circle froze on 3.7 dut to high usage of processing power.
            # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
            # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
            # and not the maximum amount.
            import demisto_sdk.commands.common.update_id_set as uis
            mocker.patch.object(uis, 'cpu_count', return_value=1)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [CREATE_ID_SET_CMD, '-o', './id_set_result.json', '--marketplace', 'marketplacev2'],
                                   catch_exceptions=False)

            id_set_result = self.open_json_file('./id_set_result.json')

        expected_id_set = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/id_set_after_removing_dependencies.json')

        assert IsEqualFunctions.is_dicts_equal(id_set_result, expected_id_set)
        assert result.exit_code == 0
        assert result.stderr == ""

    def test_create_id_set_with_excluded_items_mini(self, mocker, repo):
        """
        Given
            - the pack "ExcludedPack" has been removed from the id_set due to marketplace mismatch
            - 2 packs are in the id_set - "PackDependentOnExcludedPack1", "PackDependentOnExcludedPack2"

            - the dependencies are as following:
            1. "PackDependentOnExcludedPack1" is dependent on "ExcludedPack" because the playbook "dummy_playbook" is using it's integration
            2. "PackDependentOnExcludedPack2" is dependent on "PackDependentOnExcludedPack1" because the playbook "dummy_playbook1" is using it's playbook

        When
            - removing dependencies of excluded items from the id set

        Then
            - Ensure create-id-set passes.
            - Ensure no error occurs.
            - Ensure "dummy_playbook" has been removed from the id set
            - Ensure PackDependentOnExcludedPack1 has been removed from the id set since it doesnt have any content items
            - Ensure "dummy_playbook1" has been removed from the id set
            - Ensure "dummy_playbook1" has been removed from "PackDependentOnExcludedPack2" contentItems section.
            - Ensure PackDependentOnExcludedPack2 was not removed from the id set since it still have content items
        """
        import demisto_sdk.commands.create_id_set.create_id_set as cis
        import demisto_sdk.commands.find_dependencies.find_dependencies as find_dependencies
        from demisto_sdk.tests.test_files.create_id_set.mini_id_set import (
            excluded_items_by_pack, excluded_items_by_type,
            packs_dependencies_results)

        mock_id_set = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/unfiltered_id_set.json')
        id_set_after_manual_removal = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/mini_id_set/id_set_after_manual_removal.json')

        mocker.patch.object(cis, 'get_id_set', return_value=mock_id_set)
        mocker.patch.object(find_dependencies, "get_packs_dependent_on_given_packs",
                            side_effect=[(packs_dependencies_results.first_iteration, {}),
                                         (packs_dependencies_results.second_iteration, {}),
                                         ({}, {})])
        mocker.patch.object(cis, 're_create_id_set', return_value=(id_set_after_manual_removal,
                                                                   excluded_items_by_pack.data,
                                                                   excluded_items_by_type.data))

        # Change working dir to repo
        with ChangeCWD(repo.path):
            # Circle froze on 3.7 dut to high usage of processing power.
            # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
            # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
            # and not the maximum amount.
            import demisto_sdk.commands.common.update_id_set as uis
            mocker.patch.object(uis, 'cpu_count', return_value=1)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [CREATE_ID_SET_CMD, '-o', './id_set_result.json', '--marketplace', 'marketplacev2'],
                                   catch_exceptions=False)

            id_set_result = self.open_json_file('./id_set_result.json')

        expected_id_set = self.open_json_file('demisto_sdk/tests/test_files/create_id_set/mini_id_set/id_set_after_removing_dependencies.json')

        assert IsEqualFunctions.is_dicts_equal(id_set_result, expected_id_set)
        assert result.exit_code == 0
        assert result.stderr == ""

    @staticmethod
    def test_excluded_items_contain_aliased_field(mocker, repo: Repo):
        """
        Given
            - An xsoar-only incident field.
            - An incident field with alias of the first field.
            - A mapper using the xsoar-only field.

        When
            creating an ID set for marketplacev2

        Then
            the ID set should not filter the mapper.

        """
        host = {
            'id': 'incident_host',
            'name': 'Host',
            'cliName': 'host',
            'marketplaces': ['xsoar'],
        }
        common_types_pack = repo.create_pack('CommonTypes')
        common_types_pack.pack_metadata.write_json({
            'name': 'CommonTypes',
            'currentVersion': '1.0.0',
            'marketplaces': ['xsoar', 'marketplacev2'],
        })
        common_types_pack.create_incident_field('Host', content=host)
        common_types_pack.create_incident_type('IncidentType')
        host_name = {
            'id': 'incident_hostname',
            'name': 'Host Name',
            'cliName': 'hostname',
            'marketplaces': ['xsoar', 'marketplacev2'],
            'Aliases': [
                {
                    'cliName': 'host',
                    'type': 'shortText',
                    'name': 'Host',
                }
            ]
        }

        core_alert_fields_pack = repo.create_pack('CoreAlertFields')
        core_alert_fields_pack.pack_metadata.write_json({
            'name': 'CoreAlertFields',
            'currentVersion': '1.0.0',
            'marketplaces': ['marketplacev2'],
        })
        core_alert_fields_pack.create_incident_field('HostName', content=host_name)
        mapper = {
            'id': 'Mapper',
            'type': 'mapping-incoming',
            'mapping': {
                'IncidentType': {
                    'dontMapEventToLabels': False,
                    'internalMapping': {
                        'Host': {
                            'simple': 'blabla'
                        },
                    }
                }
            }

        }
        pack = repo.create_pack('MapperPack')
        pack.pack_metadata.write_json({
            'name': 'MapperPack',
            'currentVersion': '1.0.0',
            'marketplaces': ['xsoar', 'marketplacev2'],
        })
        pack.create_mapper('Mapper', content=mapper)

        with ChangeCWD(repo.path):
            # Circle froze on 3.7 dut to high usage of processing power.
            # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
            # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
            # and not the maximum amount.
            import demisto_sdk.commands.common.update_id_set as uis
            mocker.patch.object(uis, 'cpu_count', return_value=1)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [CREATE_ID_SET_CMD, '-o', 'id_set_result.json', '--marketplace', 'marketplacev2'],
                                   catch_exceptions=False)
            assert result.exit_code == 0

        with open(os.path.join(repo.path, 'id_set_result.json')) as file_:
            id_set = json.load(file_)
        assert len(id_set['Mappers']) == 1
