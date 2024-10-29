class DemistoSDK:
    """
    The core class for the SDK.
    """

    def __init__(self):
        self.configuration = None


def get_config() -> DemistoSDK:
    # Initialize and return your DemistoSDK instance here
    sdk_instance = DemistoSDK()
    return sdk_instance
