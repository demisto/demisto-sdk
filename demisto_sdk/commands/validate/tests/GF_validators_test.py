import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_generic_field_object
from demisto_sdk.commands.validate.validators.GF_validators.GF101_generic_field_id_prefix_validate import (
    GenericFieldIdPrefixValidateValidator,
)


def test_GenericFieldIdPrefixValidateValidator_is_valid():
    content_item = create_generic_field_object(paths=["id"], values=["foo"])
    results = GenericFieldIdPrefixValidateValidator().is_valid([content_item])
    assert (
        results[0].message
        == "ID `foo` is not valid, it should start with the prefix `generic_`."
    )


def test_GenericFieldIdPrefixValidateValidator_fix():
    generic_field = create_generic_field_object(paths=["id"], values=["foo"])

    result = GenericFieldIdPrefixValidateValidator().fix(generic_field)  # type:ignore
    assert result
    assert result.message == "Change the value of `id` field to `generic_foo`."
