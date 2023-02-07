import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import demisto_sdk.commands.common.tools as tools
import demisto_sdk.commands.common.update_id_set as uis
from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    JOBS_DIR,
    WIZARDS_DIR,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.update_id_set import (
    add_item_to_exclusion_dict,
    does_dict_have_alternative_key,
    find_duplicates,
    get_classifier_data,
    get_correlation_rule_data,
    get_dashboard_data,
    get_fields_by_script_argument,
    get_filters_and_transformers_from_complex_value,
    get_filters_and_transformers_from_playbook,
    get_general_data,
    get_generic_field_data,
    get_generic_module_data,
    get_generic_type_data,
    get_incident_fields_by_playbook_input,
    get_incident_type_data,
    get_indicator_type_data,
    get_layout_data,
    get_layout_rule_data,
    get_mapper_data,
    get_modeling_rule_data,
    get_pack_metadata_data,
    get_parsing_rule_data,
    get_playbook_data,
    get_report_data,
    get_script_data,
    get_trigger_data,
    get_values_for_keys_recursively,
    get_widget_data,
    get_xdrc_template_data,
    get_xsiam_dashboard_data,
    get_xsiam_report_data,
    has_duplicate,
    merge_id_sets,
    process_general_items,
    process_incident_fields,
    process_integration,
    process_jobs,
    process_layoutscontainers,
    process_script,
    process_wizards,
    re_create_id_set,
    should_skip_item_by_mp,
)
from TestSuite.utils import IsEqualFunctions

json = JSON_Handler()


TESTS_DIR = f"{git_path()}/demisto_sdk/tests"


class TestPacksMetadata:
    METADATA_WITH_XSOAR_SUPPORT = {
        "name": "Pack1",
        "support": "xsoar",
        "currentVersion": "1.0.0",
        "author": "Cortex XSOAR",
        "tags": ["Alerts"],
        "useCases": ["Case Management"],
        "categories": ["Endpoint"],
        "marketplaces": ["xsoar", "marketplacev2"],
    }

    METADATA_WITH_PARTNER_SUPPORT = {
        "name": "Pack1",
        "support": "partner",
        "currentVersion": "1.0.0",
        "author": "Some Partner",
        "tags": ["Alerts"],
        "useCases": ["Case Management"],
        "categories": ["Endpoint"],
        "marketplaces": ["xsoar", "marketplacev2"],
    }

    METADATA_WITH_COMMUNITY_SUPPORT = {
        "name": "Pack1",
        "support": "community",
        "currentVersion": "1.0.0",
        "author": "Someone",
        "tags": ["Alerts"],
        "useCases": ["Case Management"],
        "categories": ["Endpoint"],
        "marketplaces": ["xsoar", "marketplacev2"],
    }

    TEST_PACK = [
        (METADATA_WITH_XSOAR_SUPPORT, "Cortex XSOAR", "certified"),
        (METADATA_WITH_PARTNER_SUPPORT, "Some Partner", "certified"),
        (METADATA_WITH_COMMUNITY_SUPPORT, "Someone", ""),
    ]

    @staticmethod
    @pytest.mark.parametrize("metadata_file_content, author, certification", TEST_PACK)
    def test_process_metadata(
        mocker, repo, metadata_file_content, author, certification
    ):
        """
        Given
            - A pack_metadata file for Pack1
        When
            - parsing pack metadata files
        Then
            - parsing all the data from file successfully
        """
        mocker.patch.object(tools, "get_pack_name", return_value="Pack1")
        mocker.patch.object(
            tools,
            "get_mp_types_from_metadata_by_item",
            return_value=["xsoar", "marketplacev2"],
        )

        pack = repo.create_pack("Pack1")
        pack.pack_metadata.write_json(metadata_file_content)

        res = get_pack_metadata_data(pack.pack_metadata.path, print_logs=False)
        result = res.get("Pack1")

        assert "name" in result.keys()
        assert result.get("name") == "Pack1"
        assert result.get("current_version") == "1.0.0"
        assert result.get("author") == author
        assert result.get("certification") == certification
        assert result.get("tags") == ["Alerts"]
        assert result.get("use_cases") == ["Case Management"]
        assert result.get("categories") == ["Endpoint"]
        assert result.get("marketplaces") == ["xsoar", "marketplacev2"]

    @staticmethod
    def test_process_metadata__marketplace_mismatch(mocker):
        """
        Given
            - Pack metadata

        When
            - parsing pack files when there is a mismatch between the item's marketplaces and the current run marketplace.

        Then
            - return empty dict
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=True)
        res = get_pack_metadata_data("", print_logs=False)
        assert res == {}

    @staticmethod
    @pytest.mark.parametrize("print_logs", [True, False])
    def test_process_packs_success(mocker, capsys, repo, print_logs):
        """
        Given
            - A pack metadata file path.
            - Whether to print information to log.
        When
            - Parsing pack metadata files.
        Then
            - Verify output to logs.
        """
        mocker.patch.object(uis, "get_pack_name", return_value="Pack1")
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        pack = repo.create_pack("Pack1")
        pack.pack_metadata.write_json(
            {
                "name": "Pack",
                "currentVersion": "1.0.0",
                "author": "Cortex XSOAR",
                "support": "xsoar",
                "tags": ["Alerts"],
                "useCases": ["Case Management"],
                "categories": ["Endpoint"],
                "marketplaces": ["xsoar", "marketplacev2"],
            }
        )
        pack_metadata_path = pack.pack_metadata.path
        res = get_pack_metadata_data(pack_metadata_path, print_logs)

        captured = capsys.readouterr()

        assert res["Pack1"]["name"] == "Pack"
        assert res["Pack1"]["current_version"] == "1.0.0"
        assert res["Pack1"]["author"] == "Cortex XSOAR"
        assert res["Pack1"]["tags"] == ["Alerts"]
        assert res["Pack1"]["use_cases"] == ["Case Management"]
        assert res["Pack1"]["categories"] == ["Endpoint"]
        assert res["Pack1"]["certification"] == "certified"
        assert res["Pack1"]["marketplaces"] == ["xsoar", "marketplacev2"]

        assert (f"adding {pack_metadata_path} to id_set" in captured.out) == print_logs

    @staticmethod
    def test_process_packs_exception_thrown(capsys, mocker):
        """
        Given
            - A pack metadata file path.
        When
            - Parsing pack metadata files.
        Then
            - Handle the exceptions gracefully.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        with pytest.raises(FileNotFoundError):
            get_pack_metadata_data("Pack_Path", True)
        captured = capsys.readouterr()

        assert "Failed to process Pack_Path, Error:" in captured.out


class TestDuplicates:
    MOCKED_DATA = [
        (
            [
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0",
                    }
                },
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0",
                    }
                },
            ],
            "BluecatAddressManager",
            True,
        ),
        (
            [
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "5.0.0",
                    }
                },
                {
                    "BluecatAddressManager": {
                        "name": "BluecatAddressManager",
                        "file_path": "Integrations/BluecatAddressManager/BluecatAddressManager.yml",
                        "fromversion": "3.1.0",
                        "toversion": "4.0.0",
                    }
                },
            ],
            "BluecatAddressManager",
            False,
        ),
        (
            [
                {
                    "Test3": {
                        "name": "Test3",
                        "file_path": "A",
                        "fromversion": "3.0.0",
                        "toversion": "3.6.0",
                    }
                },
                {
                    "Test3": {
                        "name": "Test3",
                        "file_path": "B",
                        "fromversion": "3.5.0",
                        "toversion": "4.5.0",
                    }
                },
                {
                    "Test3": {
                        "name": "Test3",
                        "file_path": "C",
                        "fromversion": "3.5.2",
                        "toversion": "3.5.4",
                    }
                },
                {
                    "Test3": {
                        "name": "Test3",
                        "file_path": "D",
                        "fromversion": "4.5.0",
                    },
                },
            ],
            "Test3",
            True,
        ),
    ]

    @staticmethod
    @pytest.mark.parametrize(
        "first_pack, second_pack, first_source, second_source, expected",
        [
            (
                "pack1",
                "pack2",
                ("github.com", "demisto", "repo1"),
                ("github.com", "demisto", "repo2"),
                True,
            ),
            (
                "pack1",
                "pack2",
                ("github.com", "demisto", "repo1"),
                ("github.com", "demisto", "repo1"),
                True,
            ),
            (
                "pack1",
                "pack1",
                ("github.com", "demisto", "repo1"),
                ("github.com", "demisto", "repo2"),
                True,
            ),
            (
                "pack1",
                "pack1",
                ("github.com", "demisto", "repo1"),
                ("github.com", "demisto", "repo1"),
                False,
            ),
            (
                "pack1",
                "pack1",
                ("github.com", "demisto", "repo1"),
                ("code.pan.run", "xsoar", "repo1"),
                False,
            ),
            (
                "pack1",
                "pack1",
                ("github.com", "demisto", "repo1"),
                ("code.pan.run", "xsoar", "repo2"),
                True,
            ),
        ],
    )
    def test_has_duplicate(
        first_pack, second_pack, first_source, second_source, expected
    ):
        """
        Given
            - id_set.json with two duplicate layouts of the same type (details), their versions also overrides.
            They are considered duplicates because they have the same name (typeID), their versions override, and they
            are the same kind (details).
            If the pack and source is the same - there are duplicates, otherwise they are not

        When
            - checking for duplicate

        Then
            - Ensure duplicates found depending on the pack and source
        """
        id_set = {"Layouts": []}
        id_set["Layouts"].append(
            {
                "urlRep": {
                    "typeID": "urlRep",
                    "fromVersion": "5.0.0",
                    "kind": "Details",
                    "path": "Layouts/layout-details-urlrep.json",
                    "marketplaces": ["xsoar"],
                    "pack": first_pack,
                    "source": first_source,
                }
            }
        )

        id_set["Layouts"].append(
            {
                "urlRep": {
                    "typeID": "urlRep",
                    "kind": "Details",
                    "path": "Layouts/layout-details-urlrep2.json",
                    "marketplaces": ["xsoar"],
                    "pack": second_pack,
                    "source": second_source,
                }
            }
        )

        # Check for duplicates for existing id-sets,
        # Will not be considered as duplicate when two entities come from the same source
        has_duplicates = has_duplicate(
            id_set["Layouts"], "urlRep", "Layouts", False, is_create_new=False
        )
        assert has_duplicates == expected

        # Check for duplicates for a new id-set,
        # In this case all the examples above should be considered as duplicates
        assert has_duplicate(
            id_set["Layouts"], "urlRep", "Layouts", False, is_create_new=True
        ), "if it's a new pack it is always a duplicate"

    @staticmethod
    def test_has_no_duplicate():
        """
        Given
            - id_set.json with two non duplicate layouts. They have different kind

        When
            - checking for duplicate

        Then
            - Ensure duplicates not found
        """
        id_set = {"Layouts": []}
        id_set["Layouts"].append(
            {
                "urlRep": {
                    "typeID": "urlRep",
                    "kind": "Details",
                    "path": "Layouts/layout-details-urlrep.json",
                }
            }
        )

        id_set["Layouts"].append(
            {
                "urlRep": {
                    "typeID": "urlRep",
                    "kind": "edit",
                    "path": "Layouts/layout-edit-urlrep.json",
                }
            }
        )

        has_duplicates = has_duplicate(id_set["Layouts"], "urlRep", "Layouts", False)
        assert has_duplicates is False

    @staticmethod
    def test_similar_items_on_different_marketplaces():
        """
        Given
            - id_set with two integrations with the same IDs with different marketplaces.

        When
            - checking for duplicate

        Then
            - Ensure duplicates not found
        """

        integrations = [
            {
                "Integ": {
                    "id": "Integ",
                    "name": "Integ",
                    "pack": "Reut",
                    "marketplaces": ["xsoar"],
                }
            },
            {
                "Integ": {
                    "id": "Integ",
                    "name": "Integ",
                    "pack": "Cactus",
                    "marketplaces": ["marketplacev2"],
                }
            },
        ]
        has_duplicates = has_duplicate(
            integrations, "Integ", "integrations", print_logs=False
        )
        assert not has_duplicates


