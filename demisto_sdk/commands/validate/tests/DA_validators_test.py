from demisto_sdk.commands.validate.tests.test_tools import create_dashboard_object
from demisto_sdk.commands.validate.validators.DA_validators.DA100_dashboard_contains_forbidden_fields import (
    IsDashboardContainForbiddenFieldsValidator,
)
from demisto_sdk.commands.validate.validators.DA_validators.DA101_dashboard_contains_necessary_fields import (
    IsDashboardContainNecessaryFieldsValidator,
)


def test_IsDashboardContainForbiddenFieldsValidator_is_valid():
    """
    Given:
        - Dashboard content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the Dashboard who has a field with name 'system'
        - Ensure that no ValidationResult returned
          when `system` field does not exist
    """
    dashboard = create_dashboard_object(paths=["system"], values=["foo"])

    # not valid
    results = IsDashboardContainForbiddenFieldsValidator().is_valid([dashboard])
    assert results[0].message == "the following fields need to be removed: system."

    # valid
    dashboard.data["system"] = None
    assert not IsDashboardContainForbiddenFieldsValidator().is_valid([dashboard])


def test_IsDashboardContainNecessaryFieldsValidator_is_valid():
    """
    Given:
        - Dashboard content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned when all required fields exist.
        - Ensure that the ValidationResult returned
          for the dashboard whose 'fromDate' field is missing.
    """
    # valid
    dashboard = create_dashboard_object()
    assert not IsDashboardContainNecessaryFieldsValidator().is_valid([dashboard])

    # not valid
    dashboard.data["fromDate"] = None
    result = IsDashboardContainNecessaryFieldsValidator().is_valid([dashboard])
    assert (
        result[0].message
        == "the following fields are missing and need to be added: fromDate."
    )


def test_IsDashboardContainForbiddenFieldsValidator_fix():
    """
    Given:
        - invalid dashboard that has 'system' field
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `system` has the value None
    """
    dashboard = create_dashboard_object(paths=["system"], values=["foo"])
    IsDashboardContainForbiddenFieldsValidator().invalid_fields[
        "Confluera Dashboard"
    ] = ["system"]
    result = IsDashboardContainForbiddenFieldsValidator().fix(dashboard)
    assert result.message == "removed the following fields system."
    assert not dashboard.data.get("system")
