from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers import (
    IntegrationParser,
    ModelingRuleParser,
    ScriptParser,
)
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST110_is_valid_scheme import (
    SchemaValidator,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST111_no_exclusions_schema import (
    StrictSchemaValidator,
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
        "'Connect', 'Collect', 'Optimize', 'Mirroring'"
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
            "Missing sectionorder key. Add sectionorder to the top of your YAML file and specify the order of the "
            "Connect, Collect, Optimize, Mirroring sections (at least one is required)."
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

    def test_valid_section_mirroring(self, pack: Pack):
        """
        Given:
            - an integration which contains the mirroring section
        When:
            - executing the IntegrationParser
        Then:
            - the integration is valid and no structure error is being raised
        """
        integration = pack.create_integration(yml=load_yaml("integration.yml"))
        integration_info = integration.yml.read_dict()
        curr_config = integration_info["configuration"]
        curr_config[0]["section"] = "Mirroring"
        integration.yml.update({"sectionorder": ["Connect", "Mirroring"]})
        integration.yml.update({"configuration": curr_config})

        integration_parser = IntegrationParser(
            Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
        )

        results = SchemaValidator().obtain_invalid_content_items([integration_parser])
        assert len(results) == 0
