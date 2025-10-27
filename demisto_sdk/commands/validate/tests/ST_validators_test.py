from pathlib import Path

import pytest

from TestSuite.test_tools import ChangeCWD
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers import (
    IntegrationParser,
    ModelingRuleParser,
    ScriptParser,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.strict_objects.trigger import _StrictTrigger
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_integration_object,
    create_script_object,
    create_playbook_object,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST110_is_valid_scheme import (
    SchemaValidator,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST111_no_exclusions_schema import (
    StrictSchemaValidator,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST112_is_quickaction_supported import (
    IsQuickactionSupported,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST113_supported_modules_is_not_empty import (
    SupportedModulesIsNotEmpty,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST114_is_supported_modules_subset_of_pack import (
    IsSupportedModulesSubsetOfPack,
)
from TestSuite.pack import Pack


def test_sanity_SchemaValidator():
    """
    Given:
        - a valid script
        - a valid integration
    When:
        - execute the SchemaValidator (ST110 validation) on the two valid content items
    Then:
        - Ensure the validation is passed without any errors (a sanity check)
    """
    content_items = [
        create_script_object(paths=["name"], values=["Test"]),
        create_integration_object(paths=["name"], values=["Test"]),
    ]

    results = SchemaValidator().obtain_invalid_content_items(content_items)
    assert len(results) == 0


def test_SchemaValidator_None_as_value(pack: Pack):
    """
    Given:
        - an integration which contains name field with None as a value
    When:
        - execute the SchemaValidator (ST110 validation) on the invalid integration
    Then:
        - Ensure the validation is failed due to "none is not an allowed value"
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"name": None})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert (
        results[0].message
        == "Structure error (assertion_error) in field name of integration_0.yml:"
        " The field name is not required, but should not be None if it exists"
    )


def test_SchemaValidator_missing_mandatory_field(pack: Pack):
    """
    Given:
        - a script which does not contain mandatory field 'name'
    When:
        - execute the SchemaValidator (ST110 validation) on the invalid script
    Then:
        - Ensure the validation is failed due to "field required"
    """
    script = pack.create_script(yml=load_yaml("script.yml"))
    script.yml.delete_key("name")
    script_parser = ScriptParser(
        Path(script.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([script_parser])
    assert len(results) == 1
    assert (
        results[0].message
        == "Structure error (value_error.missing) in field name of script0.yml:"
        " The field name is required but missing"
    )


def test_SchemaValidator_extra_field(pack: Pack):
    """
    Given:
        - an integration which contains extra field called 'EXTRA_FIELD'
    When:
        - execute the SchemaValidator (ST110 validation) on the invalid integration
    Then:
        - Ensure the validation is failed due to "extra fields not permitted"
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"EXTRA_FIELD": "EXTRA_FIELD"})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert (
        results[0].message
        == "Structure error (value_error.extra) in field EXTRA_FIELD of integration_0.yml:"
        " The field EXTRA_FIELD is extra and extra fields not permitted"
    )


def test_modeling_rule_parser_sanity_check(pack: Pack):
    """
    Given:
        - a modeling rule which contains valid yml and schema (a json file)
    When:
        - execute the ModelingRuleParser
    Then:
        - Ensure there are no structure errors
    """
    modeling_rule = pack.create_modeling_rule(
        yml={
            "id": "Tanium_ModelingRule",
            "name": "Tanium",
            "fromversion": "8.2.0",
            "toversion": "6.99.99",
            "tags": "",
            "rules": "",
            "schema": "",
        },
        schema={
            "tanium_integrity_monitor_raw": {
                "_raw_log": {"type": "string", "is_array": False}
            }
        },
    )
    modeling_rule_parser = ModelingRuleParser(
        path=modeling_rule.yml.obj_path,
        pack_marketplaces=[MarketplaceVersions.XSOAR],
        pack_supported_modules=[],
    )
    assert modeling_rule_parser.structure_errors == []


def test_modeling_rule_parser_errors_check(pack: Pack):
    """
    Given:
        - a modeling rule which contains invalid yml and schema (a json file)
    When:
        - execute the ModelingRuleParser
    Then:
        - Ensure there are two structure errors of the expected types
    """
    modeling_rule = pack.create_modeling_rule(
        yml={
            "id": "Tanium_ModelingRule",
            "name": "Tanium",
            # no fromversion field in the yml which is a required field
            "toversion": "6.99.99",
            "tags": "",
            "rules": "",
            "schema": "",
        },
        schema={
            "tanium_integrity_monitor_raw": {
                "_raw_log": {
                    "type": "string",
                    "is_array": "dummy string - not boolean!",  # should be a boolean field
                }
            }
        },
    )

    modeling_rule_parser = ModelingRuleParser(
        path=modeling_rule.yml.obj_path,
        pack_marketplaces=[MarketplaceVersions.XSOAR],
        pack_supported_modules=[],
    )

    assert len(modeling_rule_parser.structure_errors) == 2

    error_messages = {e.error_message for e in modeling_rule_parser.structure_errors}
    error_types = {e.error_type for e in modeling_rule_parser.structure_errors}

    assert {
        "field required",
        "value could not be parsed to a boolean",
    } == error_messages
    assert {"value_error.missing", "type_error.bool"} == error_types


def test_pack_parser_sanity_check(pack: Pack):
    """
    Given:
        - a pack which contains valid RN and pack_metadata files
    When:
        - execute the PackParser
    Then:
        - Ensure there are no structure errors
    """
    pack.create_release_notes_config(version="5.0.0", content={"breakingChanges": True})
    pack_parser = PackParser(path=pack.path)
    assert pack_parser.structure_errors == []


def test_pack_parser_errors_check(pack: Pack):
    """
    Given:
        - a pack which contains invalid RN and invalid pack_metadata files
    When:
        - execute the PackParser
    Then:
        - Ensure there are two structure errors of the expected types
    """
    # invalid value for breakingChanges field (should be a boolean)
    pack.create_release_notes_config(
        version="1.0.0", content={"breakingChanges": "aaa"}
    )

    pack.pack_metadata.update(
        {
            "name": "name",
            "description": "here be description",
            # invalid str for 'support' key ->
            # should contain one of those options ["xsoar", "partner", "community", "developer"]
            "support": "aaa",
            "url": "https://paloaltonetworks.com",
            "author": "Cortex XSOAR",
            "currentVersion": "1.0.0",
            "tags": [],
            "categories": [],
            "useCases": [],
            "keywords": [],
        }
    )

    pack_parser = PackParser(path=pack.path)

    assert len(pack_parser.structure_errors) == 2

    error_messages = {e.error_message for e in pack_parser.structure_errors}
    error_types = {e.error_type for e in pack_parser.structure_errors}

    assert {
        "value could not be parsed to a boolean",
        "value is not a valid enumeration member; permitted: 'xsoar', 'partner', 'community', 'developer'",
    } == error_messages
    assert {"type_error.bool", "type_error.enum"} == error_types


def test_invalid_section_order(pack: Pack):
    """
    Given:
        - an integration which contains invalid section order
    When:
        - executing the IntegrationParser
    Then:
        - the integration is invalid and the correct error message is returned
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"sectionorder": ["Connect", "Run"]})

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert results[0].message == (
        "Structure error (type_error.enum) in field sectionorder,1 of integration_0.yml: "
        "value is not a valid enumeration member; permitted: "
        "'Connect', 'Collect', 'Optimize', 'Mirroring', 'Result'"
    )


def test_missing_section_order(pack: Pack):
    """
    Given:
        - an integration with a missing section order
    When:
        - executing the IntegrationParser
    Then:
        - the validation does not fail as it is only addressed in ST111
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.delete_key("sectionorder")

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 0


def test_invalid_section(pack: Pack):
    """
    Given:
        - an integration which contains invalid section clause in one of its configuration objects
    When:
        - executing the IntegrationParser
    Then:
        - the integration is invalid and the correct error message is returned
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    curr_config = integration.yml.read_dict()["configuration"]
    curr_config[0]["section"] = "Run"
    integration.yml.update({"configuration": curr_config})

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert results[0].message == (
        "Structure error (assertion_error) in field configuration of integration_0.yml: "
        "section Run of URL is not present in section_order ['Connect']"
    )


def test_missing_section(pack: Pack):
    """
    Given:
        - an integration with a missing section clause in one of its configuration objects
    When:
        - executing the IntegrationParser
    Then:
        - the validation does not fail as it is only addressed in ST111
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    curr_config = integration.yml.read_dict()["configuration"]
    curr_config[0].pop("section")
    integration.yml.update({"configuration": curr_config})

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 0


def test_SchemaValidator_isCloudProviderIntegration_true(pack: Pack):
    """
    Given:
        - An integration with `isCloudProviderIntegration` set to True
    When:
        - Executing the SchemaValidator (ST110 validation)
    Then:
        - Ensure the validation passes
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"isCloudProviderIntegration": True})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 0


def test_SchemaValidator_isCloudProviderIntegration_false(pack: Pack):
    """
    Given:
        - An integration with `isCloudProviderIntegration` set to False
    When:
        - executing the SchemaValidator (ST110 validation)
    Then:
        - Ensure the validation passes
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"isCloudProviderIntegration": False})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 0


def test_SchemaValidator_isCloudProviderIntegration_none(pack: Pack):
    """
    Given:
        - An integration with `isCloudProviderIntegration` set to None
    When:
        - Executing the SchemaValidator (ST110 validation)
    Then:
        - Ensure the validation fails
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"isCloudProviderIntegration": None})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert (
        "The field isCloudProviderIntegration is not required, but should not be None if it exists"
        in results[0].message
    )


def test_SchemaValidator_isCloudProviderIntegration_invalid_type(pack: Pack):
    """
    Given:
       - An integration with `isCloudProviderIntegration` set to a non-boolean value
    When:
        - Executing the SchemaValidator (ST110 validation)
    Then:
        - Ensure the validation fails
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"isCloudProviderIntegration": "not a boolean"})
    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert "value could not be parsed to a boolean" in results[0].message


