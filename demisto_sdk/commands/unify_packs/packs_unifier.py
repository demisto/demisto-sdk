import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import click
from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import arg_to_list
from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
    IGNORED_PACKS, ArtifactsManager, ContentObject, create_dirs, delete_dirs,
    dump_pack, zip_pack_zips, zip_packs)

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
            self.artifacts_manager.dump_packs()
            return self.artifacts_manager.output_path, self.artifacts_manager.pack_names

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
            None, as packs can came outside from Content directory

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

    def dump_packs(self):
        """

        Dump all the packs stored in the packs field
        and will print summery according to the quit_mode field

        """
        reports = []
        # we quite the outputs and in case we want the output - a summery will be printed
        with QuiteModeController(quite_logger=True, quite_output=True), PacksDirsHandler(self):
            for pack_name in self.pack_names:
                if pack_name not in IGNORED_PACKS:
                    reports.append(dump_pack(self, self.packs[pack_name]))

        if not self.quite_mode:
            logger = logging.getLogger('demisto-sdk')
            for report in reports:
                logger.info(report.to_str(self.get_base_path()))


class QuiteModeController:
    """
    Quite mode controller
    in entry will quite the stdout and the logger according ti the flag passed to the constructor
    and in exit will return to the previous status of both the stdout and logger
    """

    def __init__(self, quite_logger: bool, quite_output):
        self.quite_modes = dict(quite_logger=quite_logger, quite_output=quite_output)
        self.old_stdout = sys.stdout
        self.logger = logging.getLogger('demisto-sdk')
        self.prev_logger_level = self.logger.getEffectiveLevel()

    def __enter__(self):
        if self.quite_modes['quite_output']:
            sys.stdout = open(os.devnull, 'w')
        if self.quite_modes['quite_logger']:
            self.logger.setLevel(logging.ERROR)

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        self.logger.setLevel(self.prev_logger_level)


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
