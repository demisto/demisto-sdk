import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from shutil import make_archive

import click
from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import arg_to_list
from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
    IGNORED_PACKS, ArtifactsManager, ContentObject, create_dirs, delete_dirs,
    dump_pack, zip_packs)

EX_SUCCESS = 0
EX_FAIL = 1


class PacksZipper:

    def __init__(self, pack_paths: str, output: str, content_version: str, zip_all: bool, quiet_mode: bool = False):
        self.artifacts_manager = PacksManager(
            pack_paths=pack_paths,
            artifacts_path=output,
            content_version=content_version,
            all_in_one_zip=zip_all,
            quiet_mode=quiet_mode,
        )

    def zip_packs(self):
        """Compress the given packs to one zip file or zip for each pack (depended on the zip_all flag).

        Returns:
            tuple: (the created zip path or the directory of the pack zips, list of the pack names)
                    or (None, None) if the pack names are empty

        """
        if self.artifacts_manager.pack_names:
            self.artifacts_manager.dump_packs()
            return self.artifacts_manager.output_path, self.artifacts_manager.pack_names

        else:
            return None, None


class PacksManager(ArtifactsManager):
    """Manages the work with packs in zip-packs command.

    Attributes:
        zip_all (bool): Flag indicating whether to zip all the packs in one zip or not.
        quiet_mode (bool): Flag indicating is in quiet mode or not.
        output_path (str): The target of the created zip

    """

    def __init__(self, pack_paths: str, all_in_one_zip: bool, quiet_mode: bool, **kwargs):
        super().__init__(packs=True, zip=True, cpus=1, suffix='', **kwargs)
        self.init_packs(pack_paths)
        self.zip_all = all_in_one_zip
        self.quiet_mode = quiet_mode
        self.output_path = f'{self.content_uploadable_zips_path}.zip' if self.zip_all \
            else str(self.content_uploadable_zips_path)

    def init_packs(self, pack_paths):
        """Init dict that map pack name to Pack object and init also the pack_names property.

        Args:
            pack_paths (str): CSV str with the pack paths.

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
        """Get the path of the given object relatively from the Packs directory, for example HelloWorld/Scripts.

        Args:
            content_object (ContentObject): The object to get the relative path for.

        Returns:
            Path: The relative path.
        """
        for part in content_object.path.parts:
            if part in self.packs:
                return content_object.path.relative_to(self.packs[part].path.parent)

    def get_dir_to_delete(self):
        """Get list of directories to delete after the unify process finished.

        Returns:
            list: The value from ArtifactsManager.get_dir_to_delete, if zip_all is True - the uploadable_packsalso dir also
        """

        result = super().get_dir_to_delete()
        if self.zip_all:
            result.append(self.content_uploadable_zips_path)
        return result

    def dump_packs(self):
        """Dump all the packs stored in the packs field
        and will print summery according to the quit_mode field

        """
        reports = []
        # we quiet the outputs and in case we want the output - a summery will be printed
        with QuietModeController(quiet_logger=True, quiet_output=True), PacksDirsHandler(self):
            for pack_name in self.pack_names:
                if pack_name not in IGNORED_PACKS:
                    reports.append(dump_pack(self, self.packs[pack_name]))

        if not self.quiet_mode:
            logger = logging.getLogger('demisto-sdk')
            for report in reports:
                logger.info(report.to_str(src_relative_to=None))

            created_zip_path = self.output_path if self.zip_all \
                else '\n'.join([f'{self.output_path}/{pack_name}.zip' for pack_name in self.pack_names])
            logger.info(f'\nCreated zips:\n{created_zip_path}')


class QuietModeController:
    """Control a quiet mode for loggers and stdout.

    Attributes:
        quiet_modes (dict): Dict with bool flags for the various outputs (logger, stdout).
        old_stdout (TextIO): The previous target of the system stdout.
        logger (logging.Logger): The active logger.
        prev_logger_level (int): The previous log level before quiet mode was activated.
    """

    def __init__(self, quiet_logger: bool, quiet_output):
        self.quiet_modes = dict(quiet_logger=quiet_logger, quiet_output=quiet_output)
        self.old_stdout = sys.stdout
        self.logger = logging.getLogger('demisto-sdk')
        self.prev_logger_level = self.logger.getEffectiveLevel()

    def __enter__(self):
        if self.quiet_modes['quiet_output']:
            sys.stdout = open(os.devnull, 'w')
        if self.quiet_modes['quiet_logger']:
            self.logger.setLevel(logging.ERROR)

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        self.logger.setLevel(self.prev_logger_level)


def zip_uploadable_packs(artifact_manager: ArtifactsManager):
    """Zip the zipped packs directory"""
    pack_zips_dir = artifact_manager.content_uploadable_zips_path
    make_archive(pack_zips_dir, 'zip', pack_zips_dir)


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
            zip_uploadable_packs(artifact_manager)
        else:
            zip_packs(artifact_manager)

        delete_dirs(artifact_manager)
