import pytest

from demisto_sdk.commands.common.constants import (
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
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
from demisto_sdk.commands.validate.validators.SC_validators.SC110_wrapper_script_missing_dependson_all_files import (
    WrapperScriptMissingDependsOnValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.SC_validators.SC110_wrapper_script_missing_dependson_list_files import (
    WrapperScriptMissingDependsOnValidatorListFiles,
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


# --- SC110 Tests ---


class _FakeAction:
    """Lightweight stand-in for AgentixAction nodes returned by the graph query."""

    def __init__(
        self, underlying_content_item_id, underlying_content_item_type="script"
    ):
        self.underlying_content_item_id = underlying_content_item_id
        self.underlying_content_item_type = underlying_content_item_type


class _FakeGraph:
    """Fake graph that returns a pre-configured list of AgentixActions."""

    def __init__(self, wrapped_script_ids):
        self._actions = [_FakeAction(sid) for sid in wrapped_script_ids]
        self.last_query_ids = None

    def get_agentix_actions_using_content_items(self, content_item_ids):
        self.last_query_ids = list(content_item_ids)
        # Mimic the real query: when ids are provided, only return matching ones.
        if not content_item_ids:
            return list(self._actions)
        ids = set(content_item_ids)
        return [a for a in self._actions if a.underlying_content_item_id in ids]


def _install_fake_graph(monkeypatch, wrapped_script_ids):
    """Replace BaseValidator.graph_interface with a fake graph for SC110 tests."""
    fake_graph = _FakeGraph(wrapped_script_ids)
    monkeypatch.setattr(BaseValidator, "graph_interface", fake_graph)
    return fake_graph


@pytest.mark.parametrize(
    "code, dependson, expected_invalid",
    [
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {"must": ["MyScript"]},
            False,
            id="valid: called command declared in dependson.must",
        ),
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {"should": ["MyScript"]},
            False,
            id="valid: called command declared in dependson.should",
        ),
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {"must": ["MyScript"], "should": ["OtherScript"]},
            False,
            id="valid: called command in must, extra entry in should",
        ),
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {},
            True,
            id="invalid: called command not declared in dependson",
        ),
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {"must": ["OtherScript"]},
            True,
            id="invalid: dependson.must has different command",
        ),
        pytest.param(
            "result = some_function()",
            {},
            False,
            id="valid: no executeCommand calls",
        ),
        pytest.param(
            'demisto.executeCommand("MyScript", {})',
            {"must": ["MyPack|MyScript"]},
            False,
            id="valid: pipe-prefixed pack name stripped correctly",
        ),
        pytest.param(
            'demisto.execute_command("MyScript", {})',
            {},
            True,
            id="invalid: execute_command (underscore variant) also detected",
        ),
        pytest.param(
            'demisto.execute_command("MyScript", {})',
            {"must": ["MyScript"]},
            False,
            id="valid: execute_command (underscore variant) declared in must",
        ),
        pytest.param(
            'demisto.executeCommand("ScriptA", {})\ndemisto.executeCommand("ScriptB", {})',
            {"must": ["ScriptA", "ScriptB"]},
            False,
            id="valid: multiple calls all declared",
        ),
        pytest.param(
            'demisto.executeCommand("ScriptA", {})\ndemisto.executeCommand("ScriptB", {})',
            {"must": ["ScriptA"]},
            True,
            id="invalid: one of multiple calls not declared",
        ),
        pytest.param(
            'demisto.executeCommand("ScriptA", {})\ndemisto.executeCommand("ScriptB", {})',
            {"must": ["ScriptA"], "should": ["ScriptB"]},
            False,
            id="valid: multiple calls split across must and should",
        ),
    ],
)
def test_WrapperScriptMissingDependsOnValidator_obtain_invalid_content_items(
    monkeypatch, code, dependson, expected_invalid
):
    """
    Given:
        - A script wrapped by an AgentixAction with various combinations of
          executeCommand calls and dependson declarations.
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - Scripts missing dependson entries for called commands produce a ValidationResult.
        - Scripts with all called commands declared (in must or should) pass validation.
        - Scripts with no executeCommand calls always pass.
        - Pipe-prefixed pack names in dependson are handled correctly.
    """
    content_item = create_script_object(
        paths=["dependson"],
        values=[dependson],
        code=code,
    )

    # Tell the fake graph this script is wrapped by an AgentixAction.
    _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    if expected_invalid:
        assert len(results) == 1
        assert content_item.name in results[0].message
    else:
        assert len(results) == 0


def test_WrapperScriptMissingDependsOnValidator_llm_script_is_skipped(monkeypatch):
    """
    Given:
        - An LLM script (isllm=True) that would otherwise fail (no dependson declared),
          and is wrapped by an AgentixAction.
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - LLM scripts are skipped entirely (no code to parse), so no ValidationResult is produced.
    """
    content_item = create_script_object(
        paths=["isllm"],
        values=[True],
    )

    _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert len(results) == 0


def test_WrapperScriptMissingDependsOnValidator_missing_commands_listed_in_message(
    monkeypatch,
):
    """
    Given:
        - A script wrapped by an AgentixAction that calls two commands via executeCommand
          but declares neither in dependson.
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - The ValidationResult message lists both missing command names.
    """
    code = (
        'demisto.executeCommand("CommandAlpha", {})\n'
        'demisto.executeCommand("CommandBeta", {})'
    )
    content_item = create_script_object(
        paths=["dependson"],
        values=[{}],
        code=code,
    )

    _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert len(results) == 1
    assert "CommandAlpha" in results[0].message
    assert "CommandBeta" in results[0].message