class TestIntegrations:
    INTEGRATION_DATA = {
        "Dummy Integration": {
            "name": "Dummy Integration",
            "display_name": "Palo Alto Networks Cortex XDR - Investigation and Response",
            "file_path": TESTS_DIR
            + "/test_files/DummyPack/Integrations/DummyIntegration/DummyIntegration.yml",
            "fromversion": "4.1.0",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "docker_image": "demisto/python3:3.7.4.977",
            "type": "python3",
            "commands": [
                "xdr-get-incidents",
                "xdr-get-incident-extra-data",
                "xdr-update-incident",
                "xdr-insert-parsed-alert",
                "xdr-insert-cef-alerts",
                "xdr-isolate-endpoint",
                "xdr-unisolate-endpoint",
                "xdr-get-endpoints",
                "xdr-get-distribution-versions",
                "xdr-create-distribution",
                "xdr-get-distribution-url",
                "xdr-get-create-distribution-status",
                "xdr-get-audit-management-logs",
                "xdr-get-audit-agent-reports",
            ],
            "api_modules": ["HTTPFeedApiModule"],
            "classifiers": "dummy-classifier",
            "incident_types": "dummy-incident-type",
            "indicator_fields": "CommonTypes",
            "indicator_types": "CommonTypes",
            "is_fetch": True,
            "mappers": ["dummy-mapper-in", "dummy-mapper-out"],
        }
    }

    UNIFIED_INTEGRATION_DATA = {
        "Dummy Integration": {
            "name": "Dummy Integration",
            "display_name": "Palo Alto Networks Cortex XDR - Investigation and Response",
            "file_path": TESTS_DIR
            + "/test_files/DummyPack/Integrations/integration-DummyIntegration.yml",
            "fromversion": "4.1.0",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "type": "python3",
            "commands": [
                "xdr-get-incidents",
                "xdr-get-incident-extra-data",
                "xdr-update-incident",
                "xdr-insert-parsed-alert",
                "xdr-insert-cef-alerts",
                "xdr-isolate-endpoint",
                "xdr-unisolate-endpoint",
                "xdr-get-endpoints",
                "xdr-get-distribution-versions",
                "xdr-create-distribution",
                "xdr-get-distribution-url",
                "xdr-get-create-distribution-status",
                "xdr-get-audit-management-logs",
                "xdr-get-audit-agent-reports",
            ],
            "api_modules": ["HTTPFeedApiModule"],
            "classifiers": "dummy-classifier",
            "incident_types": "dummy-incident-type",
            "indicator_fields": "CommonTypes",
            "indicator_types": "CommonTypes",
            "is_fetch": True,
            "mappers": ["dummy-mapper-in", "dummy-mapper-out"],
        }
    }

    def test_process_integration__sanity(self, mocker):
        """
        Given
            - A valid script package folder located at Packs/DummyPack/Integrations/DummyIntegration.

        When
            - parsing script files

        Then
            - integration data will be collected properly
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")
        packs = {"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}}

        non_unified_file_path = os.path.join(
            TESTS_DIR, "test_files", "DummyPack", "Integrations", "DummyIntegration"
        )
        res, _ = process_integration(
            non_unified_file_path,
            packs,
            MarketplaceVersions.XSOAR.value,
            print_logs=True,
        )
        assert len(res) == 1
        non_unified_integration_data = res[0]

        unified_file_path = os.path.join(
            TESTS_DIR,
            "test_files",
            "DummyPack",
            "Integrations",
            "integration-DummyIntegration.yml",
        )
        res, _ = process_integration(
            unified_file_path, packs, MarketplaceVersions.XSOAR.value, print_logs=True
        )
        assert len(res) == 1
        unified_integration_data = res[0]

        test_pairs = [
            (non_unified_integration_data, TestIntegrations.INTEGRATION_DATA),
            (unified_integration_data, TestIntegrations.UNIFIED_INTEGRATION_DATA),
        ]

        for returned, constant in test_pairs:
            assert list(returned.keys()) == list(constant.keys())

            const_data = constant.get("Dummy Integration")
            returned_data = returned.get("Dummy Integration")

            assert IsEqualFunctions.is_dicts_equal(
                returned_data, const_data, lists_as_sets=True
            )

    @staticmethod
    def test_process_integration__exception(mocker):
        """
        Given
            - An invalid "integration" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing integration files

        Then
            - an exception will be raised
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "invalid_file_structures", "integration.yml"
        )
        with pytest.raises(Exception):
            process_integration(
                test_file_path,
                {"DummyPack": {}},
                MarketplaceVersions.XSOAR.value,
                print_logs=True,
            )

    @staticmethod
    def test_process_integration__marketplace_mismatch(mocker):
        """
        Given
            - An integration file

        When
            - parsing item files when there is a mismatch between the item's marketplaces and the current run marketplace.

        Then
            - return empty list
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=True)
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "invalid_file_structures", "integration.yml"
        )
        res, _ = process_integration(
            test_file_path,
            {"DummyPack": {}},
            MarketplaceVersions.XSOAR.value,
            print_logs=False,
        )
        assert res == []


class TestScripts:
    SCRIPT_DATA = {
        "DummyScript": {
            "name": "DummyScript",
            "display_name": "DummyScript",
            "file_path": TESTS_DIR + "/test_files/DummyPack/Scripts/DummyScript2.yml",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "fromversion": "5.0.0",
            "docker_image": "demisto/python3:3.7.3.286",
            "type": "python3",
            "tests": ["No test - no need to test widget"],
        }
    }

    SCRIPT_DATA_ALTERNATIVE_TOP_LEVEL = {
        "DummyScript": {
            "name": "DummyScript",
            "display_name": "DummyScript",
            "file_path": TESTS_DIR
            + "/test_files/alternative_meta_fields/Script-top_level_alternative_fields.yml",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "fromversion": "5.0.0",
            "docker_image": "demisto/python3:3.7.3.286",
            "type": "python3",
            "tests": ["No test - no need to test widget"],
            "has_alternative_meta": True,
        }
    }

    SCRIPT_DATA_ALTERNATIVE_SECOND_LEVEL = {
        "DummyScript": {
            "name": "DummyScript",
            "display_name": "DummyScript",
            "file_path": TESTS_DIR
            + "/test_files/alternative_meta_fields/Script-second_level_alternative_fields.yml",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "fromversion": "5.0.0",
            "docker_image": "demisto/python3:3.7.3.286",
            "type": "python3",
            "tests": ["No test - no need to test widget"],
            "has_alternative_meta": True,
        }
    }

    PACK_SCRIPT_DATA = {
        "DummyScript": {
            "name": "DummyScript",
            "display_name": "DummyScript",
            "file_path": "Packs/DummyPack/Scripts/DummyScript/DummyScript.yml",
            "source": ["github.com", "demisto", "demisto-sdk"],
            "marketplaces": ["xsoar"],
            "docker_image": "demisto/python3:3.8.2.6981",
            "type": "python3",
            "pack": "DummyPack",
        }
    }

    @staticmethod
    def test_get_script_data(mocker):
        """
        Test for getting the script data
        """
        file_path = TESTS_DIR + "/test_files/DummyPack/Scripts/DummyScript2.yml"
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")

        data = get_script_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )

        assert list(data.keys()) == list(TestScripts.SCRIPT_DATA.keys())

        const_data = TestScripts.SCRIPT_DATA.get("DummyScript")
        returned_data = data.get("DummyScript")

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_get_script_data_with_alternative_fields_top_level(mocker):
        """
        Given
            - A script file which contains alternative fields in the top level of the yml.

        When
            - parsing scripts files

        Then
            - parsing all the data from file successfully
            - making sure the entry has a field called "has_alternative_meta" set to True
        """
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")

        file_path = (
            TESTS_DIR
            + "/test_files/alternative_meta_fields/Script-top_level_alternative_fields.yml"
        )
        data = get_script_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )

        assert list(data.keys()) == list(
            TestScripts.SCRIPT_DATA_ALTERNATIVE_TOP_LEVEL.keys()
        )

        const_data = TestScripts.SCRIPT_DATA_ALTERNATIVE_TOP_LEVEL.get("DummyScript")
        returned_data = data.get("DummyScript")

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_get_script_data_with_alternative_fields_second_level(mocker):
        """
        Given
            - A script file which contains alternative fields in the second level of the yml.

        When
            - parsing scripts files

        Then
            - parsing all the data from file successfully
            - making sure the entry has a field called "has_alternative_meta" set to True
        """
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")

        file_path = (
            TESTS_DIR
            + "/test_files/alternative_meta_fields/Script-second_level_alternative_fields.yml"
        )
        data = get_script_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )

        assert list(data.keys()) == list(
            TestScripts.SCRIPT_DATA_ALTERNATIVE_SECOND_LEVEL.keys()
        )

        const_data = TestScripts.SCRIPT_DATA_ALTERNATIVE_SECOND_LEVEL.get("DummyScript")
        returned_data = data.get("DummyScript")

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    @pytest.mark.parametrize(
        argnames="code",
        argvalues=[
            "executeCommand('dummy_command', {'key': 'test'});",
            "execute_command('dummy_command', {'key': 'test'});",
            "demisto.executeCommand('dummy_command', {'key': 'test'});",
        ],
    )
    def test_get_script_data_script_executions(repo, code):
        """
        Given
            - A script file which contains different kinds of execute_command call.

        When
            - parsing scripts files

        Then
            - make sure the script_executions was parsed successfully.
        """
        pack = repo.create_pack(name="DummyPack")
        script = pack.create_script(
            name="DummyScript",
            code=code,
            yml={
                "script": code,
                "type": "python",
                "commonfields": {"id": "DummyScript"},
            },
        )
        res, _ = process_script(
            script.path,
            packs={"DummyPack": {}},
            marketplace=MarketplaceVersions.XSOAR.value,
            print_logs=False,
        )
        data = res[0]

        script_executions = data.get("DummyScript", {}).get("script_executions")
        assert script_executions == ["dummy_command"]

    @staticmethod
    def test_process_script__sanity_package(mocker):
        """
        Given
            - An invalid "script" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing script files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "Packs", "DummyPack", "Scripts", "DummyScript"
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        res, _ = process_script(
            test_file_path,
            {"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
            MarketplaceVersions.XSOAR.value,
            print_logs=True,
        )
        assert len(res) == 1
        data = res[0]

        assert list(data.keys()) == list(TestScripts.PACK_SCRIPT_DATA.keys())

        const_data = TestScripts.PACK_SCRIPT_DATA.get("DummyScript")
        returned_data = data.get("DummyScript")

        assert IsEqualFunctions.is_dicts_equal(returned_data, const_data)

    @staticmethod
    def test_process_script__marketplace_mismatch(mocker):
        """
        Given
            - A script file

        When
            - parsing script files when there is a mismatch between the item's marketplaces and the current run marketplace.

        Then
            - return empty list
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "Packs", "DummyPack", "Scripts", "DummyScript"
        )
        res, _ = process_script(
            test_file_path,
            {"DummyPack": {"marketplaces": [MarketplaceVersions.MarketplaceV2.value]}},
            MarketplaceVersions.XSOAR.value,
            print_logs=False,
        )
        assert res == []

    @staticmethod
    def test_process_script__exception(mocker):
        """
        Given
            - An invalid "script" file located at invalid_file_structures where commonfields object is not a dict.

        When
            - parsing script files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "invalid_file_structures", "script.yml"
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        with pytest.raises(Exception):
            process_script(
                test_file_path,
                {"DummyPack": {}},
                MarketplaceVersions.XSOAR.value,
                print_logs=True,
            )


class TestPlaybooks:
    PLAYBOOK_DATA = {
        "name": "Dummy Playbook",
        "display_name": "Dummy Playbook",
        "file_path": TESTS_DIR + "/test_files/DummyPack/Playbooks/DummyPlaybook.yml",
        "source": ["github.com", "demisto", "demisto-sdk"],
        "fromversion": "4.5.0",
        "marketplaces": ["xsoar"],
        "filters": ["isEqualString"],
        "transformers": ["uniq"],
        "implementing_scripts": [
            "XDRSyncScript",
            "StopScheduledTask",
        ],
        "implementing_playbooks": [
            "Palo Alto Networks - Malware Remediation",
            "Calculate Severity - Standard",
        ],
        "command_to_integration": {
            "xdr-update-incident": "",
            "autofocus-sample-analysis": "",
        },
        "tests": ["No Test"],
        "skippable_tasks": [
            "StopScheduledTask",
            "Palo Alto Networks - Malware Remediation",
            "autofocus-sample-analysis",
        ],
    }

    PLAYBOOK_DATA_ALTERNATIVE_FIELDS_TOP_LEVEL = {
        "name": "Dummy Playbook",
        "display_name": "Dummy Playbook",
        "file_path": TESTS_DIR
        + "/test_files/alternative_meta_fields/Playbook-top_level_alternative_fields.yml",
        "source": ["github.com", "demisto", "demisto-sdk"],
        "fromversion": "4.5.0",
        "marketplaces": ["xsoar"],
        "filters": ["isEqualString"],
        "transformers": ["uniq"],
        "implementing_scripts": ["StopScheduledTask", "XDRSyncScript"],
        "implementing_playbooks": [
            "Calculate Severity - Standard",
            "Palo Alto Networks - Malware Remediation",
        ],
        "command_to_integration": {
            "xdr-update-incident": "",
            "autofocus-sample-analysis": "",
        },
        "tests": ["No Test"],
        "skippable_tasks": [
            "StopScheduledTask",
            "Palo Alto Networks - Malware Remediation",
            "autofocus-sample-analysis",
        ],
        "has_alternative_meta": True,
    }

    PLAYBOOK_DATA_ALTERNATIVE_FIELDS_SECOND_LEVEL = {
        "name": "Dummy Playbook",
        "display_name": "Dummy Playbook",
        "file_path": TESTS_DIR
        + "/test_files/alternative_meta_fields/Playbook-second_level_alternative_fields.yml",
        "source": ["github.com", "demisto", "demisto-sdk"],
        "marketplaces": ["xsoar"],
        "fromversion": "4.5.0",
        "filters": ["isEqualString"],
        "transformers": ["uniq"],
        "implementing_scripts": [
            "XDRSyncScript",
            "StopScheduledTask",
        ],
        "implementing_playbooks": [
            "Calculate Severity - Standard",
            "Palo Alto Networks - Malware Remediation",
        ],
        "command_to_integration": {
            "xdr-update-incident": "",
            "autofocus-sample-analysis": "",
        },
        "tests": ["No Test"],
        "skippable_tasks": [
            "StopScheduledTask",
            "Palo Alto Networks - Malware Remediation",
            "autofocus-sample-analysis",
        ],
        "has_alternative_meta": True,
    }

    @staticmethod
    def test_get_playbook_data(mocker):
        """
        Test for getting the playbook data
        """
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")
        file_path = TESTS_DIR + "/test_files/DummyPack/Playbooks/DummyPlaybook.yml"
        data = get_playbook_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )["Dummy Playbook"]
        assert IsEqualFunctions.is_dicts_equal(
            data, TestPlaybooks.PLAYBOOK_DATA, lists_as_sets=True
        )

    @staticmethod
    def test_get_playbook_data_with_alternative_fields_top_level(mocker):
        """
        Given
            - A playbook file which contains alternative fields in the top level of the yml.

        When
            - parsing playbooks files

        Then
            - parsing all the data from file successfully
            - making sure the entry has a field called "has_alternative_meta" set to True
        """
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")
        file_path = (
            TESTS_DIR
            + "/test_files/alternative_meta_fields/Playbook-top_level_alternative_fields.yml"
        )
        data = get_playbook_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )["Dummy Playbook"]

        assert IsEqualFunctions.is_dicts_equal(
            data,
            TestPlaybooks.PLAYBOOK_DATA_ALTERNATIVE_FIELDS_TOP_LEVEL,
            lists_as_sets=True,
        )

    @staticmethod
    def test_get_playbook_data_with_alternative_fields_second_level(mocker):
        """
        Given
            - A playbook file which contains alternative fields in the second level of the yml.

        When
            - parsing playbooks files

        Then
            - parsing all the data from file successfully
            - making sure the entry has a field called "has_alternative_meta" set to True
        """
        mocker.patch.object(tools, "get_pack_name", return_value="DummyPack")
        file_path = (
            TESTS_DIR
            + "/test_files/alternative_meta_fields/Playbook-second_level_alternative_fields.yml"
        )
        data = get_playbook_data(
            file_path,
            packs={"DummyPack": {"marketplaces": [MarketplaceVersions.XSOAR.value]}},
        )["Dummy Playbook"]
        assert IsEqualFunctions.is_dicts_equal(
            data,
            TestPlaybooks.PLAYBOOK_DATA_ALTERNATIVE_FIELDS_SECOND_LEVEL,
            lists_as_sets=True,
        )

    @staticmethod
    def test_get_playbook_data_2():
        """
        Given
            - A playbook file called playbook-with-incident-fields.yml

        When
            - parsing playbook files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f"{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/playbook-with-incident-fields.yml"
        result = get_playbook_data(test_dir, packs={"DummyPack": {}})
        result = result.get("Arcsight - Get events related to the Case")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "implementing_scripts" in result.keys()
        assert "command_to_integration" in result.keys()
        assert "tests" in result.keys()
        assert "incident_fields" in result.keys()
        assert "indicator_fields" in result.keys()

    @staticmethod
    def test_get_playbook_data_no_fields(mocker):
        """
        Given
            - A playbook file called playbook-no-incident-fields.yml without any
                incident or indicator fields that it depends on.

        When
            - parsing playbook files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f"{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/playbook-no-incident-fields.yml"
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        result = get_playbook_data(test_dir, packs={"DummyPack": {}})
        result = result.get("Arcsight - Get events related to the Case")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "implementing_scripts" in result.keys()
        assert "command_to_integration" in result.keys()
        assert "tests" in result.keys()
        assert "incident_fields" not in result.keys()
        assert "indicator_fields" not in result.keys()

    @staticmethod
    def test_process_playbook__exception(mocker):
        """
        Given
            - An invalid "playbook" file located at invalid_file_structures where tasks object is not a dict.

        When
            - parsing playbook files

        Then
            - an exception will be raised
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "invalid_file_structures", "playbook.yml"
        )
        with pytest.raises(Exception):
            process_general_items(
                test_file_path,
                {"DummyPack": {}},
                MarketplaceVersions.XSOAR.value,
                True,
                (FileType.PLAYBOOK,),
                get_playbook_data,
            )

    @staticmethod
    def test_get_playbook_data_bad_graph():
        """
        Given
            - A playbook file called playbook-invalid-bad-graph.yml:
                - task 1 point to non-existing task
                - task 2 is not connected

        When
            - parsing playbook files

        Then
            - parsing flow graph from file successfully (only tasks 0 and 1 will be in the graph)
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "playbook-invalid-bad-graph.yml"
        )
        result = get_playbook_data(test_file_path, packs={"DummyPack": {}})
        playbook_data = result.get("InvalidPlaybook-BadGraph", {})
        assert playbook_data.get("name") == "InvalidPlaybook-BadGraph"
        assert playbook_data.get("display_name") == "InvalidPlaybook-BadGraph"
        assert playbook_data.get("command_to_integration", {}).get("ip") == ""
        assert playbook_data.get("command_to_integration", {}).get("domain") == ""
        assert "domain" in playbook_data.get("skippable_tasks", [])
        assert "ip" not in playbook_data.get("skippable_tasks", [])

    @staticmethod
    def test_get_playbook_data_bad_graph_2():
        """
        Given
            - A playbook file called playbook-invalid-bad-graph_2.yml:
                - starttaskid=5 but task 5 does not exist

        When
            - parsing playbook files

        Then
            - parsing flow graph from file successfully (no actual tasks will be in the graph)
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "playbook-invalid-bad-graph_2.yml"
        )
        result = get_playbook_data(test_file_path, packs={"DummyPack": {}})
        playbook_data = result.get("InvalidPlaybook-BadGraph", {})
        assert playbook_data.get("name") == "InvalidPlaybook-BadGraph"
        assert playbook_data.get("display_name") == "InvalidPlaybook-BadGraph"
        assert playbook_data.get("command_to_integration", {}).get("ip") == ""
        assert playbook_data.get("command_to_integration", {}).get("domain") == ""
        # domain task is marked as skippable so it will be included regardless to the graph.
        assert "domain" in playbook_data.get("skippable_tasks", [])
        assert len(playbook_data.get("skippable_tasks", [])) == 1

    @staticmethod
    def test_get_filters_from_playbook_tasks():
        """
        Given
        - playbook with one task and 3 filters: isEqualString, isEqualString and StringContainsArray

        When
        - parsing filters from the playbook

        Then
        - parsing 2 filters successfully
        - isEqualString filter shows once

        """
        data = {
            "tasks": {
                "0": {
                    "scriptarguments": {
                        "value": {
                            "complex": {
                                "filters": [
                                    [{"operator": "isEqualString"}],
                                    [{"operator": "isEqualString"}],
                                    [{"operator": "StringContainsArray"}],
                                ]
                            }
                        }
                    }
                }
            }
        }
        _, filters = get_filters_and_transformers_from_playbook(data)
        assert len(filters) == 2
        assert "isEqualString" in filters
        assert "StringContainsArray" in filters

    @staticmethod
    def test_get_transformers_from_playbook_tasks():
        """
        Given
        - playbook with one task and 3 transformers: Length, Length and toUpperCase

        When
        - parsing transformers from the playbook

        Then
        - parsing 2 transformers successfully
        - Length transformer shows once

        """
        data = {
            "tasks": {
                "0": {
                    "scriptarguments": {
                        "value": {
                            "complex": {
                                "transformers": [
                                    {"operator": "toUpperCase"},
                                    {"operator": "Length"},
                                    {"operator": "Length"},
                                ]
                            }
                        }
                    }
                }
            }
        }
        transformers, _ = get_filters_and_transformers_from_playbook(data)
        assert len(transformers) == 2
        assert "toUpperCase" in transformers
        assert "Length" in transformers

    @staticmethod
    def test_get_transformers_from_playbook_condition_task():
        """
        Given
        - playbook with one condition task with toUpperCase transformer

        When
        - parsing transformers from the playbook

        Then
        - parsing toUpperCase transformer successfully

        """
        data = {
            "tasks": {
                "0": {
                    "type": "condition",
                    "conditions": [
                        {
                            "condition": [
                                [
                                    {
                                        "left": {
                                            "value": {
                                                "complex": {
                                                    "transformers": [
                                                        {"operator": "toUpperCase"}
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                ]
                            ]
                        }
                    ],
                }
            }
        }
        transformers, _ = get_filters_and_transformers_from_playbook(data)
        assert transformers == ["toUpperCase"]

    @staticmethod
    def test_get_transformers_and_filters_from_playbook_two_conditions_task():
        """
        Given
        - playbook with one task that contains 2 conditions: one with filter and one with transformer

        When
        - parsing transformers and filters from the playbook

        Then
        - parsing toUpperCase transformer successfully
        - parsing isEqualString filter successfully


        """
        data = {
            "tasks": {
                "0": {
                    "type": "condition",
                    "conditions": [
                        {
                            "condition": [
                                [
                                    {
                                        "left": {
                                            "value": {
                                                "complex": {
                                                    "filters": [
                                                        [{"operator": "isEqualString"}]
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                ]
                            ]
                        },
                        {
                            "condition": [
                                [
                                    {
                                        "right": {
                                            "value": {
                                                "complex": {
                                                    "transformers": [
                                                        {"operator": "toUpperCase"}
                                                    ]
                                                }
                                            }
                                        }
                                    }
                                ]
                            ]
                        },
                    ],
                }
            }
        }

        transformers, filters = get_filters_and_transformers_from_playbook(data)
        assert transformers == ["toUpperCase"]
        assert filters == ["isEqualString"]

    @staticmethod
    def test_get_transformers_from_playbook_inputs(mocker):
        """
        Given
        - playbook with 2 inputs that using Length and toUpperCase transformers

        When
        - parsing transformers from the playbook inputs

        Then
        - parsing 2 transformers successfully

        """
        data = {
            "inputs": [
                {"value": {"complex": {"transformers": [{"operator": "toUpperCase"}]}}},
                {"value": {"complex": {"transformers": [{"operator": "Length"}]}}},
            ]
        }
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        transformers, _ = get_filters_and_transformers_from_playbook(data)
        assert len(transformers) == 2
        assert "toUpperCase" in transformers
        assert "Length" in transformers


class TestLayouts:
    @staticmethod
    def test_process_layouts__sanity(mocker):
        """
        Given
            - A layout file called layout-to-test.json

        When
            - parsing layout files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "layout-to-test.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_general_items(
            test_file,
            {"DummyPack": {}},
            MarketplaceVersions.XSOAR.value,
            True,
            (FileType.LAYOUT,),
            get_layout_data,
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("urlRep")
        assert "kind" in result.keys()
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "fromversion" in result.keys()
        assert "toversion" in result.keys()
        assert "file_path" in result.keys()
        assert "typeID" in result.keys()
        assert "incident_and_indicator_types" in result.keys()
        assert "incident_and_indicator_fields" in result.keys()

    @staticmethod
    def test_process_layouts__no_incident_types_and_fields(mocker):
        """
        Given
            - A layout file called layout-to-test.json that doesnt have related incident fields and indicator fields

        When
            - parsing layout files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "layout-to-test-no-types-fields.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_general_items(
            test_file,
            {"DummyPack": {}},
            MarketplaceVersions.XSOAR.value,
            False,
            (FileType.LAYOUT,),
            get_layout_data,
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("urlRep")
        assert "kind" in result.keys()
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "fromversion" in result.keys()
        assert "toversion" in result.keys()
        assert "file_path" in result.keys()
        assert "typeID" in result.keys()
        assert "incident_and_indicator_types" in result.keys()
        assert "incident_and_indicator_fields" not in result.keys()

    @staticmethod
    def test_process_layoutscontainer__sanity(mocker):
        """
        Given
            - A layoutscontainer file called layoutscontainer-to-test.json
        When
            - parsing layoutscontainer files
        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "layoutscontainer-to-test.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_layoutscontainers(
            test_file, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("layouts_container_test")
        assert "detailsV2" in result.keys()
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "group" in result.keys()
        assert "fromversion" in result.keys()
        assert "toversion" in result.keys()
        assert "file_path" in result.keys()
        assert "incident_and_indicator_types" in result.keys()
        assert "incident_and_indicator_fields" in result.keys()

    LAYOUT_TYPE_TO_MARKETPLACE_TESTS = [
        ("indicator", MarketplaceVersions.XSOAR.value, False),
        ("indicator", MarketplaceVersions.MarketplaceV2.value, False),
        ("incident", MarketplaceVersions.XSOAR.value, False),
        ("incident", MarketplaceVersions.MarketplaceV2.value, False),
    ]

    @staticmethod
    @pytest.mark.parametrize(
        "layout_type, marketplace, should_exclude", LAYOUT_TYPE_TO_MARKETPLACE_TESTS
    )
    def test_process_layoutscontainer__excluding_from_marketplace_by_layout_type(
        layout_type, marketplace, should_exclude, repo
    ):
        """
        Given
            - A layoutcontainer of layout_type (incident/indicator)
        When
            - parsing a layoutcontainer file.
        Then
            - exclude incident layout from marketplace v2
            - accept all other cases
        """
        pack = repo.create_pack(name=f"DummyPack-{layout_type}")
        layout = pack.create_layoutcontainer(
            "Reut",
            {
                "id": "Reut",
                "group": layout_type,
                "detailsV2": {},
                "marketplaces": ["xsoar", "marketplacev2"],
            },
        )

        res, excluded_items = process_layoutscontainers(
            layout.path, {pack.name: {}}, marketplace, True
        )

        if should_exclude:
            assert not res
            assert excluded_items
            assert pack.name in excluded_items
            assert ("layoutscontainer", "Reut") in excluded_items[pack.name]
        else:
            assert len(res) == 1
            assert res[0].get("Reut")
            assert not excluded_items

    @staticmethod
    def test_process_layoutscontainer__marketplace_mismatch(repo):
        """
        Given
            - An indicator layoutcontainer
        When
            - parsing a layoutcontainer file when there is a mismatch between the item's marketplaces and the current run marketplace.
        Then
            - return empty list
        """
        pack = repo.create_pack(name="DummyPack")
        layout = pack.create_layoutcontainer(
            "Itay",
            {
                "id": "Itay",
                "group": "indicator",
                "detailsV2": {},
                "marketplaces": ["marketplacev2"],
            },
        )
        res, excluded_items = process_layoutscontainers(
            layout.path, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True
        )
        assert res == []
        assert excluded_items
        assert "DummyPack" in excluded_items
        assert ("layoutscontainer", "Itay") in excluded_items["DummyPack"]


