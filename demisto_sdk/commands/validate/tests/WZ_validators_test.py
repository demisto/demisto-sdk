import pytest

from demisto_sdk.commands.content_graph.objects import Wizard
from demisto_sdk.commands.validate.validators.WZ_validators.WZ104_is_wrong_link_in_wizard import (
    IsWrongLinkInWizardValidator,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_wizard_object,
)


def test_IsWrongLinkInWizardValidator_valid_case():
    wizard = create_wizard_object()
    assert not IsWrongLinkInWizardValidator().is_valid([wizard])


def test_IsWrongLinkInWizardValidator_invalid_case():
    wizard = create_wizard_object(dict_to_update={'wizard': {'fetching_integrations': []}})
    res = IsWrongLinkInWizardValidator().is_valid([wizard])
    assert not res
