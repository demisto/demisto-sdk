import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_generic_field_object
from demisto_sdk.commands.validate.validators.GF_validators.GF100_generic_field_group import (
    REQUIRED_GROUP_VALUE,
    GenericFieldGroupValidator,
)
from demisto_sdk.commands.validate.validators.GF_validators.GF101_generic_field_id_prefix_validate import (
    GenericFieldIdPrefixValidateValidator,
)


def test_GenericFieldIdPrefixValidateValidator_not_valid():
    """
    Given:
        - GenericField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'id' without `generic_` prefix
    """
    generic_field = create_generic_field_object(paths=["id"], values=["foo"])
    results = GenericFieldIdPrefixValidateValidator().is_valid([generic_field])
    assert (
        results[0].message
        == "ID `foo` is not valid, it should start with the prefix `generic_`."
    )


def test_GenericFieldIdPrefixValidateValidator_fix():
    """
    Given:
        - invalid GenericField that 'id' without `generic_` prefix
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `id` changing to with `generic_` prefix
    """

    generic_field = create_generic_field_object(paths=["id"], values=["foo"])

    result = GenericFieldIdPrefixValidateValidator().fix(generic_field)  # type:ignore
    assert result
    assert result.message == "Change the value of `id` field to `generic_foo`."


def test_GenericFieldGroupValidator_not_valid():
    """
    Given:
        - GenericField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'group' field is not valid
    """
    generic_field = create_generic_field_object(paths=["group"], values=["0"])
    assert GenericFieldGroupValidator().is_valid([generic_field])


def test_GenericFieldGroupValidator_fix():
    """
    Given:
        - invalid GenericField that 'group' field is not 4
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `group` is set to 4
    """
    generic_field = create_generic_field_object(paths=["group"], values=["0"])
    result = GenericFieldGroupValidator().fix(generic_field)
    assert result.message == f"`group` field is set to {REQUIRED_GROUP_VALUE}."
    assert generic_field.group == REQUIRED_GROUP_VALUE
