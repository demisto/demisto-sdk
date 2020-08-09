# -*- coding: utf-8 -*-
"""Content create artifacts
Definitions:
    1. flattern - only files, without directories structure.
    2. content_pack_internal - .pack_ignore, .secrets-ignore.
    3. content_pack_objects - every content objects wich is not content_internal (Integrations/Playbooks etc).

Pre-processing:
    1. Modify content/Packs/Base/Scripts/CommonServerPython.py global variables:
        a. CONTENT_RELEASE_VERSION to given content version flag.
        b. CONTENT_BRANCH_NAME to active branch

The following artifacts created by this module:
    1.  content_test (flattern) -
        Exclude rules:
            a. *README*.md
            b. *CHANGELOG*.md
        Include rules:
            a. content/Packs/<Pack_name>/TestPlaybooks
            b. content/TestPlaybooks
            c. If from_version/fromVersion value is stricly lower than NEWEST_SUPPORTED_VERSION.
            b. content/TestPlaybooks/NotSupported directory allready filter and should not include.

    2.  content_packs - folder which include in all packs by their original structure.
        Exclude rules:
            a. content/Packs/<Pack_name>/<content_object>/*README*.md
            b. content/Packs/<Pack_name>/<content_object>/*CHANGELOG*.md
            c. content_internal
        Include rules:
            a. pack_object - If to_version/toVersion value is bigger from NEWEST_SUPPORTED_VERSION.
        Additionals:
            a. Add Documentation to -> Base/Documentation/doc-*.json from content/Documentation/doc-*.json

    3.  content_new (flattern):
        Exclude rules:
            a. *README*.md
            b. *CHANGELOG*.md
        Include rules:
            a. content/Packs/<Pack_name>/<Conten_object>/*.(yaml|json|yml)
            b. content/Packs/D2/tools/*.zip (The module script them before copy)
            c. If from_version/fromVersion value is stricly lower than NEWEST_SUPPORTED_VERSION.

Attributes:
    FIRST_MARKETPLACE_VERSION (Version): Newest version which demisto content team supports.
    IGNORED_PACKS (List[str]): Pack names which should be excluded during content artifacts creation - On packs collect.
    IGNORED_TEST_PLAYBOOKS_DIR: Directory name which should be excluded durign content artifact creation - On content/TestPlaybooks collect.

Notes:
    1. Each file should be open only once for evaluation.
    2. The command shouldn't change existing files data excluding unify, changing files data will significally increase
     the run time of the command.
    3. The command shouldn't influence content repo current state - Every file shoudl be the same after module execution.
"""

# STD
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, Future, as_completed
from shutil import rmtree
from typing import Union, List, Dict, Optional
from contextlib import contextmanager
# 3-rd party
from wcmatch.pathlib import Path, EXTMATCH, SPLIT, BRACE, NODIR, NEGATE
from packaging.version import parse
# Local
from demisto_sdk.commands.common.content.content import Content, Pack
from demisto_sdk.commands.common.content.content.objects.pack_objects import Script
from demisto_sdk.commands.common.content.content.objects.abstract_objects import (
    YAMLContentObject, YAMLUnfiedObject, JSONContentObject, TextObject)
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR, CONNECTIONS_DIR, DOCUMENTATION_DIR, BASE_PACK,
                                                   DASHBOARDS_DIR, INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR, INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR, LAYOUTS_DIR, PLAYBOOKS_DIR, RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR, WIDGETS_DIR, TOOLS_DIR,
                                                   PACKS_DIR)
from demisto_sdk.commands.common.logger import logging_setup, Colors
from demisto_sdk.commands.common.tools import safe_copyfile, zip_and_delete_origin
from .artifacts_report import ObjectReport, ArtifactsReport

FIRST_MARKETPLACE_VERSION = parse('6.0.0')

IGNORED_PACKS = ['ApiModules']
IGNORED_TEST_PLAYBOOKS_DIR = 'Deprecated'
ContentObject = Union[YAMLUnfiedObject, YAMLContentObject, JSONContentObject, TextObject]
logger = logging_setup(3, False)


