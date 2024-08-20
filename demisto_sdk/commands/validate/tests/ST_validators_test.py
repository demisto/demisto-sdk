from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.parsers import IntegrationParser, ScriptParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.ST_validators.ST110_is_valid_scheme import (
    SchemaValidator,
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
        Path(integration.path), list(MarketplaceVersions)
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert (
        results[0].message == "problematic field: ('name',) |"
        " error message: The field ('name',) is not required, but should not be None if it exists |"
        " error type : assertion_error"
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
    script_parser = ScriptParser(Path(script.path), list(MarketplaceVersions))

    results = SchemaValidator().obtain_invalid_content_items([script_parser])
    assert len(results) == 1
    assert (
        results[0].message == "problematic field: ('name',) |"
        " error message: The field ('name',) is required but missing |"
        " error type : value_error.missing"
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
        Path(integration.path), list(MarketplaceVersions)
    )

    results = SchemaValidator().obtain_invalid_content_items([integration_parser])
    assert len(results) == 1
    assert (
        results[0].message == "problematic field: ('EXTRA_FIELD',) |"
        " error message: The field ('EXTRA_FIELD',) is extra and extra fields not permitted |"
        " error type : value_error.extra"
    )