class TestST111:
    def test_invalid_section_order(self):
        """
        Given:
            - an integration which contains invalid section order
        When:
            - executing the IntegrationParser
        Then:
            - the validation does not fail as it is only addressed in ST110
        """
        integration = create_integration_object(
            paths=["sectionorder"], values=[["Connect", "Run"]]
        )
        results = StrictSchemaValidator().obtain_invalid_content_items([integration])

        assert len(results) == 0

    def test_missing_section_order(self):
        """
        Given:
            - an integration with a missing section order
        When:
            - executing the IntegrationParser
        Then:
            - the integration is invalid and the correct error message is returned
        """
        integration = create_integration_object()
        integration.data.pop("sectionorder")
        results = StrictSchemaValidator().obtain_invalid_content_items([integration])

        assert len(results) == 1
        assert results[0].message == (
            "Missing 'sectionorder' key. Please add 'sectionorder' (lowercase) to the top of your YAML file and specify the order of the "
            "Connect, Collect, Optimize, Mirroring, Result sections (at least one is required)."
        )

    def test_invalid_section(self):
        """
        Given:
            - an integration which contains invalid section clause in one of its configuration objects
        When:
            - executing the IntegrationParser
        Then:
            - the validation does not fail as it is only addressed in ST110
        """
        integration = create_integration_object()
        curr_config = integration.data["configuration"]
        curr_config[0]["section"] = "Run"
        integration.data["configuration"] = curr_config

        results = StrictSchemaValidator().obtain_invalid_content_items([integration])
        assert len(results) == 0

    def test_missing_section(self, pack: Pack):
        """
        Given:
            - an integration with a missing section clause in one of its configuration objects
        When:
            - executing the IntegrationParser
        Then:
            - the integration is invalid and the correct error message is returned
        """
        integration = create_integration_object()
        curr_config = integration.data["configuration"]
        curr_config[0].pop("section")
        integration.data["configuration"] = curr_config

        results = StrictSchemaValidator().obtain_invalid_content_items([integration])
        assert len(results) == 1
        assert results[0].message == (
            f"Missing section for the following parameters: ['{curr_config[0].get('name')}'] "
            "Please specify the section for these parameters."
        )

    @pytest.mark.parametrize("section_type", ["Mirroring", "Result"])
    def test_valid_section(self, pack: Pack, section_type: str):
        """
        Given:
            - an integration which contains a specific section (Mirroring or Result)
        When:
            - executing the IntegrationParser
        Then:
            - the integration is valid and no structure error is being raised
        """
        integration = pack.create_integration(yml=load_yaml("integration.yml"))
        integration_info = integration.yml.read_dict()
        curr_config = integration_info["configuration"]
        curr_config[0]["section"] = section_type
        integration.yml.update({"sectionorder": ["Connect", section_type]})
        integration.yml.update({"configuration": curr_config})

        integration_parser = IntegrationParser(
            Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
        )

        results = SchemaValidator().obtain_invalid_content_items([integration_parser])
        assert len(results) == 0