class TestIncidentFields:
    @staticmethod
    def test_process_incident_fields__sanity(mocker):
        """
        Given
            - An incident field file called incidentfield-to-test.json

        When
            - parsing incident field files

        Then
            - parsing all the data from file successfully
        """
        test_dir = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "incidentfield-to-test.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_incident_fields(
            test_dir, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True, []
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("incidentfield-test")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "toversion" in result.keys()
        assert "incident_types" in result.keys()
        assert "scripts" in result.keys()
        assert "aliases" in result.keys()

    @staticmethod
    def test_process_incident_fields_with_alternative_fields(mocker):
        """
        Given
                - An incident-field file which contains alternative fields

            When
                - parsing incident-field files

            Then
                - parsing all the data from file successfully
                - making sure the entry has a field called "has_alternative_meta"
        """
        test_dir = os.path.join(
            git_path(),
            "demisto_sdk",
            "tests",
            "test_files",
            "alternative_meta_fields",
            "incidentfield-top_level_alternative_fields.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_incident_fields(
            test_dir, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True, []
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("incidentfield_upload_id")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" in result.keys()
        assert "has_alternative_meta" in result.keys()

    @staticmethod
    def test_process_incident_fields__no_types_scripts(mocker):
        """
        Given
            - An incident field file called incidentfield-to-test-no-types_scripts.json with no script or incident type
            related to it

        When
            - parsing incident field files

        Then
            - parsing all the data from file successfully
        """
        test_dir = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "incidentfield-to-test-no-types_scripts.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_incident_fields(
            test_dir, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True, []
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("incidentfield-test")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "toversion" in result.keys()
        assert "incident_types" not in result.keys()
        assert "scripts" not in result.keys()

    @staticmethod
    def test_process_incident_fields__marketplace_mismatch(mocker):
        """
        Given
            - An incident field file
        When
            - parsing An incident field files when there is a mismatch between the item's marketplaces and the current run marketplace.
        Then
            - return empty list
        """
        test_dir = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "incidentfield-to-test-no-types_scripts.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=True)
        res, _ = process_incident_fields(
            test_dir, {"DummyPack": {}}, MarketplaceVersions.XSOAR.value, True, []
        )
        assert res == []


class TestIndicatorType:
    @staticmethod
    def test_process_indicator_type__sanity(mocker):
        """
        Given
            - An indicator type file called reputation-indicatortype.json.

        When
            - parsing indicator type files

        Then
            - parsing all the data from file successfully
        """
        test_dir = f"{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/reputation-indicatortype.json"
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        result = get_indicator_type_data(
            test_dir, [{"integration": {"commands": ["ip"]}}]
        )
        result = result.get("indicator-type-dummy")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "integrations" in result.keys()
        assert "scripts" in result.keys()
        assert "dummy-script" in result.get("scripts")
        assert "dummy-script-2" in result.get("scripts")
        assert "dummy-script-3" in result.get("scripts")

    @staticmethod
    def test_get_indicator_type_data_no_integration_no_scripts():
        """
        Given
            - An indicator type file called reputation-indicatortype_no_script_no_integration.json without any
                integrations or scripts that it depends on.

        When
            - parsing indicator type files

        Then
            - parsing all the data from file successfully
        """
        test_dir = (
            f"{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/"
            f"reputation-indicatortype_no_script_no_integration.json"
        )

        result = get_indicator_type_data(test_dir, [])
        result = result.get("indicator-type-dummy")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "integrations" not in result.keys()
        assert "scripts" not in result.keys()


class TestIncidentTypes:
    @staticmethod
    def test_get_incident_type_data__sanity():
        """
        Given
            - An incident type file called incidenttype-to-test.json

        When
            - parsing incident type files

        Then
            - parsing all the data from file successfully
        """
        test_file = f"{git_path()}/demisto_sdk/commands/create_id_set/tests/test_data/incidenttype-to-test.json"

        res = get_incident_type_data(test_file)
        result = res.get("dummy incident type")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "playbooks" in result.keys()
        assert "scripts" in result.keys()

    @staticmethod
    def test_get_incident_type_data__no_playbooks_scripts():
        """
        Given
            - An incident type file called incidenttype-to-test-no-playbook-script.json with no script or playbook
            related to it

        When
            - parsing incident type files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "incidenttype-to-test-no-playbook-script.json",
        )

        res = get_incident_type_data(test_file)
        result = res.get("dummy incident type")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "playbooks" not in result.keys()
        assert "scripts" not in result.keys()


class TestClassifiers:
    @staticmethod
    def test_process_classifiers__no_types_scripts(mocker):
        """
        Given
            - An classifier file called classifier-to-test-no-incidenttypes.json with incident type
            related to it

        When
            - parsing classifier files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-to-test-no-incidenttypes.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res = get_classifier_data(test_file)
        result = res.get("dummy classifier")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" not in result.keys()
        assert "incident_fields" not in result.keys()


class TestMappers:
    @staticmethod
    def test_process_mappers__sanity():
        """
        Given
            - A mapper file called classifier-mapper-to-test.json

        When
            - parsing mapper files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-mapper-to-test.json",
        )

        res = get_mapper_data(test_file)
        result = res.get("dummy mapper")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" in result.keys()
        assert "incident_fields" in result.keys()
        assert "dummy incident type" in result["incident_types"]
        assert "dummy incident type 1" in result["incident_types"]
        assert "dummy incident type 2" in result["incident_types"]
        assert "dummy incident field" in result["incident_fields"]
        assert "dummy incident field 1" in result["incident_fields"]
        assert "dummy incident field 2" in result["incident_fields"]
        assert "dummy incident field 3" in result["incident_fields"]
        assert "occurred" not in result["incident_fields"]

    @staticmethod
    def test_process_mappers_alternative_field():
        """
        Given
            - A mapper file which contains alternative fields

        When
            - parsing mapper files

        Then
            - parsing all the data from file successfully
            - making sure the entry has a field called "has_alternative_meta"
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "tests",
            "test_files",
            "alternative_meta_fields",
            "mapper-top_level_alternative_name.json",
        )

        res = get_mapper_data(test_file)
        result = res.get("dummy mapper")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" in result.keys()
        assert "incident_fields" in result.keys()
        assert "dummy incident type" in result["incident_types"]
        assert "dummy incident type 1" in result["incident_types"]
        assert "dummy incident type 2" in result["incident_types"]
        assert "dummy incident field" in result["incident_fields"]
        assert "dummy incident field 1" in result["incident_fields"]
        assert "dummy incident field 2" in result["incident_fields"]
        assert "dummy incident field 3" in result["incident_fields"]
        assert "occurred" not in result["incident_fields"]
        assert "has_alternative_meta" in result.keys()

    @staticmethod
    def test_process_mappers__no_types_fields():
        """
        Given
            - An mapper file called classifier-mapper-to-test-no-types-fields.json with incident type
            related to it

        When
            - parsing mapper files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-mapper-to-test-no-types-fields.json",
        )

        res = get_mapper_data(test_file)
        result = res.get("dummy mapper")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" not in result.keys()
        assert "incident_fields" not in result.keys()

    @staticmethod
    def test_process_mappers__outgoing_mapper(mocker):
        """
        Given
            - A mapper file called ServiceNow-outgoing-mapper with incident fields related to it

        When
            - running get_mapper_data

        Then
            - Validating parsing all the incident fields from the simple key.
        """
        outgoing_mapper_snow = {
            "defaultIncidentType": "ServiceNow Ticket",
            "description": "Maps outgoing ServiceNow incident Fields.",
            "feed": False,
            "fromVersion": "6.0.0",
            "id": "ServiceNow-outgoing-mapper",
            "marketplaces": ["xsoar"],
            "mapping": {
                "ServiceNow Ticket": {
                    "dontMapEventToLabels": False,
                    "internalMapping": {
                        "category": {"complex": None, "simple": "servicenowcategory"},
                        "closed_at": {
                            "complex": {
                                "accessor": "",
                                "filters": [
                                    [
                                        {
                                            "ignoreCase": False,
                                            "left": {
                                                "isContext": True,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "closed",
                                                },
                                            },
                                            "operator": "isAfter",
                                            "right": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "0001-01-01T00:00:00Z",
                                                },
                                            },
                                        }
                                    ]
                                ],
                                "root": "closed",
                                "transformers": [],
                            },
                            "simple": "",
                        },
                        "description": {"complex": None, "simple": "details"},
                        "escalation": {
                            "complex": None,
                            "simple": "servicenowescalation",
                        },
                        "impact": {"complex": None, "simple": "servicenowimpact"},
                        "notify": {"complex": None, "simple": "servicenownotify"},
                        "priority": {"complex": None, "simple": "servicenowpriority"},
                        "resolved_at": {
                            "complex": {
                                "accessor": "",
                                "filters": [
                                    [
                                        {
                                            "ignoreCase": False,
                                            "left": {
                                                "isContext": True,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "closed",
                                                },
                                            },
                                            "operator": "isAfter",
                                            "right": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "0001-01-01T00:00:00Z",
                                                },
                                            },
                                        }
                                    ]
                                ],
                                "root": "closed",
                                "transformers": [],
                            },
                            "simple": "",
                        },
                        "severity": {
                            "complex": {
                                "accessor": "",
                                "filters": [],
                                "root": "severity",
                                "transformers": [
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "3 - Low",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "0",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "3 - Low",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "0.5",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "3 - Low",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "1",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "2 - Medium",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "2",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "1 - High",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "3",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                    {
                                        "args": {
                                            "limit": {
                                                "isContext": False,
                                                "value": None,
                                            },
                                            "replaceWith": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "1 - High",
                                                },
                                            },
                                            "toReplace": {
                                                "isContext": False,
                                                "value": {
                                                    "complex": None,
                                                    "simple": "4",
                                                },
                                            },
                                        },
                                        "operator": "replace",
                                    },
                                ],
                            },
                            "simple": "",
                        },
                        "short_description": {"complex": None, "simple": "name"},
                        "sla_due": {
                            "complex": None,
                            "simple": "remediationsla.dueDate",
                        },
                        "state": {"complex": None, "simple": "servicenowstate"},
                        "subcategory": {"complex": None, "simple": "subcategory"},
                        "urgency": {"complex": None, "simple": "servicenowurgency"},
                        "work_start": {
                            "complex": None,
                            "simple": "timetoassignment.startDate",
                        },
                    },
                }
            },
            "name": "ServiceNow - Outgoing Mapper",
            "type": "mapping-outgoing",
            "version": -1,
        }
        mocker.patch(
            "demisto_sdk.commands.common.tools.get_file",
            return_value=outgoing_mapper_snow,
        )

        mapper = get_mapper_data("")
        mapper_data = mapper.get("ServiceNow-outgoing-mapper")
        assert mapper_data.get("name") == "ServiceNow - Outgoing Mapper"
        assert mapper_data.get("display_name") == "ServiceNow - Outgoing Mapper"
        assert mapper_data.get("fromversion") == "6.0.0"
        assert mapper_data.get("incident_types") == ["ServiceNow Ticket"]
        assert set(mapper_data.get("incident_fields")) == {
            "closed",
            "servicenowescalation",
            "servicenowurgency",
            "subcategory",
            "servicenownotify",
            "servicenowcategory",
            "remediationsla.dueDate",
            "servicenowstate",
            "timetoassignment.startDate",
            "servicenowimpact",
            "servicenowpriority",
        }

    @staticmethod
    def test_process_mappers__complex_value():
        """
        Given
            - An mapper file called classifier-mapper-to-test-complex-value.json with one transformer and one filter

        When
            - parsing mapper files

        Then
            - parsing one filter and one transformer from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-mapper-to-test-complex-value.json",
        )

        res = get_mapper_data(test_file)
        result = res.get("dummy mapper")
        transformers = result.get("transformers")
        filters = result.get("filters")
        assert len(transformers) == 1
        assert "toUpperCase" in transformers
        assert len(filters) == 1
        assert "isEqualString" in filters


