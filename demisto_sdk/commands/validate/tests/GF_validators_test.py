from demisto_sdk.commands.validate.tests.test_tools import create_generic_field_object
from demisto_sdk.commands.validate.validators.GF_validators.GF100_generic_field_group import (
    REQUIRED_GROUP_VALUE,
    GenericFieldGroupValidator,
)
from demisto_sdk.commands.validate.validators.GF_validators.GF101_generic_field_id_prefix_validate import (
    GenericFieldIdPrefixValidateValidator,
)


def test_GenericFieldIdPrefixValidateValidator_is_valid():
    """
    Given:
        - GenericField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'id' without `generic_` prefix
        - Ensure that no ValidationResult returned
          when `id` field with `generic_` prefix
    """
    generic_field = create_generic_field_object(paths=["id"], values=["foo"])

    # not valid
    results = GenericFieldIdPrefixValidateValidator().is_valid([generic_field])
    assert results[0].message == "foo is not a valid id, it should start with generic_."

    # valid
    generic_field.object_id = "generic_foo"
    assert not GenericFieldIdPrefixValidateValidator().is_valid([generic_field])


def test_GenericFieldGroupValidator_is_valid():
    """
    Given:
        - GenericField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'group' field is not valid
        - Ensure that no ValidationResult returned when group field set to 4
    """
    # not valid
    generic_field = create_generic_field_object(paths=["group"], values=[0])
    assert GenericFieldGroupValidator().is_valid([generic_field])

    # valid
    generic_field.group = REQUIRED_GROUP_VALUE
    assert not GenericFieldGroupValidator().is_valid([generic_field])


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
    assert result.message == f"set the `group` field to {REQUIRED_GROUP_VALUE}."
    assert generic_field.group == REQUIRED_GROUP_VALUE