class ArtifactsConfiguration:
    def __init__(self, artifacts_path: str, content_version: str, suffix: str, zip: bool, content_packs: bool,
                 cpus: int):
        """ Content artifacts configuration

        Args:
            artifacts_path: existing destination directory for creating artifacts.
            content_version:
            suffix: suffix to add all file we creates.
            zip: True for zip all content artifacts to 3 diffrent zip files in same structure else False.
            cpus: Availble cpus in the computer.
        """
        self.suffix = suffix
        self.content_version = content_version
        self.zip_artifacts = zip
        self.only_content_packs = content_packs
        self.artifacts_path = Path(artifacts_path)
        self.content_new_path = self.artifacts_path / 'content_new'
        self.content_test_path = self.artifacts_path / 'content_test'
        self.content_packs_path = self.artifacts_path / 'content_packs'
        self.cpus = cpus
        self.execution_start = time.time()
        self.content = Content.from_cwd()


def mute():
    sys.stdout = open(os.devnull, 'w')


def create_content_artifacts(artifact_conf: ArtifactsConfiguration) -> int:
    exit_code = 0
    start = time.time()
    # Create content artifacts direcotry
    create_artifacts_dirs(artifact_conf)

    with ProcessPoolExecutor(artifact_conf.cpus, initializer=mute) as pool:
        futures = {}
        # Iterate over all packs in content/Packs
        for pack_name, pack in artifact_conf.content.packs.items():
            if pack_name not in IGNORED_PACKS:
                futures[pool.submit(dump_pack, artifact_conf, pack)] = f'Pack {pack.path}'
        # Iterate over all test-playbooks in content/TestPlaybooks
        futures[pool.submit(dump_tests_conditionally, artifact_conf)] = f'TestPlaybooks'
        # Dump content descriptor from content/content-descriptor.json
        futures[pool.submit(dump_content_descriptor, artifact_conf)] = 'descriptor.json'
        # Dump content documentation from content/Documentation
        futures[pool.submit(dump_content_documentations, artifact_conf)] = 'Documentation'
        # Wait for all future to be finished - catch exception if occurred - before zip
        exit_code |= wait_futures_complete(futures, artifact_conf)
        # Add suffix if suffix exists
        if artifact_conf.suffix:
            suffix_handler(artifact_conf)
        # Zip if not specified otherwise
        if artifact_conf.zip_artifacts:
            for artifact in [artifact_conf.content_test_path,
                             artifact_conf.content_new_path,
                             artifact_conf.content_packs_path]:
                futures[pool.submit(zip_and_delete_origin, artifact)] = f'Zip {artifact}'
            # Wait for all future to be finished - catch exception if occurred
            exit_code |= wait_futures_complete(futures, artifact_conf)

    print(f"{time.time() - start}")

    return exit_code


def wait_futures_complete(futures: Dict[Future, str], artifact_conf: ArtifactsConfiguration) -> int:
    """Wait for all futures to complete, Raise exception if occured.

    Args:
        futures: futures to wait for.
        artifact_conf:
    """
    exit_code = 0
    for future in as_completed(futures):
        try:
            print(future.result().to_markdown(artifact_conf.content.path))
        except (BaseException, Exception):
            logger.exception(futures[future])
            exit_code = 1

    return exit_code


def create_artifacts_dirs(artifact_conf: ArtifactsConfiguration) -> None:
    """ Create content artifacts directories:
            1. content_test
            2. content_packs
            3. content_new

    Args:
        artifact_conf: Command line configurationץ
    """
    if artifact_conf.only_content_packs:
        artifact_conf.content_packs_path.unlink(missing_ok=True)
        artifact_conf.content_packs_path.mkdir(exist_ok=True, parents=True)
    else:
        for artifact in [artifact_conf.content_test_path,
                         artifact_conf.content_new_path,
                         artifact_conf.content_packs_path]:
            if artifact.exists():
                rmtree(artifact)
            artifact.mkdir(exist_ok=True, parents=True)


