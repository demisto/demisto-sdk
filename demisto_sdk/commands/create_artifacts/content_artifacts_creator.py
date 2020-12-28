# -*- coding: utf-8 -*-
import logging
import os
import re
import sys
import time
from concurrent.futures import as_completed
from contextlib import contextmanager
from shutil import make_archive, rmtree
from typing import List, Optional, Union

from demisto_sdk.commands.common.constants import (BASE_PACK,
                                                   DOCUMENTATION_DIR,
                                                   INTEGRATIONS_DIR, PACKS_DIR,
                                                   RELEASE_NOTES_DIR,
                                                   SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   TOOLS_DIR)
from demisto_sdk.commands.common.content import (Content, ContentError,
                                                 ContentFactoryError, Pack)
from demisto_sdk.commands.common.content.objects.pack_objects import (
    JSONContentObject, Script, TextObject, YAMLContentObject,
    YAMLContentUnifiedObject)
from demisto_sdk.commands.common.logger import logging_setup
from packaging.version import parse
from pebble import ProcessFuture, ProcessPool
from wcmatch.pathlib import BRACE, EXTMATCH, NEGATE, NODIR, SPLIT, Path

from .artifacts_report import ArtifactsReport, ObjectReport

####################
# Global variables #
####################


FIRST_MARKETPLACE_VERSION = parse('6.0.0')
IGNORED_PACKS = ['ApiModules']
IGNORED_TEST_PLAYBOOKS_DIR = 'Deprecated'
ContentObject = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject, TextObject]
logger: logging.Logger
EX_SUCCESS = 0
EX_FAIL = 1


##############
# Main logic #
##############


class ArtifactsManager:
    def __init__(self, artifacts_path: str, content_version: str, suffix: str, zip: bool, packs: bool,
                 cpus: int):
        """ Content artifacts configuration

        Args:
            artifacts_path: existing destination directory for creating artifacts.
            content_version: release content varsion.
            packs: create only content_packs artifacts if True.
            suffix: suffix to add all file we creates.
            zip: True for zip all content artifacts to 3 diffrent zip files in same structure else False.
            cpus: Availble cpus in the computer.
        """
        self.suffix = suffix
        self.content_version = content_version
        self.zip_artifacts = zip
        self.only_content_packs = packs
        self.artifacts_path = Path(artifacts_path)
        self.content_new_path = self.artifacts_path / 'content_new'
        self.content_test_path = self.artifacts_path / 'content_test'
        self.content_packs_path = self.artifacts_path / 'content_packs'
        self.content_all_path = self.artifacts_path / 'all_content'
        self.cpus = cpus
        self.execution_start = time.time()
        self.content = Content.from_cwd()
        self.exit_code = EX_SUCCESS


def create_content_artifacts(artifact_manager: ArtifactsManager) -> int:
    global logger
    logger = logging_setup(3)

    with ArtifactsDirsHandler(artifact_manager), ProcessPoolHandler(artifact_manager) as pool:
        futures: List[ProcessFuture] = []
        # content/Packs
        futures.extend(dump_packs(artifact_manager, pool))
        # content/TestPlaybooks
        futures.append(pool.schedule(dump_tests_conditionally, args=(artifact_manager,)))
        # content/content-descriptor.json
        futures.append(pool.schedule(dump_content_descriptor, args=(artifact_manager,)))
        # content/Documentation/doc-*.json
        futures.append(pool.schedule(dump_content_documentations, args=(artifact_manager,)))
        # Wait for all futures to be finished
        wait_futures_complete(futures, artifact_manager)
        # Add suffix
        suffix_handler(artifact_manager)

    logger.info(f"\nExecution time: {time.time() - artifact_manager.execution_start} seconds")

    return artifact_manager.exit_code


@contextmanager
def ProcessPoolHandler(artifact_manager: ArtifactsManager) -> ProcessPool:
    """ Process pool Handler which terminate all processes in case of Exception.

    Args:
        artifact_manager: Artifacts manager object.

    Yields:
        ProcessPool: Pebble process pool.
    """
    with ProcessPool(max_workers=artifact_manager.cpus, initializer=child_mute) as pool:
        try:
            yield pool
        except KeyboardInterrupt:
            logger.info("\nCTRL+C Pressed!\nGracefully release all resources due to keyboard interrupt...")
            pool.stop()
            pool.join()
            raise
        except Exception as e:
            logger.exception(e)
            logger.error("Gracefully release all resources due to Error...")
            pool.stop()
            pool.join()
            raise
        else:
            pool.close()
            pool.join()


