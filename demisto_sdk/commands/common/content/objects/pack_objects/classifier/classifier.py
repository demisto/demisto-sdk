from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import CLASSIFIER, MAPPER, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class Classifier(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CLASSIFIER)

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def type(self):
        return FileType.CLASSIFIER


class OldClassifier(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CLASSIFIER)

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def type(self):
        return FileType.OLD_CLASSIFIER


class ClassifierMapper(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, MAPPER)

    def upload(self, client: demisto_client) -> bool:
        """
        Upload the classifier to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_classifier(file=self.path)

    def type(self):
        return FileType.MAPPER
