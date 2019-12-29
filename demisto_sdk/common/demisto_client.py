import demisto_client
import os


class Client:
    """A base class of tool classes which use the demisto_client library.
        Attributes:
            client (DefaultApi): Demisto-SDK client object.
        """
    DEMISTO_API_KEY_ENV = 'DEMISTO_API_KEY'

    def __init__(self, base_url: str, insecure: bool = False):
        self.client = demisto_client.configure(base_url=base_url,
                                               api_key=self.get_api_key(),
                                               verify_ssl=not insecure)

    def get_api_key(self):
        """Retrieve the API Key

                Raises:
                    RuntimeError: if the API Key environment variable is not found

                Returns:
                    str: API Key
                """
        ans = os.environ.get(self.DEMISTO_API_KEY_ENV, None)
        if ans is None:
            raise RuntimeError(f'Error: Environment variable {self.DEMISTO_API_KEY_ENV} not found')

        return ans
