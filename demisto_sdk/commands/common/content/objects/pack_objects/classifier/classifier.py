from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import (CLASSIFIER, DEFAULT_VERSION,
                                                   MAPPER,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from packaging.version import Version
from wcmatch.pathlib import Path

FROM_VERSION_FOR_NEW_CLASSIFIER = '6.0.0'
TO_VERSION_FOR_OLD_CLASSIFIER = '5.9.9'
CLASSIFICATION_TYPE = 'classification'
VALID_TYPE_INCOMING = 'mapping-incoming'
VALID_TYPE_OUTGOING = 'mapping-outgoing'


class Classifier(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, CLASSIFIER)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def validate(self,):
        return self.is_valid_classifier()

    def is_valid_classifier(self):
        """Checks whether the classifier is valid or not.

        Returns:
            bool. True if classifier is valid, else False.
        """
        return all([
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type()
        ])

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(str(self.path))):
                return False
        return True

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.get('fromVersion', '')
        if from_version:
            if self.from_version < Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                error_message, error_code = Errors.invalid_from_version_in_new_classifiers()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        else:
            error_message, error_code = Errors.missing_from_version_in_new_classifiers()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version field is valid.

        Returns:
            bool. True if to version filed is valid, else False.
        """
        if self.to_version <= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
            error_message, error_code = Errors.invalid_to_version_in_new_classifiers()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version <= self.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.get('type') != CLASSIFICATION_TYPE:
            error_message, error_code = Errors.invalid_type_in_new_classifiers()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True


class OldClassifier(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, CLASSIFIER)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def validate(self):
        return self.is_valid_classifier()

    def is_valid_classifier(self):
        """Checks whether the classifier is valid or not.

        Returns:
            bool. True if classifier is valid, else False.
        """
        return all([
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
        ])

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(str(self.path))):
                return False
        return True

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        is_valid = True
        if self.from_version >= Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
            error_message, error_code = Errors.invalid_from_version_in_old_classifiers()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        return is_valid

    def is_valid_to_version(self):
        """Checks if to version field is valid.

        Returns:
            bool. True if to version filed is valid, else False.
        """
        to_version = self.get('toVersion', '')
        if to_version:
            if self.to_version > Version(TO_VERSION_FOR_OLD_CLASSIFIER):
                error_message, error_code = Errors.invalid_to_version_in_old_classifiers()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        else:
            error_message, error_code = Errors.missing_to_version_in_old_classifiers()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version <= self.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True


class ClassifierMapper(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, MAPPER)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def validate(self):
        return self.is_valid_mapper()

    def is_valid_mapper(self):
        """Checks whether the mapper is valid or not.

        Returns:
            bool. True if mapper is valid, else False.
        """
        return all([
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type()
        ])

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(str(self.path))):
                return False
        return True

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.get('fromVersion', '')
        if from_version:
            if self.from_version < Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
                error_message, error_code = Errors.invalid_from_version_in_mapper()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False
        else:
            error_message, error_code = Errors.missing_from_version_in_mapper()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.to_version < Version(FROM_VERSION_FOR_NEW_CLASSIFIER):
            error_message, error_code = Errors.invalid_to_version_in_mapper()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version <= self.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.get('type') not in [VALID_TYPE_INCOMING, VALID_TYPE_OUTGOING]:
            error_message, error_code = Errors.invalid_type_in_mapper()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True