def test_WrapperScriptMissingDependsOnValidator_partial_missing_listed_in_message(
    monkeypatch,
):
    """
    Given:
        - A script wrapped by an AgentixAction that calls two commands but only declares
          one in dependson.must.
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - Only the undeclared command appears in the ValidationResult message.
        - The declared command does NOT appear in the missing list.
    """
    code = (
        'demisto.executeCommand("DeclaredScript", {})\n'
        'demisto.executeCommand("MissingScript", {})'
    )
    content_item = create_script_object(
        paths=["dependson"],
        values=[{"must": ["DeclaredScript"]}],
        code=code,
    )

    _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert len(results) == 1
    assert "MissingScript" in results[0].message
    assert "DeclaredScript" not in results[0].message


def test_WrapperScriptMissingDependsOnValidator_code_is_none_skipped(
    monkeypatch,
):
    """
    Given:
        - A script wrapped by an AgentixAction whose `.code` attribute is None
          (simulating an object loaded from the content graph, where `code` is
          excluded from serialisation).
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - The script is skipped because there is no code to parse, so no
          ValidationResult is produced.
    """
    code = 'demisto.executeCommand("MyScript", {})'
    content_item = create_script_object(
        paths=["dependson"],
        values=[{}],
        code=code,
    )
    # Simulate the object being loaded from the graph (code field is not persisted).
    content_item.code = None

    _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert len(results) == 0


def test_WrapperScriptMissingDependsOnValidator_not_wrapped_script_is_skipped(
    monkeypatch,
):
    """
    Given:
        - A script that calls a command via executeCommand without declaring it in
          dependson, but is NOT wrapped by any AgentixAction.
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - The script is skipped and no ValidationResult is produced, because the
          validation only applies to scripts wrapped by AgentixActions.
    """
    code = 'demisto.executeCommand("SomeCommand", {})'
    content_item = create_script_object(
        paths=["dependson"],
        values=[{}],
        code=code,
    )

    # Fake graph reports no wrapped scripts
    _install_fake_graph(monkeypatch, set())

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert len(results) == 0


def test_WrapperScriptMissingDependsOnValidator_only_wrapped_scripts_validated(
    monkeypatch,
):
    """
    Given:
        - Two scripts: one wrapped by an AgentixAction (missing dependson) and one
          not wrapped (also missing dependson).
    When:
        - Running WrapperScriptMissingDependsOnValidatorListFiles.obtain_invalid_content_items.
    Then:
        - Only the wrapped script produces a ValidationResult.
        - The unwrapped script is skipped.
    """
    code = 'demisto.executeCommand("SomeCommand", {})'
    wrapped_script = create_script_object(
        paths=["dependson", "commonfields.id", "name"],
        values=[{}, "WrappedScript", "WrappedScript"],
        code=code,
        name="WrappedScript",
    )
    unwrapped_script = create_script_object(
        paths=["dependson", "commonfields.id", "name"],
        values=[{}, "UnwrappedScript", "UnwrappedScript"],
        code=code,
        name="UnwrappedScript",
    )

    # Only the wrapped script's ID is reported by the fake graph
    _install_fake_graph(monkeypatch, {wrapped_script.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
            [wrapped_script, unwrapped_script]
        )
    )

    assert len(results) == 1
    assert wrapped_script.name in results[0].message


def test_WrapperScriptMissingDependsOnValidator_list_files_passes_script_ids_to_graph(
    monkeypatch,
):
    """
    Given:
        - The ListFiles subclass running on a specific changed script.
    When:
        - obtain_invalid_content_items is called.
    Then:
        - The graph query is restricted to the IDs of the scripts in scope
          (not an empty list, which would mean "all AgentixActions").
    """
    content_item = create_script_object(
        paths=["dependson"],
        values=[{}],
        code='demisto.executeCommand("SomeCommand", {})',
    )
    fake_graph = _install_fake_graph(monkeypatch, {content_item.object_id})

    WrapperScriptMissingDependsOnValidatorListFiles().obtain_invalid_content_items(
        [content_item]
    )

    assert fake_graph.last_query_ids == [content_item.object_id]


def test_WrapperScriptMissingDependsOnValidator_all_files_queries_all_actions(
    monkeypatch,
):
    """
    Given:
        - The AllFiles subclass running in ALL_FILES mode.
    When:
        - obtain_invalid_content_items is called.
    Then:
        - The graph query is called with an empty list, instructing it to return
          every AgentixAction in the graph (so wrapped scripts are detected even
          when only the script itself changed and not the wrapping action).
    """
    content_item = create_script_object(
        paths=["dependson"],
        values=[{}],
        code='demisto.executeCommand("SomeCommand", {})',
    )
    fake_graph = _install_fake_graph(monkeypatch, {content_item.object_id})

    results = (
        WrapperScriptMissingDependsOnValidatorAllFiles().obtain_invalid_content_items(
            [content_item]
        )
    )

    assert fake_graph.last_query_ids == []
    assert len(results) == 1
    assert content_item.name in results[0].message
