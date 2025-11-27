from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.SC_validators import (
    SC109_script_name_is_not_unique_validator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC100_script_has_invalid_version import (
    ScriptNameIsVersionedCorrectlyValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC101_script_arguments_aggregated_not_exists_validator import (
    MandatoryGenericArgumentsAggregatedScriptValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator_core_packs import (
    IsScriptArgumentsContainIncidentWordValidatorCorePacks,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC106_script_runas_dbot_role_validator import (
    ScriptRunAsIsNotDBotRoleValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator_all_files import (
    DuplicatedScriptNameValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator_list_files import (
    DuplicatedScriptNameValidatorListFiles,
)
from TestSuite.repo import ChangeCWD, Repo

MP_XSOAR = [MarketplaceVersions.XSOAR.value]
MP_V2 = [MarketplaceVersions.MarketplaceV2.value]
MP_XSOAR_AND_V2 = [
    MarketplaceVersions.XSOAR.value,
    MarketplaceVersions.MarketplaceV2.value,
]


def test_ScriptNameIsVersionCorrectlyValidator():
    """
    Given:
     - 1 script with valid versioned name
     - 1 script with invalid versioned name

    When:
     - Running the ScriptNameIsVersionCorrectlyValidator validator & fix

    Then:
     - make sure the script with the invalid version fails on the validation
     - make sure the fix updates the name of the script to upper-case versioned name.
    """
    content_items = [
        create_script_object(paths=["name"], values=["Testv2"]),
        create_script_object(paths=["name"], values=["TestV3"]),
    ]

    results = ScriptNameIsVersionedCorrectlyValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == 1
    assert results[0].content_object.name == "Testv2"

    fix_result = ScriptNameIsVersionedCorrectlyValidator().fix(
        results[0].content_object
    )
    assert fix_result.content_object.name == "TestV2"


def test_MandatoryGenericArgumentsAggregatedScriptValidator(mocker):
    """
    Given:
     - 1 Aggregated script with argument "verbose" does not exist.
     - 1 Aggregated script with argument "brands" does not exist.
     - 1 Aggregated script with argument "brands" and "verbose".
     - 1 Regular Script without "verbose" or "brands".

    When:
     - Running the MandatoryGenericArgumentsAggregatedScriptValidator validator.

    Then:
     - Make sure the first two scripts fails with missing arguments.
    """

    with ChangeCWD(REPO.path):
        mocker.patch(
            "demisto_sdk.commands.validate.validators.SC_validators.SC101_script_arguments_aggregated_not_exists_validator",
            return_value=["PackWithInvalidScript"],
        )

        content_items = (
            create_script_object(
                paths=["name", "args"],
                values=[
                    "InvalidScript1",
                    [
                        {
                            "name": "brands",
                            "description": "test",
                        }
                    ],
                ],
                pack_info={"name": "Aggregated Scripts"},
            ),
            create_script_object(
                paths=["name", "args"],
                values=[
                    "InvalidScript2",
                    [
                        {
                            "name": "verbose",
                            "description": "test",
                        }
                    ],
                ],
                pack_info={"name": "Aggregated Scripts"},
            ),
            create_script_object(
                paths=["name", "args"],
                values=[
                    "ValidScript",
                    [
                        {
                            "name": "verbose",
                            "description": "test",
                        },
                        {
                            "name": "brands",
                            "description": "test",
                        },
                    ],
                ],
                pack_info={"name": "Aggregated Scripts"},
            ),
            create_script_object(),
        )

        results = MandatoryGenericArgumentsAggregatedScriptValidator().obtain_invalid_content_items(
            content_items
        )
    assert len(results) == 2
    assert results[0].content_object.name == "InvalidScript1"
    assert results[1].content_object.name == "InvalidScript2"


def test_IsScriptArgumentsContainIncidentWordValidatorCorePacks_obtain_invalid_content_items(
    mocker,
):
    """
    Given:
     - 1 script that has the word incident in its arguments and is not deprecated and is in the core-packs list
     - 1 script that has the word incident in its arguments and is deprecated
     - 1 script that does not have the word incident in its arguments

    When:
     - Running the IsScriptArgumentsContainIncidentWordValidator validator

    Then:
     - make sure the script with the argument that has "incident" fails the validation
    """
    with ChangeCWD(REPO.path):
        mocker.patch(
            "demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator_core_packs.get_core_pack_list",
            return_value=["PackWithInvalidScript"],
        )

        content_items = (
            create_script_object(
                paths=["name", "args"],
                values=[
                    "InvalidScript",
                    [{"name": "incident-id", "description": "test"}],
                ],
                pack_info={"name": "PackWithInvalidScript"},
            ),
            create_script_object(
                paths=["args"],
                values=[
                    [
                        {
                            "name": "incident-id",
                            "description": "test",
                            "deprecated": True,
                        }
                    ],
                ],
                pack_info={"name": "PackWithValidScript"},
            ),
            create_script_object(),
        )

        results = IsScriptArgumentsContainIncidentWordValidatorCorePacks().obtain_invalid_content_items(
            content_items
        )
    assert len(results) == 1
    assert results[0].content_object.name == "InvalidScript"


def test_ScriptRunAsIsNotDBotRoleValidator_obtain_invalid_content_items():
    """
    Given:
     - 1 script that has runas field = DBotRole
     - 1 script that does not have runas field = DBotRole

    When:
     - Running the ScriptRunAsIsNotDBotRoleValidator validator

    Then:
     - make sure the script that has runas field = DBotRole fails the validation
    """
    content_items = (
        create_script_object(
            paths=["name", "runas"],
            values=["InvalidScript", "DBotRole"],
        ),
        create_script_object(),
    )

    results = ScriptRunAsIsNotDBotRoleValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == 1
    assert results[0].content_object.name == "InvalidScript"


def test_DuplicatedScriptNameValidatorListFiles_obtain_invalid_content_items(
    mocker, graph_repo: Repo
):
    """
    Given
        - A content repo with 8 scripts:
        - 2 scripts (test_alert1, test_incident1) supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert2, test_incident2) not supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert3, test_incident3) supported by MP V2 with SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert4, test_incident4) where only one is supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
    When
        - running DuplicatedScriptNameValidatorListFiles obtain_invalid_content_items function.
    Then
        - Validate that only the first pair of scripts appear in the results, and the rest of the scripts is valid.
    """
    mocker.patch.object(
        SC109_script_name_is_not_unique_validator,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    pack = graph_repo.create_pack()

    pack.create_script("test_incident_1").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_1").set_data(marketplaces=MP_XSOAR_AND_V2)

    pack.create_script("test_incident_2").set_data(marketplaces=MP_XSOAR)
    pack.create_script("test_alert_2").set_data(marketplaces=MP_XSOAR)

    pack.create_script("test_incident_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )
    pack.create_script("test_alert_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )

    pack.create_script("test_incident_4").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_4").set_data(marketplaces=MP_XSOAR)

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = DuplicatedScriptNameValidatorListFiles().obtain_invalid_content_items(
        [script.object for script in pack.scripts]
    )

    assert len(results) == 1
    assert "test_alert_1.yml" == results[0].content_object.path.name


def test_DuplicatedScriptNameValidatorAllFiles_obtain_invalid_content_items(
    mocker, graph_repo: Repo
):
    """
    Given
        - A content repo with 8 scripts:
        - 2 scripts (test_alert1, test_incident1) supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert2, test_incident2) not supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert3, test_incident3) supported by MP V2 with SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert4, test_incident4) where only one is supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
    When
        - running DuplicatedScriptNameValidatorAllFiles obtain_invalid_content_items function.
    Then
        - Validate that only the first pair of scripts appear in the results, and the rest of the scripts is valid.
    """
    mocker.patch.object(
        SC109_script_name_is_not_unique_validator,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    pack = graph_repo.create_pack()

    pack.create_script("test_incident_1").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_1").set_data(marketplaces=MP_XSOAR_AND_V2)

    pack.create_script("test_incident_2").set_data(marketplaces=MP_XSOAR)
    pack.create_script("test_alert_2").set_data(marketplaces=MP_XSOAR)

    pack.create_script("test_incident_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )
    pack.create_script("test_alert_3").set_data(
        skipprepare=[SKIP_PREPARE_SCRIPT_NAME], marketplaces=MP_V2
    )

    pack.create_script("test_incident_4").set_data(marketplaces=MP_XSOAR_AND_V2)
    pack.create_script("test_alert_4").set_data(marketplaces=MP_XSOAR)

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = DuplicatedScriptNameValidatorAllFiles().obtain_invalid_content_items(
        [script.object for script in pack.scripts]
    )

    assert len(results) == 1
    assert "test_alert_1.yml" == results[0].content_object.path.name