def wait_futures_complete(futures: List[ProcessFuture], artifact_manager: ArtifactsManager):
    """Wait for all futures to complete, Raise exception if occured.

    Args:
        artifact_manager: Artifacts manager object.
        futures: futures to wait for.

    Raises:
        Exception: Raise caught exception for further cleanups.
    """
    for future in as_completed(futures):
        try:
            result = future.result()
            if isinstance(result, ArtifactsReport):
                logger.info(result.to_str(artifact_manager.content.path))
        except (ContentError, DuplicateFiles, ContentFactoryError) as e:
            logger.error(e.msg)
            raise
        except Exception as e:
            logger.exception(e)
            raise


#####################################################
# Files include rules functions (Version, Type etc) #
#####################################################


def is_in_content_packs(content_object: ContentObject) -> bool:
    """ Rules content_packs:
            1. to_version >= First marketplace version.

        Args:
            content_object: Content object as specified in global variable - ContentObject.

        Returns:
            bool: True if object should be included in content_packs artifacts else False.
    """
    return content_object.to_version >= FIRST_MARKETPLACE_VERSION


def is_in_content_test(artifact_manager: ArtifactsManager, content_object: ContentObject) -> bool:
    """Rules content_test:
            1. flag of only packs is off.
            2. Object located in TestPlaybooks directory (*/TestPlaybooks/*).
            3. from_version < First marketplace version.
            4. Path of object is not including global variable - IGNORED_TEST_PLAYBOOKS_DIR

        Args:
            artifact_manager: Artifacts manager object.
            content_object: Content object as specified in global variable - ContentObject.

        Returns:
            bool: True if object should be included in content_test artifacts else False.
    """
    return (not artifact_manager.only_content_packs and
            TEST_PLAYBOOKS_DIR in content_object.path.parts and
            content_object.from_version < FIRST_MARKETPLACE_VERSION and
            IGNORED_TEST_PLAYBOOKS_DIR not in content_object.path.parts)


def is_in_content_new(artifact_manager: ArtifactsManager, content_object: ContentObject) -> bool:
    """ Rules content_new:
            1. flag of only packs is off.
            2. Object not located in TestPlaybooks directory (*/TestPlaybooks/*).
            3. from_version < First marketplace version

        Args:
            artifact_manager: Artifacts manager object.
            content_object: Content object as specified in global variable - ContentObject.

        Returns:
            bool: True if object should be included in content_new artifacts else False.
    """
    return (not artifact_manager.only_content_packs and
            TEST_PLAYBOOKS_DIR not in content_object.path.parts and
            content_object.from_version < FIRST_MARKETPLACE_VERSION)


def is_in_content_all(artifact_manager: ArtifactsManager, content_object: ContentObject) -> bool:
    """ Rules content_all:
            1. If in content_new or content_test.

        Args:
            artifact_manager: Artifacts manager object.
            content_object: Content object as specified in global variable - ContentObject.

        Returns:
            bool: True if object should be included in content_all artifacts else False.
    """
    return is_in_content_new(artifact_manager, content_object) or is_in_content_test(artifact_manager, content_object)


############################
# Documentations functions #
############################