class TestWidget:
    @staticmethod
    def test_process_widget__with_script():
        """
        Given
            - A widget file called widget-with-scripts.json

        When
            - parsing widget files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "widget-with-scripts.json",
        )

        res = get_widget_data(test_file)
        result = res.get("dummy_widget")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" in result.keys()
        assert "dummy_script" in result["scripts"]

    @staticmethod
    def test_process_widget__no_script():
        """
        Given
            - A widget file called widget-no-scripts.json

        When
            - parsing widget files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "widget-no-scripts.json",
        )

        res = get_widget_data(test_file)
        result = res.get("dummy_widget")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" not in result.keys()


class TestDashboard:
    DASHBOARD_WITH_SCRIPT = {
        "id": "dummy_dashboard",
        "layout": [
            {
                "widget": {
                    "category": "",
                    "dataType": "scripts",
                    "id": "dummy_widget",
                    "name": "dummy_dashboard",
                    "query": "dummy_script",
                    "toServerVersion": "",
                },
            }
        ],
        "name": "dummy_dashboard",
        "marketplaces": ["xsoar"],
        "fromVersion": "6.0.0",
    }

    DASHBOARD_NO_SCRIPT = {
        "id": "dummy_dashboard",
        "layout": [
            {
                "widget": {
                    "category": "",
                    "dataType": "indicators",
                    "fromServerVersion": "",
                    "id": "dummy_widget",
                    "name": "dummy_dashboard",
                    "packID": "",
                    "widgetType": "table",
                },
            }
        ],
        "name": "dummy_dashboard",
        "marketplaces": ["xsoar"],
        "fromVersion": "6.0.0",
    }

    @staticmethod
    def test_process_dashboard__with_script(repo):
        """
        Given
            - A dashboard file called dashboard-with-scripts.json

        When
            - parsing dashboard files

        Then
            - parsing all the data from file successfully
        """
        pack = repo.create_pack("Pack1")
        dashboard = pack.create_dashboard("dummy_dashboard")
        dashboard.update(TestDashboard.DASHBOARD_WITH_SCRIPT)

        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            dashboard.path,
        )

        res = get_dashboard_data(test_file)
        result = res.get("dummy_dashboard")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" in result.keys()
        assert "dummy_script" in result["scripts"]

    @staticmethod
    def test_process_dashboard__no_script(repo):
        """
        Given
            - A dashboard file called dashboard-no-scripts.json

        When
            - parsing dashboard files

        Then
            - parsing all the data from file successfully
        """
        pack = repo.create_pack("Pack1")
        dashboard = pack.create_dashboard("dummy_dashboard")
        dashboard.update(TestDashboard.DASHBOARD_NO_SCRIPT)

        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            dashboard.path,
        )

        res = get_dashboard_data(test_file)
        result = res.get("dummy_dashboard")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" not in result.keys()


