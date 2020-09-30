from demisto_sdk.commands.common.update_id_set import re_create_id_set


class IDSetCreator:
    def __init__(self, output: str = '', print_logs: bool = True):
        """IDSetCreator

        Args:
            output (str, optional): The output path. Set to None to avoid creation of a file. '' means the default path.
             Defaults to 'Tests/id_set.json'.
            print_logs (bool, optional): Print log output. Defaults to True.
        """
        self.output = output
        self.print_logs = print_logs

    def create_id_set(self):
        return re_create_id_set(id_set_path=self.output, print_logs=self.print_logs)