def dump_content_documentations(artifact_conf: ArtifactsConfiguration):
    """ Dumping content/content descriptor.json in to:
            1. content_test
            2. content_new

    Args:
        artifact_conf: Command line configuration.

    Notes:
        1. content_descriptor.json created during build run time.
    """
    term_report = ArtifactsReport("Documentations:")
    for documentation in artifact_conf.content.documentations:
        object_report = ObjectReport(documentation, content_packs=True)
        documentation.dump(artifact_conf.content_packs_path / BASE_PACK / DOCUMENTATION_DIR)
        if not artifact_conf.only_content_packs:
            documentation.dump(artifact_conf.content_new_path)
            object_report.set_content_new()
        term_report.append(object_report)

    return term_report


def dump_content_descriptor(artifact_conf: ArtifactsConfiguration):
    """ Dumping content/content descriptor.json in to:
            1. content_test
            2. content_new

    Args:
        artifact_conf: Command line configuration.

    Notes:
        1. content_descriptor.json created during build run time.
    """
    term_report = ArtifactsReport("Content descriptor:")
    if not artifact_conf.only_content_packs and artifact_conf.content.content_descriptor:
        descriptor = artifact_conf.content.content_descriptor
        object_report = ObjectReport(descriptor, content_test=True, content_new=True)
        for dest in [artifact_conf.content_test_path,
                     artifact_conf.content_new_path]:
            descriptor.dump(dest)
        term_report.append(object_report)

    return term_report


def dump_pack(artifact_conf: ArtifactsConfiguration, pack: Pack) -> None:
    """ Iterate on all required pack object and dump them conditionally, The following Pack object are excluded:
            1. Change_log files (Deprecated).
            2. Integration/Script/Playbook readme (Used for website documentation deployment).
            3. .pack-ignore (Interanl only).
            4. .secrets-ignore (Interanl only).

    Args:
        artifact_conf: Command line configuration.
        pack: Pack object.
    """
    term_report = ArtifactsReport(f"Pack {pack.name}:")
    for integration in pack.integrations:
        term_report += dump_pack_conditionally(artifact_conf, integration)
    for script in pack.scripts:
        term_report += dump_pack_conditionally(artifact_conf, script)
    for playbook in pack.playbooks:
        term_report += dump_pack_conditionally(artifact_conf, playbook)
    for test_playbook in pack.test_playbooks:
        term_report += dump_pack_conditionally(artifact_conf, test_playbook)
    for report in pack.reports:
        term_report += dump_pack_conditionally(artifact_conf, report)
    for layout in pack.layouts:
        term_report += dump_pack_conditionally(artifact_conf, layout)
    for dashboard in pack.dashboards:
        term_report += dump_pack_conditionally(artifact_conf, dashboard)
    for incident_field in pack.incident_fields:
        term_report += dump_pack_conditionally(artifact_conf, incident_field)
    for incident_type in pack.incident_types:
        term_report += dump_pack_conditionally(artifact_conf, incident_type)
    for indicator_field in pack.indicator_fields:
        term_report += dump_pack_conditionally(artifact_conf, indicator_field)
    for indicator_type in pack.indicator_types:
        term_report += dump_pack_conditionally(artifact_conf, indicator_type)
    for connection in pack.connections:
        term_report += dump_pack_conditionally(artifact_conf, connection)
    for classifier in pack.classifiers:
        term_report += dump_pack_conditionally(artifact_conf, classifier)
    for widget in pack.widgets:
        term_report += dump_pack_conditionally(artifact_conf, widget)
    for release_note in pack.release_notes:
        term_report += ObjectReport(release_note, content_packs=True)
        release_note.dump(artifact_conf.content_packs_path / pack.name / RELEASE_NOTES_DIR)
    for tool in pack.tools:
        object_report = ObjectReport(tool, content_packs=True)
        created_files = tool.dump(artifact_conf.content_packs_path / pack.name / TOOLS_DIR)
        if not artifact_conf.only_content_packs:
            object_report.set_content_new()
            for file in created_files:
                file.link_to(artifact_conf.content_new_path / file.name)
        term_report += object_report
    if pack.pack_metadata:
        term_report += ObjectReport(pack.pack_metadata, content_packs=True)
        pack.pack_metadata.dump(artifact_conf.content_packs_path / pack.name)
    if pack.readme:
        term_report += ObjectReport(pack.readme, content_packs=True)
        pack.readme.dump(artifact_conf.content_packs_path / pack.name)

    return term_report


