from demisto_sdk.commands.common.tools import run_command, print_color, LOG_COLORS


class Config:
    """Configure

    Attributes:
        base_url(str): Demisto's Base URL.
        api_key(str): Demisto API key.
    """

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key

    def configure(self):
        """Configure the env variables DEMISTO_BASE_URL and DEMISTO_API_KEY

        Returns:
            None.
        """
        while self.base_url is None or self.base_url == '':
            self.base_url = str(input(f"Please insert Demisto's Base URL: "))

        run_command(f"export DEMISTO_BASE_URL={self.base_url}")

        while self.api_key is None or self.api_key == '':
            self.api_key = str(input(f"Please insert Demisto's API KEY: "))

        print_color("Configuration Done", LOG_COLORS.GREEN)