def test_missing_IsQuickactionSupported():
    """
    Given:
        - an integration with a command that has 'quickaction: true'
        - the integration is missing the 'supportsquickactions: true' field at the top level
    When:
        - execute the IsQuickactionSupported (ST112 validation) on the invalid integration
    Then:
        - Ensure the validation fails with the appropriate error message
    """
    integration = create_integration_object()

    integration.supports_quick_actions = False
    integration.commands[0].quickaction = True

    results = IsQuickactionSupported().obtain_invalid_content_items([integration])
    assert len(results) == 1
    assert results[0].message == (
        "The following commands are using quickaction without the integrations support: test-command. "
        "Remove quickaction or add supportsquickactions: true at the top level yml."
    )
    assert results[0].validator.error_code == "ST112"


def test_IsQuickactionSupported_with_supportsquickactions():
    """
    Given:
        - an integration with a command that has 'quickaction: true'
        - the integration also has 'supportsquickactions: true' at the top level
    When:
        - execute the IsQuickactionSupported (ST112 validation) on the valid integration
    Then:
        - Ensure the validation passes without any errors
    """
    integration = create_integration_object()

    integration.supports_quick_actions = True
    integration.commands[0].quickaction = True

    results = IsQuickactionSupported().obtain_invalid_content_items([integration])
    assert len(results) == 0