def dump_pack_conditionally(artifact_conf: ArtifactsConfiguration, content_object: ContentObject) -> ObjectReport:
    """ Dump pack object by the following logic

    Args:
        artifact_conf: Command line configuration.
        content_object: content_object (e.g. Integration/Script/Layout etc)
    """
    object_report = ObjectReport(content_object)
    pack_created_files: List[Path] = []

    with content_files_handler(artifact_conf, content_object) as rm_files:
        # Content packs filter - When unify also _45.yml created which should be deleted after copy it if needed
        if is_in_content_packs(content_object):
            object_report.set_content_packs()
            pack_created_files.extend(dump_copy_files(artifact_conf, content_object,
                                                      artifact_conf.content_packs_path /
                                                      calc_relative_packs_dir(artifact_conf, content_object)))
            rm_files.extend(
                [created_file for created_file in pack_created_files if created_file.name.endswith('_45.yml')])
            real_packs = list(set(pack_created_files).difference(set(rm_files)))

        # Content test fileter
        if is_in_content_test(artifact_conf, content_object):
            object_report.set_content_test()
            dump_copy_files(artifact_conf, content_object, artifact_conf.content_test_path, pack_created_files)

        # Content new filter
        if is_in_content_new(artifact_conf, content_object):
            object_report.set_content_new()
            dump_copy_files(artifact_conf, content_object, artifact_conf.content_new_path, pack_created_files)

    return object_report


def dump_tests_conditionally(artifact_conf: ArtifactsConfiguration) -> ObjectReport:
    """ Dump test scripts/playbooks conditionally by the following logic:
            1. If from_version/fromVersion value is stricly lower than SUPPORTED_BOUND_VERSION.

    Args:
        artifact_conf: Command line configuration
    """
    term_report = ArtifactsReport("TestPlaybooks:")
    for test in artifact_conf.content.test_playbooks:
        object_report = ObjectReport(test)
        if is_in_content_test(artifact_conf, test):
            object_report.set_content_test()
            dump_copy_files(artifact_conf, test, artifact_conf.content_test_path)
        term_report += object_report

    return term_report


def dump_copy_files(artifact_conf: ArtifactsConfiguration, content_object: ContentObject,
                    target_dir: Path, created_files: Optional[List[Path]] = None) -> List[Path]:
    new_created_files = []
    if created_files:
        for file in created_files:
            new_file = target_dir / file.name
            if new_file.exists() and new_file.stat().st_mtime >= artifact_conf.execution_start:
                raise BaseException(f"Duplicate file in content repo: {content_object.path.name}")
            else:
                file.link_to(new_file)
                new_created_files.append(new_file)
    else:
        target = target_dir / content_object.normalized_file_name()
        if target.exists() and target.stat().st_mtime >= artifact_conf.execution_start:
            raise BaseException(f"Duplicate file in content repo: {content_object.path.name}")
        else:
            new_created_files.extend(content_object.dump(dest_dir=target_dir,
                                                         readme=False,
                                                         change_log=False))

    return new_created_files


def calc_relative_packs_dir(artifact_conf: ArtifactsConfiguration, content_object: ContentObject) -> Path:
    relative_pack_path = content_object.path.relative_to(artifact_conf.content.path / PACKS_DIR)
    if ((INTEGRATIONS_DIR in relative_pack_path.parts and relative_pack_path.parts[-2] != INTEGRATIONS_DIR) or
            (SCRIPTS_DIR in relative_pack_path.parts and relative_pack_path.parts[-2] != SCRIPTS_DIR)):
        relative_pack_path = relative_pack_path.parent.parent
    else:
        relative_pack_path = relative_pack_path.parent

    return relative_pack_path