class TestReport:
    REPORT_WITH_SCRIPT = {
        "id": "dummy_report",
        "modified": "2020-09-23T07:54:57.783240299Z",
        "startDate": "0001-01-01T00:00:00Z",
        "name": "dummy_report",
        "marketplaces": ["xsoar"],
        "dashboard": {
            "id": "dummy_report",
            "version": 0,
            "name": "dummy_report",
            "layout": [
                {
                    "id": "dummy_report",
                    "widget": {
                        "id": "dummy_report",
                        "version": 1,
                        "modified": "2020-09-09T14:02:27.423018192Z",
                        "name": "dummy_widget",
                        "dataType": "scripts",
                        "query": "dummy_script",
                    },
                }
            ],
        },
        "fromVersion": "6.0.0",
    }

    REPORT_NO_SCRIPT = {
        "id": "dummy_report",
        "name": "dummy_report",
        "marketplaces": ["xsoar"],
        "dashboard": {
            "id": "dummy_report",
            "name": "dummy_report",
            "layout": [
                {
                    "id": "dummy_report",
                    "widget": {
                        "id": "dummy_report",
                        "name": "dummy_widget",
                        "dataType": "indicators",
                    },
                }
            ],
        },
        "fromVersion": "6.0.0",
    }

    @staticmethod
    def test_process_report__with_script(repo):
        """
        Given
            - A report file called report-with-scripts.json

        When
            - parsing report files

        Then
            - parsing all the data from file successfully
        """
        pack = repo.create_pack("Pack1")
        report = pack.create_report("dummy_report")
        report.update(TestReport.REPORT_WITH_SCRIPT)
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            report.path,
        )

        res = get_report_data(test_file)
        result = res.get("dummy_report")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" in result.keys()
        assert "dummy_script" in result["scripts"]

    @staticmethod
    def test_process_report__no_script(repo):
        """
        Given
            - A report file called report-no-scripts.json

        When
            - parsing report files

        Then
            - parsing all the data from file successfully
        """
        pack = repo.create_pack("Pack1")
        report = pack.create_report("dummy_report")
        report.update(TestReport.REPORT_NO_SCRIPT)
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            report.path,
        )

        res = get_report_data(test_file)
        result = res.get("dummy_report")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "scripts" not in result.keys()


