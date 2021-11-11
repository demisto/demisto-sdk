from demisto_sdk.commands.format.update_description import DescriptionFormat
from demisto_sdk.tests.constants_test import (
    SOURCE_DESCRIPTION_FORMATTED_CONTRIB_DETAILS,
    SOURCE_DESCRIPTION_WITH_CONTRIB_DETAILS,
    SOURCE_DESCRIPTION_WITHOUT_BETA_DESCRIPTION,
    SOURCE_DESCRIPTION_FORMATTED_WITH_BETA_DESCRIPTION)


class TestDescriptionFormat:
    def test_remove_community_partner_details(self):
        """
        Given
            - A description file that might contain community/partner details
        When
            - Run format on it
        Then
            - Ensure the details are deleted from the description file
        """
        with open(SOURCE_DESCRIPTION_FORMATTED_CONTRIB_DETAILS, 'r') as f:
            expected = f.read()
        formatter = DescriptionFormat(input=SOURCE_DESCRIPTION_WITH_CONTRIB_DETAILS)
        formatter.remove_community_partner_details()
        assert formatter.description_content == expected

    def test_format_beta_description(self):
        """
        Given
            - A description file for beta integration with no beta description
        When
            - Run format on it
        Then
            - Ensure the beta description is added to the description file
        """
        with open(SOURCE_DESCRIPTION_FORMATTED_WITH_BETA_DESCRIPTION, 'r') as f:
            expected = f.read()
        formatter = DescriptionFormat(input=SOURCE_DESCRIPTION_WITHOUT_BETA_DESCRIPTION)
        formatter.add_betaintegration_description()
        assert formatter.description_content == expected