def is_in_content_packs(content_object: ContentObject) -> bool:
    return content_object.to_version >= FIRST_MARKETPLACE_VERSION


def is_in_content_test(artifact_conf: ArtifactsConfiguration, content_object: ContentObject) -> bool:
    return (not artifact_conf.only_content_packs and
            TEST_PLAYBOOKS_DIR in content_object.path.parts and
            content_object.from_version < FIRST_MARKETPLACE_VERSION and
            IGNORED_TEST_PLAYBOOKS_DIR not in content_object.path.parts)


def is_in_content_new(artifact_conf: ArtifactsConfiguration, content_object: ContentObject) -> bool:
    return (not artifact_conf.only_content_packs and
            TEST_PLAYBOOKS_DIR not in content_object.path.parts and
            content_object.from_version < FIRST_MARKETPLACE_VERSION)


@contextmanager
def content_files_handler(artifact_conf: ArtifactsConfiguration, content_object: ContentObject):
    """ Pre-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py global variables:
                a. CONTENT_RELEASE_VERSION to given content version flag.
                b. CONTENT_BRANCH_NAME to active branch

        Post-processing pack, perform the following:
            1. Change content/Packs/Base/Scripts/CommonServerPython.py to original state.
            2. Unifier creates *_45.yml files in content_pack by default which is not support due to_version lower than
                NEWEST_SUPPORTED_VERSION, Therefor after copy it to content_new, delete it.

    Args:
        artifact_conf: Command line configuration.
        content_object: content_object (e.g. Integration/Script/Layout etc)
    """
    rm_files = []

    if (BASE_PACK in content_object.path.parts and isinstance(content_object, Script)
            and content_object.code_path and content_object.code_path.name == 'CommonServerPython.py'):
        # modify_common_server_parameters(content_object.code_path)
        modify_common_server_constants(content_object.code_path,
                                       content_version=artifact_conf.content_version,
                                       branch_name=artifact_conf.content.git().active_branch)
    yield rm_files

    if (BASE_PACK in content_object.path.parts and isinstance(content_object, Script)
            and content_object.code_path and content_object.code_path.name == 'CommonServerPython.py'):
        # modify_common_server_parameters(content_object.code_path)
        modify_common_server_constants(content_object.code_path,
                                       content_version='0.0.0',
                                       branch_name='master')

    # Delete yaml which created by Unifier in packs and to_version/toVersion lower than NEWEST_SUPPORTED_VERSION
    for file_path in rm_files:
        file_path.unlink()


def suffix_handler(artifact_conf: ArtifactsConfiguration):
    """ Add suffix to file names exclude:
            1. pack_metadata.json
            2. README.
            3. content_descriptor.json
            3. ReleaseNotes/**

        Include:
            1. *.json
            2. *.(yaml|yml)

    Args:
        artifact_conf: Command line configuration.
    """
    files_content_packs = artifact_conf.content_packs_path.rglob("!README.md|!pack_metadata.json|*.{json,yml,yaml}",
                                                                 flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
    file_content_test = artifact_conf.content_test_path.rglob("!content_descriptor.json|*.{json,yml,yaml}",
                                                              flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
    file_content_new = artifact_conf.content_new_path.rglob("!content_descriptor.json|*.{json,yml,yaml}",
                                                            flags=BRACE | SPLIT | EXTMATCH | NODIR | NEGATE)
    for files in [file_content_new, files_content_packs, file_content_test]:
        for file in files:
            file_name_split = file.name.split('.')
            file_real_stem = ".".join(file_name_split[:-1])
            suffix = file_name_split[-1]
            file.rename(file.with_name(f'{file_real_stem}-{artifact_conf.suffix}.{suffix}'))


def modify_common_server_constants(code_path: Path, branch_name: str, content_version):
    """
    Modify content/Packs/Base/Scripts/CommonServerPython.py global variables:
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
