from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import \
    ClassifierBaseConverter
from demisto_sdk.commands.common.constants import FileType


class ClassifierSixConverter(ClassifierBaseConverter):

    def __init__(self, pack: Pack):
        super().__init__(pack)

    def convert_dir(self) -> int:
        """
        Converts old classifier in Classifiers dir to the 6.0.0 classifier convention.
        Splits the classifier of 5_9_9 to 6_0_0 classifier and 6_0_0 mapper if exists.
        Returns:
            (int): 0 if convert finished successfully, 1 otherwise.
        """
        old_classifiers = self.get_entities_by_entity_type(self.pack.classifiers, FileType.OLD_CLASSIFIER)
        return 0