class TestGenericFunctions:
    @staticmethod
    def test_process_general_items__sanity(mocker):
        """
        Given
            - A classifier file called classifier-to-test.json

        When
            - parsing classifier files

        Then
            - parsing all the data from file successfully
        """
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-to-test.json",
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        res, _ = process_general_items(
            test_file,
            {"": {}},
            MarketplaceVersions.XSOAR.value,
            True,
            (FileType.CLASSIFIER,),
            get_classifier_data,
        )
        assert len(res) == 1
        result = res[0]
        result = result.get("dummy classifier")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "incident_types" in result.keys()
        assert "dummy incident type" in result["incident_types"]
        assert "dummy incident type 2" in result["incident_types"]
        assert "dummy incident type 3" in result["incident_types"]

    @staticmethod
    def test_process_general_items__marketplace_mismatch(mocker):
        """
        Given
            - An item file

        When
            - parsing item files when there is a mismatch between the item's marketplaces and the current run marketplace.

        Then
            - return empty list
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=True)
        test_file = os.path.join(
            git_path(),
            "demisto_sdk",
            "commands",
            "create_id_set",
            "tests",
            "test_data",
            "classifier-to-test.json",
        )
        res, _ = process_general_items(
            test_file,
            {"DummyPack": {}},
            MarketplaceVersions.XSOAR.value,
            True,
            (FileType.CLASSIFIER,),
            get_classifier_data,
        )
        assert res == []

    @staticmethod
    def test_process_general_items__exception(mocker):
        """
        Given
            - An invalid "dashboard" file located at invalid_file_structures where id is a list so it can't be used
                as a dict key.

        When
            - parsing dashboard files

        Then
            - an exception will be raised
        """
        test_file_path = os.path.join(
            TESTS_DIR, "test_files", "invalid_file_structures", "dashboard.json"
        )
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        with pytest.raises(Exception):
            process_general_items(
                test_file_path, True, (FileType.DASHBOARD,), get_general_data
            )

    @staticmethod
    def test_get_values_for_keys_recursively():
        """
        Given
            - A list of keys to extract their values from a dict

        When
            - Extracting data from nested elements in the json

        Then
            - Extracting the values from all the levels of nesting in the json
        """

        test_dict = {
            "id": 1,
            "nested": {
                "x1": 1,
                "x2": "x2",
                "x3": False,
                "x4": [{"x1": 2, "x2": 55}, {"x3": 1, "x2": True}],
            },
            "x2": 4.0,
        }

        test_keys = ["x1", "x2", "x3"]

        expected = {"x1": [1, 2], "x2": ["x2", 55, True, 4.0], "x3": [False, 1]}

        assert expected == get_values_for_keys_recursively(test_dict, test_keys)

    INPUT_WITH_INCIDENT_FIELD_SIMPLE = {
        "key": "AlertID",
        "value": {"simple": "${incident.field_name}"},
        "required": False,
    }

    INPUT_WITH_INCIDENT_FIELD_COMPLEX1 = {
        "key": "AlertID",
        "value": {"complex": {"root": "incident", "accessor": "field_name"}},
        "required": False,
    }

    INPUT_WITH_INCIDENT_FIELD_COMPLEX2 = {
        "key": "AlertID",
        "value": {"complex": {"root": "incident.field_name", "accessor": "username"}},
        "required": False,
    }

    INPUT_SIMPLE_WITHOUT_INCIDENT_FIELD = {
        "key": "AlertID",
        "value": {"simple": "${not_incident.field_name}"},
        "required": False,
    }

    INPUT_COMPLEX_WITHOUT_INCIDENT_FIELD = {
        "key": "AlertID",
        "value": {"complex": {"root": "something", "accessor": "username"}},
        "required": False,
    }

    INPUTS = [
        (INPUT_WITH_INCIDENT_FIELD_SIMPLE, True),
        (INPUT_WITH_INCIDENT_FIELD_COMPLEX1, True),
        (INPUT_WITH_INCIDENT_FIELD_COMPLEX2, True),
        (INPUT_SIMPLE_WITHOUT_INCIDENT_FIELD, False),
        (INPUT_COMPLEX_WITHOUT_INCIDENT_FIELD, False),
    ]

    @staticmethod
    @pytest.mark.parametrize("playbook_input, are_there_incident_fields", INPUTS)
    def test_get_incident_fields_by_playbook_input(
        playbook_input, are_there_incident_fields
    ):
        """
        Given
            - A list of playbook inputs

        When
            - Searching for dependent incident fields

        Then
            -  Finding all dependent incident fields in the input
        """

        result = get_incident_fields_by_playbook_input(playbook_input.get("value"))
        if are_there_incident_fields:
            assert "field_name" in result
        else:
            assert result == set()

    EXAMPLE_TASK_WITH_SIMPLE_SCRIPT_ARGUMENTS = {
        "id": "ID",
        "scriptarguments": {"field_name": {"simple": "${inputs.IndicatorTagName}"}},
    }

    EXAMPLE_TASK_WITH_CUSTOM_FIELDS_SCRIPT_ARGUMENTS = {
        "id": "ID",
        "scriptarguments": {
            "customFields": {"simple": '[{"field_name":"${inputs.IndicatorTagName}"}]'}
        },
    }

    TASK_INPUTS = [
        # EXAMPLE_TASK_WITH_SIMPLE_SCRIPT_ARGUMENTS,
        EXAMPLE_TASK_WITH_CUSTOM_FIELDS_SCRIPT_ARGUMENTS
    ]

    @staticmethod
    @pytest.mark.parametrize("task", TASK_INPUTS)
    def test_get_fields_by_script_argument(task):
        """
        Given
            - A list of playbook tasks

        When
            - Searching for dependent incident fields in the task script arguments

        Then
            - Finding all dependent incident fields in the task
        """

        result = get_fields_by_script_argument(task)
        assert "field_name" in result


class TestFlow(unittest.TestCase):
    WIDGET_DATA = {
        "id": "temp-widget-dup-check",
        "version": -1,
        "fromVersion": "3.5.0",
        "name": "check duplicate",
        "dataType": "incidents",
        "widgetType": "pie",
    }

    REPORT_DATA = {
        "id": "temp-report-dup-check",
        "name": "Critical and High incidents",
        "description": "All critical and high severity incidents that may need the analyst attention.",
        "fromVersion": "3.5.0",
    }

    CLASSIFIER_DATA = {
        "id": "dup_check-classifier",
        "version": -1,
        "modified": "2018-05-21T12:41:29.542577629Z",
        "defaultIncidentType": "",
        "brandName": "dup_check-classifier-name",
    }

    LAYOUT_DATA = {
        "TypeName": "layout-dup-check-type-name",
        "kind": "details",
        "fromVersion": "5.0.0",
        "layout": {
            "TypeName": "",
            "id": "layout-dup-check-id",
            "kind": "details",
            "modified": "2019-09-01T12:25:49.808989+03:00",
            "name": "",
            "system": False,
        },
        "name": "my-layout",
        "typeId": "layout-dup-check-id",
        "version": -1,
    }

    DASHBOARD_DATA = {
        "id": "dup-check-dashbaord",
        "version": -1,
        "fromVersion": "4.0.0",
        "description": "",
        "name": "My Dashboard",
    }

    DASHBOARD_DATA2 = {
        "id": "dup-check-dashbaord",
        "version": -1,
        "fromVersion": "4.0.0",
        "description": "",
        "name": "My Dashboard2",
    }

    INCIDENT_FIELD_DATA = {
        "cliName": "accountid",
        "description": "",
        "fieldCalcScript": "",
        "group": 0,
        "id": "incident_account_field_dup_check",
        "name": "Account ID",
        "fromVersion": "5.0.0",
    }

    # TODO: unskip
    @pytest.mark.skip
    def test_find_duplicates(self):
        sys.path.insert(1, os.getcwd())
        # Make the script run from tests dir
        os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), TESTS_DIR)))

        # create duplicate report
        temp_report = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="report-",  # disable-secrets-detection
            suffix=".json",
            dir="Reports",
        )  # disable-secrets-detection
        json.dump(TestFlow.REPORT_DATA, temp_report)
        temp_report.flush()
        os.fsync(temp_report.fileno())
        temp_report2 = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="report-",  # disable-secrets-detection
            suffix=".json",
            dir="Reports",
        )  # disable-secrets-detection
        json.dump(TestFlow.REPORT_DATA, temp_report2)
        temp_report2.flush()
        os.fsync(temp_report2.fileno())

        # create duplicate Widgets
        temp_widget = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="widget-",  # disable-secrets-detection
            suffix=".json",
            dir="Widgets",
        )  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_widget)
        temp_widget.flush()
        os.fsync(temp_widget.fileno())
        temp_widget2 = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="widget-",  # disable-secrets-detection
            suffix=".json",
            dir="Widgets",
        )  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_widget2)
        temp_widget2.flush()
        os.fsync(temp_widget2.fileno())

        # create duplicate Classifier
        temp_classifier = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="classifier-",  # disable-secrets-detection
            suffix=".json",
            dir="Classifiers",
        )  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_classifier)
        temp_classifier.flush()
        os.fsync(temp_classifier.fileno())
        temp_classifier2 = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="classifier-",  # disable-secrets-detection
            suffix=".json",
            dir="Classifiers",
        )  # disable-secrets-detection
        json.dump(TestFlow.WIDGET_DATA, temp_classifier2)
        temp_classifier2.flush()
        os.fsync(temp_classifier2.fileno())

        # create duplicate Layout
        temp_layout = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="layout-",  # disable-secrets-detection
            suffix=".json",
            dir="Layouts",
        )  # disable-secrets-detection
        json.dump(TestFlow.LAYOUT_DATA, temp_layout)
        temp_layout.flush()
        os.fsync(temp_layout.fileno())
        temp_layout2 = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="layout-",
            suffix=".json",
            # disable-secrets-detection
            dir="Packs/CortexXDR/Layouts",
        )  # disable-secrets-detection
        json.dump(TestFlow.LAYOUT_DATA, temp_layout2)
        temp_layout2.flush()
        os.fsync(temp_layout2.fileno())

        # create duplicate Dashboard
        temp_dashboard = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="dashboard-",  # disable-secrets-detection
            suffix=".json",
            dir="Dashboards",
        )  # disable-secrets-detection
        json.dump(TestFlow.DASHBOARD_DATA, temp_dashboard)
        temp_dashboard.flush()
        os.fsync(temp_dashboard.fileno())
        temp_dashboard2 = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="dashboard-",  # disable-secrets-detection
            suffix=".json",
            dir="Dashboards",
        )  # disable-secrets-detection
        json.dump(TestFlow.DASHBOARD_DATA2, temp_dashboard2)
        temp_dashboard2.flush()
        os.fsync(temp_dashboard2.fileno())

        # create one incident type field and one indicator type field with same data
        temp_incident_field = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="incidentfield-",
            # disable-secrets-detection
            suffix=".json",
            dir="IncidentFields",
        )  # disable-secrets-detection
        json.dump(TestFlow.INCIDENT_FIELD_DATA, temp_incident_field)
        temp_incident_field.flush()
        os.fsync(temp_incident_field.fileno())
        temp_indicator_field = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="incidentfield-",
            # disable-secrets-detection
            suffix=".json",
            dir="IndicatorFields",
        )
        json.dump(TestFlow.INCIDENT_FIELD_DATA, temp_indicator_field)
        temp_indicator_field.flush()
        os.fsync(temp_indicator_field.fileno())

        # create temporary file for id_set
        temp_id_set = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix="temp_id_set-",  # disable-secrets-detection
            suffix=".json",
            dir="Tests/scripts",
        )  # disable-secrets-detection
        json_path = temp_id_set.name

        re_create_id_set(
            json_path,
            [
                "Reports",
                "Layouts",
                "Widgets",
                "Classifiers",
                "Dashboards",
                "IndicatorFields",
                "IncidentFields",
            ],
        )
        with open(json_path) as json_file:
            data = json.load(json_file)
            dup_data = find_duplicates(data)
            assert any("temp-widget-dup-check" in i for i in dup_data)
            assert any("temp-report-dup-check" in i for i in dup_data)
            assert any("temp-widget-dup-check" in i for i in dup_data)
            assert any("dup-check-dashbaord" in i for i in dup_data)
            assert any("layout-dup-check-id" in i for i in dup_data)
            assert any("incident_account_field_dup_check" in i for i in dup_data)


class TestGenericFields:
    @staticmethod
    def test_process_generic_fields(pack):
        """
        Given
            - A generic field file

        When
            - parsing generic field files

        Then
            - parsing all the data from file successfully
        """

        field_data = {
            "cliName": "operatigsystem",
            "id": "id",
            "name": "Operating System",
            "definitionId": "assets",
            "fromVersion": "6.5.0",
            "associatedTypes": ["Asset Type"],
        }

        generic_types_list = [
            {
                "Asset Type": {
                    "name": "Asset Type",
                    "file_path": "path/path",
                    "fromversion": "6.5.0",
                    "pack": "ObjectsExample",
                    "definitionId": "assets",
                    "layout": "Workstation Layout",
                }
            }
        ]

        generic_field = pack.create_generic_field("test-generic-field")
        generic_field.write_json(field_data)
        test_dir = generic_field.path

        result = get_generic_field_data(test_dir, generic_types_list=generic_types_list)
        result = result.get("id")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "definitionId" in result.keys()
        assert "generic_types" in result.keys()


class TestGenericType:
    @staticmethod
    def test_get_generic_type_data(pack):
        """
        Given
            - A generic type file

        When
            - parsing object type files

        Then
            - parsing all the data from file successfully
        """

        object_type = pack.create_generic_module("test-object-type")
        object_type.write_json(
            {
                "id": "type-id",
                "name": "type-name",
                "fromVersion": "version",
                "definitionId": "Assets",
                "layout": "layout",
            }
        )
        test_dir = object_type.path

        result = get_generic_type_data(test_dir)
        result = result.get("type-id")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "layout" in result.keys()
        assert "definitionId" in result.keys()


class TestGenericDefinition:
    @staticmethod
    def test_get_generic_definition_data(pack):
        """
        Given
            - A generic definition file

        When
            - parsing definition type files

        Then
            - parsing all the data from file successfully
        """

        object_type = pack.create_generic_definition("test-generic-definition")
        object_type.write_json(
            {
                "id": "type-id",
                "name": "type-name",
                "fromVersion": "version",
                "auditable": False,
            }
        )
        test_dir = object_type.path

        result = get_general_data(test_dir)
        result = result.get("type-id")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "pack" in result.keys()


class TestGenericModule:
    @staticmethod
    def test_get_generic_module_data(repo):
        """
        Given
            - A generic module file

        When
            - parsing generic generic module files

        Then
            - parsing all the data from file successfully
        """

        module_data = {
            "id": "id",
            "version": -1,
            "name": "Vulnerability Management",
            "fromVersion": "6.5.0",
            "definitionIds": ["assets"],
            "views": [
                {
                    "name": "Vulnerability Management",
                    "title": "Risk Base Vulnerability Management",
                    "tabs": [
                        {
                            "name": "Assets",
                            "newButtonDefinitionId": "assets",
                            "dashboard": {
                                "id": "assets_dashboard",
                                "version": -1,
                                "fromDate": "0001-01-01T00:00:00Z",
                                "toDate": "0001-01-01T00:00:00Z",
                                "name": "Assets Dashboard",
                                "prevName": "Assets Dashboard",
                            },
                        }
                    ],
                }
            ],
        }

        pack = repo.create_pack("pack")
        generic_module = pack.create_generic_module("test-generic-module")
        generic_module.write_json(module_data)
        test_dir = generic_module.path

        result = get_generic_module_data(test_dir)
        result = result.get("id")
        assert "name" in result.keys()
        assert "display_name" in result.keys()
        assert "file_path" in result.keys()
        assert "fromversion" in result.keys()
        assert "definitionIds" in result.keys()
        assert "views" in result.keys()
        assert "pack" in result.keys()


class TestJob:
    @staticmethod
    @pytest.mark.parametrize("print_logs", (True, False))
    @pytest.mark.parametrize("is_feed", (True, False))
    def test_process_jobs(capsys, repo, is_feed: bool, print_logs: bool, mocker):
        """
        Given
            - A repo with a job object.
            - Whether to print logs.
        When
            - Parsing job files.
        Then
            - Verify output to logs.
        """
        pack = repo.create_pack()
        job_details = "job details"
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        job = pack.create_job(is_feed, details=job_details)
        res = process_jobs(
            job.path, {pack.name: {}}, MarketplaceVersions.XSOAR.value, print_logs
        )

        captured = capsys.readouterr()
        assert len(res) == 1
        datum = res[0][job.pure_name]
        assert datum["name"] == job.pure_name
        assert datum["display_name"] == job.pure_name
        path = Path(datum["file_path"])
        assert path.name == f"job-{job.pure_name}.json"
        assert path.exists()
        assert path.is_file()
        assert path.suffix == ".json"
        assert path.parts[-2] == JOBS_DIR
        assert path.parts[-3] == pack.name

        assert datum["fromversion"] == FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.JOB)
        assert datum["pack"] == pack.name
        assert datum["details"] == job_details
        assert datum["selectedFeeds"] == []

        assert (f"adding {job.path} to id_set" in captured.out) == print_logs

    @staticmethod
    @pytest.mark.parametrize("is_feed", (True, False))
    def test_process_jobs_non_job_extension(capsys, repo, is_feed: bool, mocker):
        """
        Given
            - A file that isn't a valid Job (wrong filetype)
            - Whether to print logs.
        When
            - Parsing job files.
        Then
            - Verify output to logs.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        pack = repo.create_pack()
        job = pack.create_job(is_feed)
        job_path = Path(job.path)
        new_path = job_path.rename(job_path.with_suffix(".yml"))
        res = process_jobs(
            str(new_path), {pack.name: {}}, MarketplaceVersions.XSOAR.value, False
        )
        assert not res

    @staticmethod
    @pytest.mark.parametrize("print_logs", (True, False))
    @pytest.mark.parametrize("is_feed", (True, False))
    def test_process_jobs_file_nonexistent(
        capsys, repo, is_feed: bool, print_logs: bool, mocker
    ):
        """
        Given
            - A file that isn't a valid Job (missing file)
            - Whether to print logs.
        When
            - Parsing job files.
        Then
            - Verify output to logs.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)

        pack = repo.create_pack()
        job = pack.create_job(is_feed)
        job_json_path = Path(job.path)
        job_json_path_as_yml = job_json_path.with_suffix(".yml")

        job_json_path.rename(job_json_path_as_yml)
        with pytest.raises(FileNotFoundError):
            assert not process_jobs(
                str(job_json_path),
                {pack.name: {}},
                MarketplaceVersions.XSOAR.value,
                print_logs,
            )
        assert f"failed to process job {job_json_path}" in capsys.readouterr().out


class TestWizard:
    EXPECTED_DEPENDENCY_PACKS = [
        "CrowdStrikeFalcon",
        "MicrosoftDefenderAdvancedThreatProtection",
    ]

    @staticmethod
    @pytest.mark.parametrize("print_logs", (True, False))
    def test_process_wizards(capsys, repo, print_logs: bool, mocker):
        """
        Given
            - A repo with a wizard object.
            - Whether to print logs.
        When
            - Parsing wizard files.
        Then
            - Verify output to logs.
        """
        pack = repo.create_pack()
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        wizard = pack.create_wizard("wizard")
        res = process_wizards(
            wizard.path, {pack.name: {}}, MarketplaceVersions.XSOAR.value, print_logs
        )

        captured = capsys.readouterr()
        assert len(res) == 1
        datum = res[0][wizard.id]
        assert datum["name"] == wizard.id
        assert datum["display_name"] == wizard.id
        assert set(datum["dependency_packs"]) == set(
            TestWizard.EXPECTED_DEPENDENCY_PACKS
        )
        path = Path(datum["file_path"])
        assert path.name == wizard.name
        assert path.exists()
        assert path.is_file()
        assert path.suffix == ".json"
        assert path.parts[-2] == WIZARDS_DIR
        assert path.parts[-3] == pack.name

        assert datum["fromversion"] == FILETYPE_TO_DEFAULT_FROMVERSION.get(
            FileType.WIZARD
        )
        assert datum["pack"] == pack.name

        assert (f"adding {wizard.path} to id_set" in captured.out) == print_logs


class TestParsingRules:
    @staticmethod
    def test_process_parsing_rules(mocker, capsys, pack):
        """
        Given
            - A repo with a parsing rule object.
        When
            - Parsing the parsing rule files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        parsing_rule = pack.create_parsing_rule("parsing_rule_name")
        res = process_general_items(
            parsing_rule.yml.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.PARSING_RULE,),
            get_parsing_rule_data,
        )

        captured = capsys.readouterr()
        parsing_rule_result = res[0][0]["parsing-rule"]

        assert len(res) == 2
        assert "name" in parsing_rule_result.keys()
        assert "display_name" in parsing_rule_result.keys()
        assert "file_path" in parsing_rule_result.keys()
        assert "pack" in parsing_rule_result.keys()

        assert parsing_rule_result["name"] == "Parsing Rule"
        assert parsing_rule_result["file_path"] == parsing_rule.yml.path
        assert parsing_rule_result["pack"] == pack.name

        assert f"adding {parsing_rule.yml.path} to id_set" in captured.out