def dump_content_documentations(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """ Dumping Documentation/doc-*.json into:
            1. content_new
            2. content_all

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.
    """
    report = ArtifactsReport("Documentations:")
    for documentation in artifact_manager.content.documentations:
        object_report = ObjectReport(documentation, content_packs=True)
        created_files = documentation.dump(artifact_manager.content_packs_path / BASE_PACK / DOCUMENTATION_DIR)
        if not artifact_manager.only_content_packs:
            object_report.set_content_new()
            object_report.set_content_all()
            for dest in [artifact_manager.content_new_path,
                         artifact_manager.content_all_path]:
                created_files = dump_link_files(artifact_manager, documentation, dest, created_files)
        report.append(object_report)

    return report


########################
# Descriptor functions #
########################


def dump_content_descriptor(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """ Dumping content/content_descriptor.json into:
            1. content_test
            2. content_new
            3. content_all

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.

    Notes:
        1. content_descriptor.json created during build run time.
    """
    report = ArtifactsReport("Content descriptor:")
    if not artifact_manager.only_content_packs and artifact_manager.content.content_descriptor:
        descriptor = artifact_manager.content.content_descriptor
        object_report = ObjectReport(descriptor, content_test=True, content_new=True, content_all=True)
        created_files: List[Path] = []
        for dest in [artifact_manager.content_test_path,
                     artifact_manager.content_new_path,
                     artifact_manager.content_all_path]:
            created_files = dump_link_files(artifact_manager, descriptor, dest, created_files)
        report.append(object_report)

    return report


##################################
# Content Testplaybook functions #
##################################


def dump_tests_conditionally(artifact_manager: ArtifactsManager) -> ArtifactsReport:
    """ Dump test scripts/playbooks conditionally into:
            1. content_test

    Args:
        artifact_manager: Artifacts manager object.

    Returns:
        ArtifactsReport: ArtifactsReport object.
    """
    report = ArtifactsReport("TestPlaybooks:")
    for test in artifact_manager.content.test_playbooks:
        object_report = ObjectReport(test)
        if is_in_content_test(artifact_manager, test):
            object_report.set_content_test()
            test_created_files = dump_link_files(artifact_manager, test, artifact_manager.content_test_path)
            dump_link_files(artifact_manager, test, artifact_manager.content_all_path, test_created_files)
        report += object_report

    return report


###########################
# Content packs functions #
###########################

def dump_packs(artifact_manager: ArtifactsManager, pool: ProcessPool) -> List[ProcessFuture]:
    """ Create futures which dumps conditionally content/Packs.

    Args:
        artifact_manager: Artifacts manager object.
        pool: Process pool to schedule new processes.

    Returns:
        List[ProcessFuture]: List of pebble futures to wait for.
    """
    futures = []
    for pack_name, pack in artifact_manager.content.packs.items():
        if pack_name not in IGNORED_PACKS:
            futures.append(pool.schedule(dump_pack, args=(artifact_manager, pack)))

    return futures


def dump_pack(artifact_manager: ArtifactsManager, pack: Pack) -> ArtifactsReport:
    """ Dumping content/Packs/<pack_id>/ into:
            1. content_test
            2. content_new
            3. content_all
            4. content_packs

    Args:
        artifact_manager: Artifacts manager object.
        pack: Pack object.

    Notes:
        1. Include all file object, excluding:
            a. Change_log files (Deprecated).
            b. Integration/Script/Playbook readme (Used for website documentation deployment).
            c. .pack-ignore (Internal only).
            d. .secrets-ignore (Internal only).

    Returns:
        ArtifactsReport: ArtifactsReport object.
    """
    pack_report = ArtifactsReport(f"Pack {pack.id}:")
    for integration in pack.integrations:
        pack_report += dump_pack_conditionally(artifact_manager, integration)
    for script in pack.scripts:
        pack_report += dump_pack_conditionally(artifact_manager, script)
    for playbook in pack.playbooks:
        pack_report += dump_pack_conditionally(artifact_manager, playbook)
    for test_playbook in pack.test_playbooks:
        pack_report += dump_pack_conditionally(artifact_manager, test_playbook)
    for report in pack.reports:
        pack_report += dump_pack_conditionally(artifact_manager, report)
    for layout in pack.layouts:
        pack_report += dump_pack_conditionally(artifact_manager, layout)
    for dashboard in pack.dashboards:
        pack_report += dump_pack_conditionally(artifact_manager, dashboard)
    for incident_field in pack.incident_fields:
        pack_report += dump_pack_conditionally(artifact_manager, incident_field)
    for incident_type in pack.incident_types:
        pack_report += dump_pack_conditionally(artifact_manager, incident_type)
    for indicator_field in pack.indicator_fields:
        pack_report += dump_pack_conditionally(artifact_manager, indicator_field)
    for indicator_type in pack.indicator_types:
        pack_report += dump_pack_conditionally(artifact_manager, indicator_type)
    for connection in pack.connections:
        pack_report += dump_pack_conditionally(artifact_manager, connection)
    for classifier in pack.classifiers:
        pack_report += dump_pack_conditionally(artifact_manager, classifier)
    for widget in pack.widgets:
        pack_report += dump_pack_conditionally(artifact_manager, widget)
    for release_note in pack.release_notes:
        pack_report += ObjectReport(release_note, content_packs=True)
        release_note.dump(artifact_manager.content_packs_path / pack.id / RELEASE_NOTES_DIR)
    for tool in pack.tools:
        object_report = ObjectReport(tool, content_packs=True)
        created_files = tool.dump(artifact_manager.content_packs_path / pack.id / TOOLS_DIR)
        if not artifact_manager.only_content_packs:
            object_report.set_content_new()
            dump_link_files(artifact_manager, tool, artifact_manager.content_new_path, created_files)
            object_report.set_content_all()
            dump_link_files(artifact_manager, tool, artifact_manager.content_all_path, created_files)
        pack_report += object_report
    if pack.pack_metadata:
        pack_report += ObjectReport(pack.pack_metadata, content_packs=True)
        pack.pack_metadata.dump(artifact_manager.content_packs_path / pack.id)
    if pack.readme:
        pack_report += ObjectReport(pack.readme, content_packs=True)
        pack.readme.dump(artifact_manager.content_packs_path / pack.id)
    if pack.author_image:
        pack_report += ObjectReport(pack.author_image, content_packs=True)
        pack.author_image.dump(artifact_manager.content_packs_path / pack.id)

    return pack_report


def dump_pack_conditionally(artifact_manager: ArtifactsManager, content_object: ContentObject) -> ObjectReport:
    """ Dump pack object by the following logic

    Args:
        artifact_manager: Artifacts manager object.
        content_object: content_object (e.g. Integration/Script/Layout etc)

    Returns:
        ObjectReport: ObjectReport object.
    """
    object_report = ObjectReport(content_object)
    pack_created_files: List[Path] = []
    test_new_created_files: List[Path] = []

    with content_files_handler(artifact_manager, content_object) as files_to_remove:
        # Content packs filter - When unify also _45.yml created which should be deleted after copy it if needed
        if is_in_content_packs(content_object):
            object_report.set_content_packs()
            # Unify will create *_45.yml files which shouldn't be in content_packs
            pack_created_files.extend(dump_link_files(artifact_manager, content_object,
                                                      artifact_manager.content_packs_path /
                                                      calc_relative_packs_dir(artifact_manager, content_object)))
            # Collecting files *_45.yml which created and need to be removed after execution.
            files_to_remove.extend(
                [created_file for created_file in pack_created_files if created_file.name.endswith('_45.yml')])

        # Content test fileter
        if is_in_content_test(artifact_manager, content_object):
            object_report.set_content_test()
            test_new_created_files = dump_link_files(artifact_manager, content_object,
                                                     artifact_manager.content_test_path, pack_created_files)

        # Content new filter
        if is_in_content_new(artifact_manager, content_object):
            object_report.set_content_new()
            test_new_created_files = dump_link_files(artifact_manager, content_object,
                                                     artifact_manager.content_new_path, pack_created_files)
        # Content all filter
        if is_in_content_all(artifact_manager, content_object):
            object_report.set_content_all()
            dump_link_files(artifact_manager, content_object, artifact_manager.content_all_path, test_new_created_files)

    return object_report


@contextmanager
def content_files_handler(artifact_manager: ArtifactsManager, content_object: ContentObject):
    """ Pre-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py global variables:
                a. CONTENT_RELEASE_VERSION to given content version flag.
                b. CONTENT_BRANCH_NAME to active branch

        Post-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py to original state.
            2. Unifier creates *_45.yml files in content_pack by default which is not support due to_version lower than
                NEWEST_SUPPORTED_VERSION, Therefor after copy it to content_new, delete it.

    Args:
        artifact_manager: Command line configuration.
        content_object: content_object (e.g. Integration/Script/Layout etc)

    Yields:
        List[Path]: List of file to be removed after execution.
    """
    files_to_remove: List[Path] = []

    try:
        if (BASE_PACK in content_object.path.parts) and isinstance(content_object, Script) and \
                content_object.code_path and content_object.code_path.name == 'CommonServerPython.py':
            # Modify CommonServerPython.py global variables
            repo = artifact_manager.content.git()
            modify_common_server_constants(content_object.code_path, artifact_manager.content_version,
                                           'master' if not repo else repo.active_branch)
        yield files_to_remove
    finally:
        if (BASE_PACK in content_object.path.parts) and isinstance(content_object, Script) and \
                content_object.code_path and content_object.code_path.name == 'CommonServerPython.py':
            # Modify CommonServerPython.py global variables
            modify_common_server_constants(content_object.code_path, '0.0.0', 'master')

        # Delete yaml which created by Unifier in packs and to_version/toVersion lower than NEWEST_SUPPORTED_VERSION
        for file_path in files_to_remove:
            file_path.unlink()


def modify_common_server_constants(code_path: Path, content_version: str, branch_name: Optional[str] = None):
    """ Modify content/Packs/Base/Scripts/CommonServerPython.py global variables:
            a. CONTENT_RELEASE_VERSION to given content version flag.
            b. CONTENT_BRANCH_NAME to active branch

    Args:
        code_path: Packs/Base/Scripts/CommonServerPython.py full code path.
        branch_name: branch name to update in CONTENT_BRANCH_NAME
        content_version: content version to update in CONTENT_RELEASE_VERSION
    """
    file_content_new = re.sub(r"CONTENT_RELEASE_VERSION = '\d.\d.\d'",
                              f"CONTENT_RELEASE_VERSION = '{content_version}'",
                              code_path.read_text())
    file_content_new = re.sub(r"CONTENT_BRANCH_NAME = '\w+'",
                              f"CONTENT_BRANCH_NAME = '{branch_name}'",
                              file_content_new)
    code_path.write_text(file_content_new)


########################
# Suffix add functions #
########################


def suffix_handler(artifact_manager: ArtifactsManager):
    """ Add suffix to file names exclude:
            1. pack_metadata.json
            2. README.
            3. content_descriptor.json
            3. ReleaseNotes/**

        Include:
            1. *.json
            2. *.(yaml|yml)

    Args:
        artifact_manager: Artifacts manager object.
    """
    files_pattern_to_add_suffix = "!reputations.json|!pack_metadata.json|" \
                                  "!doc-*.json|!content-descriptor.json|*.{json,yml,yaml}"
    if artifact_manager.suffix:
        files_content_packs = artifact_manager.content_packs_path.rglob(
            files_pattern_to_add_suffix, flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
        files_content_test = artifact_manager.content_test_path.rglob(files_pattern_to_add_suffix,
                                                                      flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
        files_content_new = artifact_manager.content_new_path.rglob(files_pattern_to_add_suffix,
                                                                    flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
        files_content_all = artifact_manager.content_all_path.rglob(files_pattern_to_add_suffix,
                                                                    flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
        for files in [files_content_new, files_content_packs, files_content_test, files_content_all]:
            for file in files:
                file_name_split = file.name.split('.')
                file_real_stem = ".".join(file_name_split[:-1])
                suffix = file_name_split[-1]
                file.rename(file.with_name(f'{file_real_stem}{artifact_manager.suffix}.{suffix}'))

###########
# Helpers #
###########


class DuplicateFiles(Exception):
    def __init__(self, exiting_file: Path, src: Path):
        """ Exception raised when 2 files with the same name existing in same directory when creating artifacts

            Args:
                exiting_file: File allready exists in artifacts.
                src: File source which copy or link to same directory.
        """
        self.exiting_file = exiting_file
        self.src = src
        self.msg = f"\nFound duplicate files\n1. {src}\n2. {exiting_file}"


def dump_link_files(artifact_manager: ArtifactsManager, content_object: ContentObject,
                    dest_dir: Path, created_files: Optional[List[Path]] = None) -> List[Path]:
    """ Dump content object to requested destination dir.
    Due to perfomence issue if known files allredy created and dump is done for the same object, This function
    will link files instead of creating the files from scratch (Reduce unify, split etc.)

    Args:
        artifact_manager: Artifacts manager object.
        content_object: Content object.
        dest_dir: Destination dir.
        created_files: Pre-created file (Not mandatory).

    Returns:
        List[Path]: List of new created files.

    Raises:
        DuplicateFiles: Exception occured if duplicate files exists in the same dir (Protect from override).
    """
    new_created_files = []
    # Handle case where files allready created
    if created_files:
        for file in created_files:
            new_file = dest_dir / file.name
            if new_file.exists() and new_file.stat().st_mtime >= artifact_manager.execution_start:
                raise DuplicateFiles(new_file, content_object.path)
            else:
                os.link(file, new_file)
                new_created_files.append(new_file)
    # Handle case where object first time dump.
    else:
        target = dest_dir / content_object.normalize_file_name()
        if target.exists() and target.stat().st_mtime >= artifact_manager.execution_start:
            raise DuplicateFiles(target, content_object.path)
        else:
            new_created_files.extend(content_object.dump(dest_dir=dest_dir))

    return new_created_files


def calc_relative_packs_dir(artifact_manager: ArtifactsManager, content_object: ContentObject) -> Path:
    relative_pack_path = content_object.path.relative_to(artifact_manager.content.path / PACKS_DIR)
    if ((INTEGRATIONS_DIR in relative_pack_path.parts and relative_pack_path.parts[-2] != INTEGRATIONS_DIR) or
            (SCRIPTS_DIR in relative_pack_path.parts and relative_pack_path.parts[-2] != SCRIPTS_DIR)):
        relative_pack_path = relative_pack_path.parent.parent
    else:
        relative_pack_path = relative_pack_path.parent

    return relative_pack_path


def child_mute():
    """Mute child process inorder to keep log clean"""
    sys.stdout = open(os.devnull, 'w')


###################################
# Artifacts Directories functions #
###################################


@contextmanager
def ArtifactsDirsHandler(artifact_manager: ArtifactsManager):
    """ Artifacts Directories handler.
    Logic by time line:
        1. Delete artifacts directories if exists.
        2. Create directories.
        3. If any error occured -> Delete artifacts directories -> Exit.
        4. If finish succesfully:
            a. If zip:
                1. Zip artifacts zip.
                2. Delete artifacts directories.
        5. log report.

    Args:
        artifact_manager: Artifacts manager object.
    """
    try:
        delete_dirs(artifact_manager)
        create_dirs(artifact_manager)
        yield
    except (Exception, KeyboardInterrupt):
        delete_dirs(artifact_manager)
        artifact_manager.exit_code = EX_FAIL
    else:
        if artifact_manager.zip_artifacts:
            zip_dirs(artifact_manager)
            delete_dirs(artifact_manager)
        report_artifacts_paths(artifact_manager)


def delete_dirs(artifact_manager: ArtifactsManager):
    """Delete artifacts directories"""
    for artifact_dir in [artifact_manager.content_test_path, artifact_manager.content_new_path,
                         artifact_manager.content_packs_path, artifact_manager.content_all_path]:
        if artifact_dir.exists():
            rmtree(artifact_dir)


def create_dirs(artifact_manager: ArtifactsManager):
    """Create artifacts directories"""
    if artifact_manager.only_content_packs:
        artifact_manager.content_packs_path.mkdir(parents=True)
    else:
        for artifact_dir in [artifact_manager.content_test_path, artifact_manager.content_new_path,
                             artifact_manager.content_packs_path, artifact_manager.content_all_path]:
            artifact_dir.mkdir(parents=True)


def zip_dirs(artifact_manager: ArtifactsManager):
    """Zip artifacts directories"""
    if artifact_manager.only_content_packs:
        make_archive(artifact_manager.content_packs_path, 'zip', artifact_manager.content_packs_path)
    else:
        with ProcessPoolHandler(artifact_manager) as pool:
            for artifact_dir in [artifact_manager.content_test_path, artifact_manager.content_new_path,
                                 artifact_manager.content_packs_path, artifact_manager.content_all_path]:
                pool.schedule(make_archive, args=(artifact_dir, 'zip', artifact_dir))


def report_artifacts_paths(artifact_manager: ArtifactsManager):
    """Report artifacts results destination"""
    logger.info("\nArtifacts created:")
    if artifact_manager.zip_artifacts:
        template = "\n\t - {}.zip"
    else:
        template = "\n\t - {}"

    if artifact_manager.only_content_packs:
        logger.info(template.format(artifact_manager.content_packs_path))

    logger.info(template.format(artifact_manager.content_packs_path))

    if not artifact_manager.only_content_packs:
        for artifact_dir in [artifact_manager.content_test_path, artifact_manager.content_new_path,
                             artifact_manager.content_all_path]:
            logger.info(template.format(artifact_dir))
