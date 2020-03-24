from demisto_sdk.commands.common.update_id_set import re_create_id_set


class IDSetCreator:
    def __init__(self, output=''):
        self.output = output

    def create_id_set(self):
        return re_create_id_set(self.output)
