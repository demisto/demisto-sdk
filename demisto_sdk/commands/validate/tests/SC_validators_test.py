from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC100_script_has_invalid_version import (
    ScriptNameIsVersionedCorrectlyValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator_core_packs import (
    IsScriptArgumentsContainIncidentWordValidatorCorePacks,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC106_script_runas_dbot_role_validator import (
    ScriptRunAsIsNotDBotRoleValidator,
)
from TestSuite.repo import ChangeCWD

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

    results = ScriptNameIsVersionedCorrectlyValidator().is_valid(content_items)
    assert len(results) == 1
    assert results[0].content_object.name == "Testv2"

    fix_result = ScriptNameIsVersionedCorrectlyValidator().fix(
        results[0].content_object
    )
    assert fix_result.content_object.name == "TestV2"


def test_IsScriptArgumentsContainIncidentWordValidatorCorePacks_is_valid(mocker):
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
    mocker.patch(
        "demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator_core_packs.get_core_pack_list",
        return_value=["PackWithInvalidScript"],
    )

    content_items = (
        create_script_object(
            paths=["name", "args"],
            values=["InvalidScript", [{"name": "incident-id", "description": "test"}]],
            pack_info={"name": "PackWithInvalidScript"},
        ),
        create_script_object(
            paths=["args"],
            values=[
                [{"name": "incident-id", "description": "test", "deprecated": True}],
            ],
            pack_info={"name": "PackWithValidScript"},
        ),
        create_script_object(),
    )

    with ChangeCWD(REPO.path):
        results = IsScriptArgumentsContainIncidentWordValidatorCorePacks().is_valid(
            content_items
        )
    assert len(results) == 1
    assert results[0].content_object.name == "InvalidScript"


def test_ScriptRunAsIsNotDBotRoleValidator_is_valid():
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

    results = ScriptRunAsIsNotDBotRoleValidator().is_valid(content_items)
    assert len(results) == 1
    assert results[0].content_object.name == "InvalidScript"