def test_IsQuickactionSupported_no_quickaction_commands():
    """
    Given:
        - an integration without any quickaction commands
        - the integration is missing 'supportsquickactions' (which is fine in this case)
    When:
        - execute the IsQuickactionSupported (ST112 validation) on the integration
    Then:
        - Ensure the validation passes without any errors
    """
    integration = create_integration_object()

    integration.supports_quick_actions = False
    integration.commands[0].quickaction = False

    results = IsQuickactionSupported().obtain_invalid_content_items([integration])
    assert len(results) == 0


def test_SupportedModulesIsNotEmpty_empty(pack: Pack):
    """
    Given:
        - A content item (integration) with an empty 'supportedModules' list.
    When:
        - Running the SupportedModulesIsNotEmpty validator.
    Then:
        - Ensure the validation fails with the correct error message.
    """
    integration = create_integration_object()
    integration.supportedModules = []

    results = SupportedModulesIsNotEmpty().obtain_invalid_content_items([integration])
    assert len(results) == 1
    assert (
        results[0].message
        == "supportedModules cannot be an empty list. To allow all modules, omit the field instead."
    )
    assert results[0].validator.error_code == "ST113"


def test_SupportedModulesIsNotEmpty_not_empty(pack: Pack):
    """
    Given:
        - A content item (integration) with a non-empty 'supportedModules' list.
    When:
        - Running the SupportedModulesIsNotEmpty validator.
    Then:
        - Ensure the validation passes without any errors.
    """
    integration = create_integration_object()

    results = SupportedModulesIsNotEmpty().obtain_invalid_content_items([integration])
    assert len(results) == 0


def test_SupportedModulesIsNotEmpty_missing_field(pack: Pack):
    """
    Given:
        - A content item (script) with the 'supportedModules' field missing.
    When:
        - Running the SupportedModulesIsNotEmpty validator.
    Then:
        - Ensure the validation passes without any errors (missing field is allowed).
    """
    script = create_script_object()
    script.supportedModules = ["C3", "X0", "X1", "X3"]

    results = SupportedModulesIsNotEmpty().obtain_invalid_content_items([script])
    assert len(results) == 0


