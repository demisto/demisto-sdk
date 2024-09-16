from demisto_sdk.commands.validate.tests.test_tools import create_dashboard_object
from demisto_sdk.commands.validate.validators.DA_validators.DA100_dashboard_contains_forbidden_fields import (
    IsDashboardContainForbiddenFieldsValidator,
)
from demisto_sdk.commands.validate.validators.DA_validators.DA101_dashboard_contains_necessary_fields import (
    IsDashboardContainNecessaryFieldsValidator,
)


def test_IsDashboardContainForbiddenFieldsValidator_obtain_invalid_content_items():
    """
    Given:
        - Dashboard content items.
    When:
        - run obtain_invalid_content_items method.
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
    results = IsDashboardContainForbiddenFieldsValidator().obtain_invalid_content_items(
        [dashboard]
    )
    assert (
        "The 'system' fields need to be removed from Confluera Dashboard."
        in results[0].message
    )
    assert (
        "The 'owner' fields need to be removed from widget test Widget listed under Confluera Dashboard."
        in results[0].message
    )

    # valid
    del dashboard.data_dict["system"]
    del dashboard.layout[0]["widget"]["owner"]
    assert (
        not IsDashboardContainForbiddenFieldsValidator().obtain_invalid_content_items(
            [dashboard]
        )
    )


def test_IsDashboardContainNecessaryFieldsValidator_obtain_invalid_content_items():
    """
    Given:
        - Dashboard content items.
    When:
        - run obtain_invalid_content_items method.
    Then:
        - Ensure that no ValidationResult returned when all required fields exist.
        - Ensure that the ValidationResult returned
          for the dashboard whose 'fromDate' field is missing.
    """
    # valid
    dashboard = create_dashboard_object()
    assert (
        not IsDashboardContainNecessaryFieldsValidator().obtain_invalid_content_items(
            [dashboard]
        )
    )

    # not valid
    del dashboard.data_dict["fromDate"]
    del dashboard.layout[0]["widget"]["dateRange"]["toDate"]
    result = IsDashboardContainNecessaryFieldsValidator().obtain_invalid_content_items(
        [dashboard]
    )

    assert (
        "The 'fromDate' fields are missing from Confluera Dashboard and need to be added."
        in result[0].message
    )
    assert (
        "The 'toDate' fields are missing from detcount Widget listed under Confluera Dashboard and need to be added."
        in result[0].message
    )


def test_fix_IsDashboardContainForbiddenFieldsValidator():
    """
    Given:
        - Dashboard content items with forbidden fields.
    When:
        - Running validate with the --fix flag.
    Then:
        - Remove the forbidden fields.
    """
    dashboard = create_dashboard_object(
        ["system", "isCommon", "shared", "owner"], [None] * 4
    )

    res = IsDashboardContainForbiddenFieldsValidator().fix(dashboard)

    assert (
        not IsDashboardContainForbiddenFieldsValidator().obtain_invalid_content_items(
            [res.content_object]
        )
    )
