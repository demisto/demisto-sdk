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
    dashboard = create_dashboard_object(
        paths=["system", "layout"],
        values=[
            "foo",
            [
                {
                    "id": "layout test",
                    "widget": {"owner": "owner test", "id": "widget test"},
                }
            ],
        ],
    )

    # not valid
    results = IsDashboardContainForbiddenFieldsValidator().is_valid([dashboard])
    assert (
        "the 'system' fields need to be removed from Confluera Dashboard."
        in results[0].message
    )
    assert (
        "the 'owner' fields need to be removed from widget test Widget in Confluera Dashboard."
        in results[0].message
    )

    # valid
    dashboard.data["system"] = None
    dashboard.data["layout"][0]["widget"]["owner"] = None
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