def test_SchemaValidator_triggers_section__valid(pack: Pack):
    """
    Given:
        - An integration YAML file.
    When:
        - A valid 'triggers' section is added to the YAML and the SchemaValidator is run.
    Then:
        - The SchemaValidator should not report any errors related to the 'triggers' section.
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))

    integration.yml.update(
        {
            "triggers": [
                {
                    "conditions": [
                        {"name": "engine", "operator": "not_exists"},
                        {"name": "isEngineGroup", "operator": "not_exists"},
                    ],
                    "effects": [
                        {
                            "name": "longRunningPort",
                            "action": {"hidden": True, "required": False},
                        },
                        {"name": "credentials", "action": {"required": True}},
                    ],
                }
            ]
        }
    )

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 0


@pytest.mark.parametrize(
    "invalid_trigger, expected_error_substring",
    [
        pytest.param(
            {"conditions": [{"name": "engine", "operator": "exists"}]},
            "effects is required but missing",
            id="missing effects",
        ),
        pytest.param(
            {
                "conditions": [{"name": "engine", "operator": "invalid_operator"}],
                "effects": [
                    {"name": "effect1", "action": {"hidden": False, "required": True}}
                ],
            },
            "value is not a valid enumeration member",
            id="invalid operator",
        ),
        pytest.param(
            {
                "conditions": [{"name": "engine", "operator": "equal", "value": 123}],
                "effects": [
                    {
                        "name": "effect1",
                        "action": {"hidden": "string", "required": True},
                    }
                ],
            },
            "value could not be parsed to a boolean",
            id="invalid value type",
        ),
    ],
)
def test_SchemaValidator_triggers_section__invalid(
    pack: Pack, invalid_trigger, expected_error_substring
):
    """
    Given:
        - An integration YAML file with an invalid 'triggers' section.
        Case 1: Missing 'effects' section.
        Case 2: Invalid operator in a condition (not one of the allowed operators).
        Case 3: Incorrect value type in an effect (not a boolean or boolean string).
    When:
        - The SchemaValidator is running.
    Then:
        - The SchemaValidator should report an error related to the invalid trigger.
    """
    integration = pack.create_integration(yml=load_yaml("integration.yml"))
    integration.yml.update({"triggers": [invalid_trigger]})

    integration_parser = IntegrationParser(
        Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
    )
    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert expected_error_substring in results[0].message


def test_validate_automation_playbook_logic_valid_with_automation_pair():
    """
    Given:
        - A trigger with both automation_id and automation_type provided.
    When:
        - Instantiating StrictTrigger.
    Then:
        - Validation passes (no exception) and fields are set.
    """
    values = {
        "trigger_id": "t1",
        "trigger_name": "Test Trigger",
        "description": "desc",
        "suggestion_reason": "reason",
        "automation_type": "command",
        "automation_id": "Auto123",
    }
    returned = _StrictTrigger.validate_automation_playbook_logic(values=values)
    assert returned["automation_id"] == "Auto123"
    assert returned["automation_type"] == "command"


def test_validate_automation_playbook_logic_invalid_both_automation_and_playbook():
    """
    Given:
        - A trigger that provides both playbook_id and automation fields.
    When:
        - Instantiating StrictTrigger.
    Then:
        - ValidationError is raised with an appropriate message.
    """
    values = {
        "trigger_id": "t2",
        "trigger_name": "Bad Trigger",
        "description": "desc",
        "suggestion_reason": "reason",
        "playbook_id": "Playbook123",
        "automation_type": "playbook",
        "automation_id": "Auto456",
    }
    with pytest.raises(ValueError) as exc:
        _StrictTrigger.validate_automation_playbook_logic(values=values)
    assert "Cannot provide both automation fields and playbook_id." in str(exc.value)


def test_validate_automation_playbook_logic_invalid_partial_automation_fields():
    """
    Given:
        - A trigger that provides only automation_type without automation_id.
    When:
        - Instantiating StrictTrigger.
    Then:
        - ValidationError is raised indicating both must be provided together.
    """
    values = {
        "trigger_id": "t3",
        "trigger_name": "Partial Trigger",
        "description": "desc",
        "suggestion_reason": "reason",
        "automation_type": "command",
    }
    with pytest.raises(ValueError) as exc:
        _StrictTrigger.validate_automation_playbook_logic(values=values)
    assert "automation_id and automation_type must be provided together." in str(
        exc.value
    )


def test_IsSupportedModulesSubsetOfPack_invalid_modules():
    """
    Given:
        - A content item (integration) whose 'supportedModules' includes modules not allowed by its Content Pack.
    When:
        - Running the IsSupportedModulesSubsetOfPack (ST114) validator.
    Then:
        - The validation should fail with the appropriate error message and error code ST114.
    """
    with ChangeCWD(REPO.path):
        integration = create_integration_object(
            paths=["supportedModules"], values=[["C1", "X0"]],
            pack_info={"supportedModules": ["C1", "C3"]}
        )

        results = IsSupportedModulesSubsetOfPack().obtain_invalid_content_items([integration])
        assert len(results) == 1
        assert "'X0'" in results[0].message
        assert results[0].validator.error_code == "ST114"


def test_IsSupportedModulesSubsetOfPack_valid_subset():
    """
    Given:
        - A content item (script) whose 'supportedModules' are a subset of its Content Pack's supported modules.
    When:
        - Running the IsSupportedModulesSubsetOfPack (ST114) validator.
    Then:
        - The validation should pass.
    """
    with ChangeCWD(REPO.path):
        script = create_script_object(
            paths=["supportedModules"], values=[["C1", "X0"]],
            pack_info={"supportedModules": ["C1", "C3", "X0"]}
        )

        results = IsSupportedModulesSubsetOfPack().obtain_invalid_content_items([script])
        assert len(results) == 0


def test_IsSupportedModulesSubsetOfPack_inherit_pack_when_missing():
    """
    Given:
        - A content item (playbook) with no 'supportedModules' defined.
        - Its Content Pack defines supportedModules.
    When:
        - Running the IsSupportedModulesSubsetOfPack (ST114) validator.
    Then:
        - The validation should pass (item inherits pack modules).
    """
    with ChangeCWD(REPO.path):
        playbook = create_playbook_object(pack_info={"supportedModules": ["C1", "C3"]})
        playbook.supportedModules = None

        results = IsSupportedModulesSubsetOfPack().obtain_invalid_content_items([playbook])
        assert len(results) == 0
