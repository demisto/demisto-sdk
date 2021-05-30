from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import \
    ClassifierBaseConverter


class ClassifierBelowSixConverter(ClassifierBaseConverter):

    def __init__(self, pack: Pack):
        super().__init__(pack)

    def convert_dir(self) -> int:
        """
        Converts new classifier in Classifiers dir to the below 6.0.0 classifier convention.
        Returns:
            (int): 0 if convert finished successfully, 1 otherwise.
        """
        return 0
