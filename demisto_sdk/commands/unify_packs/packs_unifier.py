import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import arg_to_list
from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
    ArtifactsManager, ContentObject, ProcessPoolHandler, create_dirs,
    delete_dirs, dump_packs, logger, wait_futures_complete, zip_pack_zips,
    zip_packs)
from pebble import ProcessFuture
from pipenv.patched.piptools import click

EX_SUCCESS = 0
EX_FAIL = 1


class PacksUnifier:

    def __init__(self, pack_paths: str, output: str, content_version: str, zip_all: bool, quite_mode: bool = False):
        default_args = dict(packs=True, zip=True, cpus=os.cpu_count(), suffix='')
        self.artifacts_manager = PacksManager(
            pack_paths=pack_paths,
            artifacts_path=output,
            content_version=content_version,
            all_in_one_zip=zip_all,
            quite_mode=quite_mode,
            **default_args,
        )

    def unify_packs(self):
        """
        Compress the given packs to one zip file or zip for each pack (depended on the zip_all flag)

        Returns: tuple (the created zip path or the directory of the pack zips, list of the pack names)
                 or (None, None) if the pack names are empty

        """
        if self.artifacts_manager.pack_names:
            prev_level = logger.getEffectiveLevel()
            if self.artifacts_manager.quite_mode:
                logger.setLevel(logging.ERROR)
            try:
                with PacksDirsHandler(self.artifacts_manager), ProcessPoolHandler(self.artifacts_manager) as pool:
                    futures: List[ProcessFuture] = dump_packs(self.artifacts_manager, pool)
                    wait_futures_complete(futures, self.artifacts_manager)
                    if len(futures) > 0:
                        # packs was dumped
                        logger.info(f'Artifacts created: - {self.artifacts_manager.output_path}')
                        return self.artifacts_manager.output_path, self.artifacts_manager.pack_names

            finally:
                if self.artifacts_manager.quite_mode:
                    logger.setLevel(prev_level)
        else:
            return None, None


class PacksManager(ArtifactsManager):
    def __init__(self, pack_paths: str, all_in_one_zip: bool, quite_mode: bool, **kwargs):
        super().__init__(**kwargs)
        self.init_packs(pack_paths)
        self.zip_all = all_in_one_zip
        self.quite_mode = quite_mode
        self.output_path = f'{self.content_uploadable_zips_path}.zip' if self.zip_all \
            else str(self.content_uploadable_zips_path)

    def init_packs(self, pack_paths):
        """

        Args:
            pack_paths: CSV str with the pack paths

        init dict that map pack name to Pack object and init also the pack_names property

        """
        self.packs = {}
        for path_str in arg_to_list(pack_paths):
            path = Path(path_str)
            if len(path.parts) == 2 and path.parts[0] == PACKS_DIR:  # relative path from Packs/...
                path = self.content.path / path

            if not os.path.exists(path):
                click.secho(f'Error: Given input path: {path} does not exist, ignored', fg='bright_red')
                continue

            self.packs.update({path.name: Pack(path)})

        self.pack_names = [*self.packs]

    def get_relative_pack_path(self, content_object: ContentObject):
        """

        Args:
            content_object: the object to get the relative path for

        Returns:
            the path of the given object relative from the pack directory, for example HelloWorld/Scripts


        """
        for part in content_object.path.parts:
            if part in self.packs:
                return content_object.path.relative_to(self.packs[part].path.parent)

    def get_base_path(self):
        """

        Returns:
            None, as packs can came outside from Content

        """
        return None

    def get_dir_to_delete(self):
        """

        Returns:
            the value of ArtifactsManager.get_dir_to_delete and if zip_all is True - also the uploadable_packs dir
        """

        result = super().get_dir_to_delete()
        if self.zip_all:
            result.append(self.content_uploadable_zips_path)
        return result

    def is_in_quite_mode(self):
        return self.quite_mode


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
            zip_packs(artifact_manager)
            zip_pack_zips(artifact_manager)
        else:
            zip_packs(artifact_manager)

        delete_dirs(artifact_manager)
