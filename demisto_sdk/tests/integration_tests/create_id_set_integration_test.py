from click.testing import CliRunner

from demisto_sdk.__main__ import main
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions
import json

CREATE_ID_SET_CMD = "create-id-set"


class TestCreateIdSet:  # Use classes to speed up test - multi threaded py pytest
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
        from demisto_sdk.tests.test_files.create_id_set import excluded_items_by_pack, excluded_items_by_type, \
            packs_dependencies_results
        import demisto_sdk.commands.find_dependencies.find_dependencies as find_dependencies
        import demisto_sdk.commands.create_id_set.create_id_set as cis

        pack = repo.create_pack('CreateIdSetPack')
        integration = pack.create_integration('integration')
        integration.create_default_integration()

        with open('demisto_sdk/tests/test_files/create_id_set/test_unfiltered_id_set.json') as id_set_file:
            mock_id_set = json.load(id_set_file)
        mocker.patch.object(find_dependencies, "save_dict_of_sets")
        mocker.patch.object(cis, 'get_id_set', return_value=mock_id_set)
        mocker.patch.object(find_dependencies, "get_packs_dependent_on_given_packs",
                            side_effect=[(packs_dependencies_results.data, {}), ({}, {})])
        mocker.patch.object(cis, 're_create_id_set',
                            return_value=(mock_id_set, excluded_items_by_pack.data, excluded_items_by_type.data))

        with open('/Users/rshalem/dev/demisto/demisto-sdk/demisto_sdk/tests/test_files/create_id_set/excluded_items_by_pack.py', 'w', encoding='utf-8') as f:
            json.dump(excluded_items_by_pack.data, f, ensure_ascii=False, indent=4)

        mocker.patch("click.secho")

        # Change working dir to repo
        with ChangeCWD(integration.repo_path):
            # Circle froze on 3.7 dut to high usage of processing power.
            # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
            # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
            # and not the maximum amount.
            import demisto_sdk.commands.common.update_id_set as uis
            mocker.patch.object(uis, 'cpu_count', return_value=1)
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [CREATE_ID_SET_CMD, '-o', './id_set_result.json', '--marketplace', 'marketplacev2'],
                                   catch_exceptions=False)

            with open('./id_set_result.json') as id_set_result_json:
                id_set_result = json.load(id_set_result_json)
        with open('demisto_sdk/tests/test_files/create_id_set/id_set_after_removal.json') as expected_id_set_json:
            expected_id_set = json.load(expected_id_set_json)

        assert IsEqualFunctions.is_dicts_equal(id_set_result, expected_id_set)
        assert result.exit_code == 0
        assert result.stderr == ""
