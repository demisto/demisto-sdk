import tempfile
from typing import Optional, Union

import demisto_client
from demisto_sdk.commands.common.constants import INTEGRATION, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.tools import (get_demisto_version,
                                               unlock_entity)
from packaging.version import parse
from wcmatch.pathlib import Path


class Integration(YAMLContentUnifiedObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.INTEGRATION, INTEGRATION)

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_image.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_description.md"]
        self.dun
        return next(self._path.parent.glob(patterns=patterns), None)

    def upload(self, client: demisto_client = None, override: bool = False):
        """
        Upload the integration to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.
            override: Whether to unlock the integration if it is a locked system integration.

        Returns:
            The result of the upload command from demisto_client
        """
        if self.is_unify():
            return client.integration_upload(file=self.path)  # type: ignore
        else:
            with tempfile.TemporaryDirectory() as dir:
                unified_files = self._unify(dir)
                for file in unified_files:
                    if (str(file)[-7:] == '_45.yml') == (get_demisto_version(client) < parse('4.6.0')):
                        # The above condition checks that the file ends in `_45.yml' and the version is 4.5 or less
                        # or that the file doesn't end in `_45.yml` and the version is higher than 4.5
                        try:
                            return client.integration_upload(file=file)  # type: ignore
                        except Exception as e:
                            if 'Item is system' in e.body and override:  # type: ignore
                                integration_id = self.__getitem__('commonfields').get('id')
                                unlock_entity(client, FileType.INTEGRATION, integration_id)
                                return client.integration_upload(file=file)  # type: ignore
                            else:
                                raise
