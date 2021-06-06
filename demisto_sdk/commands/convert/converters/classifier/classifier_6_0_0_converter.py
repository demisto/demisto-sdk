from typing import List, Set

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import \
    Classifier
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import \
    ClassifierBaseConverter


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
        old_classifiers: List[Classifier] = self.get_entities_by_entity_type(self.pack.classifiers,
                                                                                   FileType.OLD_CLASSIFIER)
        intersection_fields = self.get_classifiers_schema_intersection_fields()
        for old_classifier in old_classifiers:
            self.create_classifier_from_old_classifier(old_classifier, intersection_fields)
            self.create_mapper_from_old_classifier(old_classifier)

        return 0

    def create_classifier_from_old_classifier(self, old_classifier: Classifier,
                                              intersection_fields: Set[str]) -> None:
        """
        Receives classifier of format 5_9_9. Builds classifier of format 6_0_0 and above.
        Args:
            old_classifier (Classifier): Old classifier object
            intersection_fields (Set[str]): Intersection fields of 6_0_0 and 5_9_9 formats.

        Returns:
            (None): Creates a new corresponding classifier to 'old_classifier' by 6_0_0 file structure.
        """
        classifier_name_and_id = self.extract_classifier_name(old_classifier)
        if not classifier_name_and_id:
            return
        new_classifier = {k: v for k, v in old_classifier.to_dict().items() if k in intersection_fields}
        new_classifier = dict(new_classifier, type='classification', name=f'{classifier_name_and_id} - Classifier',
                              description='', fromVersion='6.0.0', id=classifier_name_and_id)

        new_classifier_path = self.calculate_new_path(classifier_name_and_id, is_mapper=False)
        self.dump_new_entity(new_classifier_path, new_classifier)

    def create_mapper_from_old_classifier(self, old_classifier: Classifier) -> None:
        """
        Receives classifier of format 5_9_9. Builds mapper of format 6_0_0 and above, if mapping exists in
        the old classifier.
        Args:
            old_classifier (Classifier): Old classifier object

        Returns:
            (None): Creates a new corresponding mapper to 'old_classifier' by 6_0_0 file structure, if mapping exists.
        """
        classifier_name_and_id = self.extract_classifier_name(old_classifier)
        mapping = old_classifier.get('mapping')
        if not classifier_name_and_id or not mapping:
            return
        mapper = dict(id=f'{classifier_name_and_id}-mapper', name=f'{classifier_name_and_id} - Incoming Mapper',
                      type='mapping-incoming', description='', version=-1, fromVersion='6.0.0', mapping=mapping,
                      feed=old_classifier.get('feed', False))
        default_incident_type = old_classifier.get('defaultIncidentType')
        if default_incident_type:
            mapper['defaultIncidentType'] = default_incident_type

        new_mapper_path = self.calculate_new_path(classifier_name_and_id, is_mapper=True)
        self.dump_new_entity(new_mapper_path, mapper)

    def calculate_new_path(self, old_classifier_brand: str, is_mapper: bool) -> str:
        """
        Calculates the new path for mapper or classifier of 6_0_0 format
        Args:
            old_classifier_brand (str): Brand name of the old classifier.
            is_mapper (bool): Whether path created is for mapper or for classifier.

        Returns:
            (str): The path to the newly created classifier/mapper of 6_0_0 format.
        """
        fixed_brand_name = self.entity_separators_to_underscore(old_classifier_brand)
        if is_mapper:
            fixed_brand_name = f'mapper-incoming-{fixed_brand_name}'
        new_path_suffix = f'classifier-{fixed_brand_name}.json'
        new_path = f'{str(self.pack.path)}/Classifiers/{new_path_suffix}'

        return new_path
