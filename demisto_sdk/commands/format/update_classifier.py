from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class ClassifierJSONFormat(BaseUpdateJSON):
    """ClassifierJSONFormat class is designed to update dashboard JSON file according to Demisto's convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(self, input='', output='', path='', from_version=''):
        super().__init__(input, output, path, from_version)

    def format_file(self):
        """Manager function for the integration YML updater."""
        pass