class TestModelingRules:
    @staticmethod
    def test_process_modeling_rules(mocker, capsys, pack):
        """
        Given
            - A repo with a modeling rule object.
        When
            - Parsing the modeling rule files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        modeling_rule = pack.create_modeling_rule("modeling_rule_name")
        res = process_general_items(
            modeling_rule.yml.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.MODELING_RULE,),
            get_modeling_rule_data,
        )

        captured = capsys.readouterr()
        modeling_rule_result = res[0][0]["modeling-rule"]

        assert len(res) == 2
        assert "name" in modeling_rule_result.keys()
        assert "display_name" in modeling_rule_result.keys()
        assert "file_path" in modeling_rule_result.keys()
        assert "pack" in modeling_rule_result.keys()

        assert modeling_rule_result["name"] == "Modeling Rule"
        assert modeling_rule_result["file_path"] == modeling_rule.yml.path
        assert modeling_rule_result["pack"] == pack.name

        assert f"adding {modeling_rule.yml.path} to id_set" in captured.out


class TestCorrelationRules:
    @staticmethod
    def test_process_correlation_rules(mocker, capsys, pack):
        """
        Given
            - A repo with a correlation rule object.
        When
            - Parsing the correlation rule files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        correlation_rule = pack.create_correlation_rule(
            "correlation_rule_name",
            {
                "global_rule_id": "correlation_rule_id",
                "name": "correlation_rule_name",
                "alert_category": "",
            },
        )
        res = process_general_items(
            correlation_rule.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.CORRELATION_RULE,),
            get_correlation_rule_data,
        )

        captured = capsys.readouterr()
        correlation_rule_result = res[0][0]["correlation_rule_id"]

        assert len(res) == 2
        assert "name" in correlation_rule_result.keys()
        assert "display_name" in correlation_rule_result.keys()
        assert "file_path" in correlation_rule_result.keys()
        assert "pack" in correlation_rule_result.keys()

        assert (
            correlation_rule_result["name"]
            == correlation_rule._tmp_path.parts[-1].split(".")[0]
        )
        assert correlation_rule_result["file_path"] == correlation_rule.path
        assert correlation_rule_result["pack"] == pack.name

        assert f"adding {correlation_rule._tmp_path} to id_set" in captured.out


class TestXSIAMDashboards:
    @staticmethod
    def test_process_xsiam_dashboards(mocker, capsys, pack):
        """
        Given
            - A repo with a XSIAM dashboard object.
        When
            - Parsing the XSIAM dashboards files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        xsiam_dashboard = pack.create_xsiam_dashboard(
            "xsiam_dashboard_name",
            {
                "dashboards_data": [
                    {"global_id": "xsiam_dashboard_id", "name": "xsiam_dashboard_name"}
                ]
            },
        )
        res = process_general_items(
            xsiam_dashboard.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.XSIAM_DASHBOARD,),
            get_xsiam_dashboard_data,
        )

        captured = capsys.readouterr()
        xsiam_dashboard_result = res[0][0]["xsiam_dashboard_id"]

        assert len(res) == 2
        assert "name" in xsiam_dashboard_result.keys()
        assert "display_name" in xsiam_dashboard_result.keys()
        assert "file_path" in xsiam_dashboard_result.keys()
        assert "pack" in xsiam_dashboard_result.keys()

        assert (
            xsiam_dashboard_result["name"]
            == xsiam_dashboard._file_path.parts[-1].split(".")[0]
        )
        assert xsiam_dashboard_result["file_path"] == xsiam_dashboard.path
        assert xsiam_dashboard_result["pack"] == pack.name

        assert f"adding {xsiam_dashboard._file_path} to id_set" in captured.out


class TestXSIAMReports:
    @staticmethod
    def test_process_xsiam_reports(mocker, capsys, pack):
        """
        Given
            - A repo with a XSIAM report object.
        When
            - Parsing the XSIAM reports files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        xsiam_report = pack.create_xsiam_report(
            "xsiam_report_name",
            {
                "templates_data": [
                    {"global_id": "xsiam_report_id", "report_name": "xsiam_report_name"}
                ]
            },
        )
        res = process_general_items(
            xsiam_report.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.XSIAM_REPORT,),
            get_xsiam_report_data,
        )

        captured = capsys.readouterr()
        xsiam_report_result = res[0][0]["xsiam_report_id"]

        assert len(res) == 2
        assert "name" in xsiam_report_result.keys()
        assert "display_name" in xsiam_report_result.keys()
        assert "file_path" in xsiam_report_result.keys()
        assert "pack" in xsiam_report_result.keys()

        assert (
            xsiam_report_result["name"]
            == xsiam_report._file_path.parts[-1].split(".")[0]
        )
        assert xsiam_report_result["file_path"] == xsiam_report.path
        assert xsiam_report_result["pack"] == pack.name

        assert f"adding {xsiam_report._file_path} to id_set" in captured.out


