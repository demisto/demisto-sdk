import logging
import os
from contextlib import contextmanager
from typing import List

from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
    ArtifactsManager, ProcessPoolHandler, create_dirs, delete_dirs, dump_packs,
    wait_futures_complete, zip_dirs, zip_packs)
from pebble import ProcessFuture

EX_SUCCESS = 0
EX_FAIL = 1
logger = logging.getLogger('demisto-sdk')


class PacksCompiler:

    def __init__(self, input: str, output: str, content_version: str, zip_all: bool):
        default_args = dict(packs=True, zip=True, cpus=os.cpu_count(), suffix='')
        self.artifacts_manager = PacksManager(pack_names=input,
                                              artifacts_path=output,
                                              content_version=content_version,
                                              all_in_one_zip=zip_all,
                                              **default_args)

    def compile_packs(self):
        """
        Compress the given packs to one zip file or zip for each pack (depended on the zip_all flag)

        Returns: The path to the created zip or to directory of the pack zips

        """
        with PacksDirsHandler(self.artifacts_manager), ProcessPoolHandler(self.artifacts_manager) as pool:
            futures: List[ProcessFuture] = dump_packs(self.artifacts_manager, pool)
            wait_futures_complete(futures, self.artifacts_manager)
            if len(futures) > 0:
                # packs was dumped
                logger.info(f'\nArtifacts created:\n\t - {self.artifacts_manager.output_path}')
                return self.artifacts_manager.output_path

        logger.warning(f'Artifacts was not created, be sure your working directory are the Content path.\n '
                       f'current path is: {self.artifacts_manager.content.path}')
        return None


class PacksManager(ArtifactsManager):
    def __init__(self, all_in_one_zip: bool, **kwargs):
        super(PacksManager, self).__init__(**kwargs)
        self.zip_all = all_in_one_zip
        self.output_path = f'{self.content_packs_path}.zip' if self.zip_all else str(self.content_uploadable_zips_path)


@contextmanager
def PacksDirsHandler(artifact_manager: PacksManager):
    """ Artifacts Directories handler.
    Logic by time line:
        1. Delete artifacts directories if exists.
        2. Create directories.
        3. If any error occurred -> Delete artifacts directories -> Exit.
        4. If finish successfully:
            a. If zip all:
                 Zip artifacts zip.
               Else
                 Zip packs for uploading.
            b. Delete artifacts directories.

    Args:
        artifact_manager: Packs manager object.
    """
    try:
        delete_dirs(artifact_manager)
        create_dirs(artifact_manager)
        yield
    except (Exception, KeyboardInterrupt):
        delete_dirs(artifact_manager)
        artifact_manager.exit_code = EX_FAIL
    else:
        if artifact_manager.zip_all:
            zip_dirs(artifact_manager)
        else:
            zip_packs(artifact_manager)

        delete_dirs(artifact_manager)
