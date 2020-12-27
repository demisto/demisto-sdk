from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import (
    Classifier, OldClassifier)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from packaging.version import Version

FROM_VERSION_FOR_NEW_CLASSIFIER = '6.0.0'
TO_VERSION_FOR_OLD_CLASSIFIER = '5.9.9'
CLASSIFICATION_TYPE = 'classification'


class ClassifierValidator(ContentEntityValidator):

    def __init__(self, structure_validator, new_classifier_version=True, ignored_errors=None,
                 print_as_warnings=False, suppress_print=False):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print)
        self.new_classifier_version = new_classifier_version
        self.classifier_object = Classifier(structure_validator.file_path) if new_classifier_version else \
            OldClassifier(structure_validator.file_path)

    def is_valid_classifier(self, validate_rn=True):
        """Checks whether the classifier is valid or not.

        Returns:
            bool. True if classifier is valid, else False.
        """
        return all([
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type()
        ])

    def is_valid_version(self):
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.classifier_object.get('fromVersion', '')
        if from_version:
            if self.new_classifier_version:
                if self.classifier_object.from_version < Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_from_version_in_new_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                        return False
            else:
                if self.classifier_object.from_version >= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_from_version_in_old_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                        return False

        elif not from_version and self.new_classifier_version:
            error_message, error_code = Errors.missing_from_version_in_new_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version field is valid.

        Returns:
            bool. True if to version filed is valid, else False.
        """
        to_version = self.classifier_object.get('toVersion', '')
        if to_version:
            if self.new_classifier_version:
                if self.classifier_object.to_version <= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                    error_message, error_code = Errors.invalid_to_version_in_new_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                        return False
            else:
                if self.classifier_object.to_version > Version(TO_VERSION_FOR_OLD_CLASSIFIER):
                    error_message, error_code = Errors.invalid_to_version_in_old_classifiers()
                    if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                        return False

        elif not to_version and not self.new_classifier_version:
            error_message, error_code = Errors.missing_to_version_in_old_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.classifier_object.to_version <= self.classifier_object.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.new_classifier_version and self.classifier_object.get('type') != CLASSIFICATION_TYPE:
            error_message, error_code = Errors.invalid_type_in_new_classifiers()
            if self.handle_error(error_message, error_code, file_path=self.classifier_object.path):
                return False
        return True