class TestTriggers:
    @staticmethod
    def test_process_triggers(mocker, capsys, pack):
        """
        Given
            - A repo with a XSIAM report object.
        When
            - Parsing the XSIAM reports files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        trigger = pack.create_trigger(
            "trigger_name", {"trigger_id": "trigger_id", "trigger_name": "trigger_name"}
        )
        res = process_general_items(
            trigger.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.TRIGGER,),
            get_trigger_data,
        )

        captured = capsys.readouterr()
        trigger_result = res[0][0]["trigger_id"]

        assert len(res) == 2
        assert "name" in trigger_result.keys()
        assert "display_name" in trigger_result.keys()
        assert "file_path" in trigger_result.keys()
        assert "pack" in trigger_result.keys()

        assert trigger_result["name"] == trigger._file_path.parts[-1].split(".")[0]
        assert trigger_result["file_path"] == trigger.path
        assert trigger_result["pack"] == pack.name

        assert f"adding {trigger._file_path} to id_set" in captured.out


class TestXDRCTemplates:
    @staticmethod
    def test_process_xdrc_templates(mocker, capsys, pack):
        """
        Given
            - A repo with a XSIAM XDRC Template object.
        When
            - Parsing the XSIAM XDRC Template files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        xdrc_template = pack.create_xdrc_template(
            "xdrc_template_name",
            {
                "content_global_id": "xdrc_template_id",
                "name": "xdrc_template_name",
                "os_type": "os_type_test",
                "profile_type": "profile_type_test",
                "yaml_template": "yaml_test",
            },
        )
        res = process_general_items(
            xdrc_template.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.XDRC_TEMPLATE,),
            get_xdrc_template_data,
            "json",
        )

        captured = capsys.readouterr()
        xdrc_template_result = res[0][0]["xdrc_template_id"]

        assert len(res) == 2
        assert "name" in xdrc_template_result.keys()
        assert "display_name" in xdrc_template_result.keys()
        assert "file_path" in xdrc_template_result.keys()
        assert "pack" in xdrc_template_result.keys()

        assert (
            xdrc_template_result["name"]
            == xdrc_template._file_path.parts[-1].split(".")[0]
        )
        assert xdrc_template_result["file_path"] == xdrc_template.path
        assert xdrc_template_result["pack"] == pack.name

        assert f"adding {xdrc_template._file_path} to id_set" in captured.out


class TestLayoutRules:
    @staticmethod
    def test_process_layout_rules(mocker, capsys, pack):
        """
        Given
            - A repo with a LayoutRule object.
        When
            - Parsing the LayoutRule files.
        Then
            - Verify result as expeted.
        """
        mocker.patch.object(uis, "should_skip_item_by_mp", return_value=False)
        layout_rule = pack.create_layout_rule(
            "rule_name", {"rule_id": "rule_id", "rule_name": "rule_name"}
        )
        res = process_general_items(
            layout_rule.path,
            {pack.name: {}},
            MarketplaceVersions.MarketplaceV2.value,
            True,
            (FileType.LAYOUT_RULE,),
            get_layout_rule_data,
            "json",
        )

        captured = capsys.readouterr()
        layout_rule_result = res[0][0]["rule_id"]

        assert len(res) == 2
        assert "name" in layout_rule_result.keys()
        assert "display_name" in layout_rule_result.keys()
        assert "file_path" in layout_rule_result.keys()
        assert "pack" in layout_rule_result.keys()

        assert (
            layout_rule_result["name"] == layout_rule._file_path.parts[-1].split(".")[0]
        )
        assert layout_rule_result["file_path"] == layout_rule.path
        assert layout_rule_result["pack"] == pack.name

        assert f"adding {layout_rule._file_path} to id_set" in captured.out


def test_merge_id_sets(tmp_path):
    """
    Given
    - two id_set files
    - id_sets don't contain duplicate items

    When
    - merged

    Then
    - ensure the output id_set contains items from both id_sets
    - ensure no duplicates found
    """
    tmp_dir = tmp_path / "somedir"
    tmp_dir.mkdir()

    first_id_set = {
        "playbooks": [{"playbook_foo1": {}}],
        "integrations": [{"integration_foo1": {}}],
        "Packs": {"pack_foo1": {}},
    }

    second_id_set = {
        "playbooks": [{"playbook_foo2": {}}],
        "integrations": [{"integration_foo2": {}}],
        "Packs": {"pack_foo2": {}},
    }

    output_id_set, duplicates = merge_id_sets(first_id_set, second_id_set)

    assert output_id_set.get_dict() == {
        "playbooks": [{"playbook_foo1": {}}, {"playbook_foo2": {}}],
        "integrations": [{"integration_foo1": {}}, {"integration_foo2": {}}],
        "Packs": {"pack_foo1": {}, "pack_foo2": {}},
    }

    assert not duplicates


def test_merged_id_sets_with_duplicates(caplog):
    """
    Given
    - first_id_set.json
    - second_id_set.json
    - they both has the same script ScriptFoo

    When
    - merged

    Then
    - ensure output id_set contains items from both id_sets
    - ensure merge fails
    - ensure duplicate ScriptFoo found

    """
    caplog.set_level(logging.DEBUG)

    first_id_set = {
        "playbooks": [
            {
                "playbook_foo1": {
                    "name": "playbook_foo1",
                    "marketplaces": "xsoar",
                }
            }
        ],
        "scripts": [
            {
                "ScriptFoo": {
                    "name": "ScriptFoo",
                    "pack": "ScriptFoo1",
                    "marketplaces": "xsoar",
                }
            }
        ],
    }

    second_id_set = {
        "playbooks": [
            {
                "playbook_foo2": {
                    "name": "playbook_foo2",
                    "marketplaces": "xsoar",
                }
            }
        ],
        "scripts": [
            {
                "ScriptFoo": {
                    "name": "ScriptFoo",
                    "pack": "ScriptFoo2",
                    "marketplaces": "xsoar",
                }
            }
        ],
    }

    output_id_set, duplicates = merge_id_sets(first_id_set, second_id_set)

    assert output_id_set is None
    assert duplicates == ["ScriptFoo"]


def test_merged_id_sets_with_legal_duplicates(caplog):
    """
    Given
    - first_id_set.json
    - second_id_set.json
    - they both have the same playbook

    When
    - merged

    Then
    - ensure merge fails
    - ensure duplicate playbook_foo1 found

    """
    caplog.set_level(logging.DEBUG)

    first_id_set = {
        "playbooks": [
            {
                "playbook_foo1": {
                    "name": "playbook_foo1",
                    "pack": "foo_1",
                    "marketplaces": "xsoar",
                    "source": ["github.com", "demisto", "repo1"],
                }
            }
        ],
        "scripts": [
            {
                "Script_Foo1": {
                    "name": "ScriptFoo",
                    "pack": "foo_1",
                    "marketplaces": "xsoar",
                    "source": ["github.com", "demisto", "repo1"],
                }
            }
        ],
    }

    second_id_set = {
        "playbooks": [
            {
                "playbook_foo1": {
                    "name": "playbook_foo1",
                    "pack": "foo_1",
                    "marketplaces": "xsoar",
                    "source": ["github.com", "demisto", "repo2"],
                }
            }
        ],
        "scripts": [],
    }

    output_id_set, duplicates = merge_id_sets(first_id_set, second_id_set)

    assert output_id_set is None
    assert duplicates == ["playbook_foo1"]


def test_get_filters_and_transformers_from_complex_value():
    """
    Given
    - complex value with 3 transformers: Length, Length and toUpperCase
      and 3 filters: isEqualString, isEqualString and StringContainsArray

    When
    - parsing transformers and filters from the value

    Then
    - parsing 2 transformers successfully
    - Length transformer shows once
    - parsing 2 filters successfully
    - isEqualString filter shows once

    """

    data = {
        "transformers": [
            {"operator": "toUpperCase"},
            {"operator": "Length"},
            {"operator": "Length"},
        ],
        "filters": [
            [{"operator": "isEqualString"}],
            [{"operator": "isEqualString"}],
            [{"operator": "StringContainsArray"}],
        ],
    }
    transformers, filters = get_filters_and_transformers_from_complex_value(data)
    assert len(transformers) == 2
    assert len(filters) == 2
    assert "toUpperCase" in transformers
    assert "Length" in transformers
    assert "isEqualString" in filters
    assert "StringContainsArray" in filters


TEST_DICTS = [
    ({"key1": "val1", "key2": "val2"}, False),
    ({"key1": "val1", "key2": {"key1": "val1", "key2": "val2"}}, False),
    ({"key1": "val1", "key2_x2": "val2"}, True),
    ({"key1": "val1", "key2": {"kay1": "val1", "key2_x2": "val2"}}, True),
]


@pytest.mark.parametrize("dict_to_test, expected_result", TEST_DICTS)
def test_does_dict_have_alternative_key(dict_to_test, expected_result):
    result = does_dict_have_alternative_key(dict_to_test)
    assert result == expected_result


def test_should_skip_item_by_mp(mocker):
    """
    Given
    - path of content item, the current marketplace this id set is generated for.
    When
    - when creating the id set, checking a content item that is 'xsoar only' if it should be part of the mpV2
     id set.
    Then
    - return True since this item should be skipped.

    """
    import demisto_sdk.commands.common.tools as tools

    mocker.patch.object(
        tools, "get_mp_types_from_metadata_by_item", return_value=["xsoar"]
    )
    pack_path = os.path.join(
        TESTS_DIR, "test_files", "DummyPackXsoarMPOnly", "pack_metadata.json"
    )
    script_path = os.path.join(
        TESTS_DIR,
        "test_files",
        "DummyPackScriptIsXsoarOnly",
        "Scripts",
        "DummyScript.yml",
    )
    res1 = should_skip_item_by_mp(pack_path, "mpv2", {})
    res2 = should_skip_item_by_mp(script_path, "mpv2", {})
    assert res1
    assert res2


def test_should_skip_item_by_mp_no_update_excluded_dict(mocker):
    """
    Given
        - path of a pack which related only to xsoar marketplace, the current marketplace this id set is generated for.
    When
        - checking if it should be part of the mpV2 id set.
    Then
        - return True since this item should be skipped.
        - don't update the excluded item dict since we only want to add content items and not packs

    """
    import demisto_sdk.commands.common.tools as tools

    excluded_items_dict = {}
    mocker.patch.object(
        tools, "get_mp_types_from_metadata_by_item", return_value=["xsoar"]
    )
    pack_path = os.path.join(
        TESTS_DIR, "test_files", "DummyPackXsoarMPOnly", "pack_metadata.json"
    )
    res1 = should_skip_item_by_mp(pack_path, "mpv2", excluded_items_dict)
    assert res1
    assert not excluded_items_dict


def test_should_skip_item_by_mp_update_excluded_dict(mocker):
    """
    Given
        - path of a script which related only to xsoar, the current marketplace this id set is generated for.
    When
        - checking if it should be part of the mpV2 id set.
    Then
        - return True since this item should be skipped.
        - update the excluded item dict since we want to add content items to the dict

    """
    import demisto_sdk.commands.common.tools as tools

    excluded_items_dict = {}
    mocker.patch.object(
        tools, "get_mp_types_from_metadata_by_item", return_value=["xsoar"]
    )
    script_path = os.path.join(
        TESTS_DIR,
        "test_files",
        "DummyPackScriptIsXsoarOnly",
        "Scripts",
        "DummyScript.yml",
    )
    res2 = should_skip_item_by_mp(script_path, "mpv2", excluded_items_dict)
    assert excluded_items_dict
    assert res2


def test_add_item_to_exclusion_dict():
    """
    Given
        - path of content item, the current marketplace this id set is generated for.
    When
        - when creating the id set, checking a content item that is 'xsoar only' if it should be part of the mpV2 id set.
    Then
        - return True since this item should be skipped.
    """

    expected_result = {"CortexXDR": {("integration", "Cortex XDR")}}
    excluded_items_from_id_set = {}
    file_path = os.path.join(
        TESTS_DIR,
        "test_files",
        "Packs",
        "CortexXDR",
        "Integrations",
        "PaloAltoNetworks_XDR",
        "PaloAltoNetworks_XDR.yml",
    )
    add_item_to_exclusion_dict(excluded_items_from_id_set, file_path, "Cortex XDR")

    assert IsEqualFunctions.is_dicts_equal(expected_result, excluded_items_from_id_set)
