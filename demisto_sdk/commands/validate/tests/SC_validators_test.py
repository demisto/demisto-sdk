from demisto_sdk.commands.validate.tests.test_tools import (
    create_script_object,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC105_incident_not_in_args_validator import (
    IsScriptArgumentsContainIncidentWordValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC106_script_runas_dbot_role_validator import (
    ScriptRunAsIsNotDBotRoleValidator,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC109_script_name_is_not_unique_validator import (
    DuplicatedScriptNameValidator,
)
from TestSuite.repo import Repo


def test_IsScriptArgumentsContainIncidentWordValidator_is_valid():
    """
    Given:
     - 1 script that has the word incident in its arguments and is not deprecated
     - 1 script that has the word incident in its arguments and is deprecated
     - 1 script that does not have the word incident in its arguments

    When:
     - Running the IsScriptArgumentsContainIncidentWordValidator validator

    Then:
     - make sure the script with the argument that has "incident" fails the validation
    """
    content_items = (
        create_script_object(
            paths=["name", "args"],
            values=["InvalidScript", [{"name": "incident-id", "description": "test"}]],
        ),
        create_script_object(
            paths=["args"],
            values=[
                [{"name": "incident-id", "description": "test", "deprecated": True}]
            ],
        ),
        create_script_object(),
    )

    results = IsScriptArgumentsContainIncidentWordValidator().is_valid(content_items)
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


def test_DuplicatedScriptNameValidator_is_valid(graph_repo: Repo):
    """
    Given
        - A content repo with 8 scripts:
        - 2 scripts (test_alert1, test_incident1) supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert2, test_incident2) not supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert3, test_incident3) supported by MP V2 with SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
        - 2 scripts (test_alert4, test_incident4) where only one is supported by MP V2 without SKIP_PREPARE_SCRIPT_NAME = "script-name-incident-to-alert".
    When
        - running DuplicatedScriptNameValidator is_valid function.
    Then
        - Validate that only the first pair of scripts appear in the results, and teh rest of the scripts is valid.
    """
    pack = graph_repo.create_pack()

    script1 = pack.create_script()
    script2 = pack.create_script()

    script1.set_data(name="test")
    script2.set_data(name="test")

    graph_repo.create_graph()

    from TestSuite.test_tools import ChangeCWD

    with ChangeCWD(graph_repo.path):
        results = DuplicatedScriptNameValidator().is_valid([script1.object, script2.object])

    assert len(results) == 1
    assert "test_alert_1.yml" == results[0].content_object.path.name
