from demisto_sdk.commands.integration_diff.integration_diff_detector import \
    IntegrationDiffDetector


class TestIntegrationDiffDetector:

    NEW_YAML = {
        'commands': [
            {

            }
        ]
    }

    def test_integration_diff(self, pack):
        return IntegrationDiffDetector()
