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
import re
import time
from concurrent.futures import ProcessPoolExecutor, Future, as_completed
from typing import Union, List, Dict, Optional
from contextlib import contextmanager
import textwrap
# 3-rd party
from wcmatch.pathlib import Path, EXTMATCH, SPLIT, BRACE, NODIR, NEGATE
from packaging.version import parse, Version
# Local
from demisto_sdk.commands.common.content.content import Content, Pack
from demisto_sdk.commands.common.content.content.objects.pack_objects import Script
from demisto_sdk.commands.common.content.content.objects.abstract_objects import (
    YAMLConentObject, YAMLUnfiedObject, JSONContentObject, TextObject)
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR, CONNECTIONS_DIR, DOCUMENTATION_DIR, BASE_PACK,
                                                   DASHBOARDS_DIR, INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR, INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR, LAYOUTS_DIR, PLAYBOOKS_DIR, RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR, WIDGETS_DIR, TOOLS_DIR)
from demisto_sdk.commands.common.logger import logging_setup, Colors
from demisto_sdk.commands.common.tools import safe_copyfile, zip_and_delete_origin

FIRST_MARKETPLACE_VERSION = parse('6.0.0')

IGNORED_PACKS = ['ApiModules']
IGNORED_TEST_PLAYBOOKS_DIR = 'Deprecated'
ContentObject = Union[YAMLUnfiedObject, YAMLConentObject, JSONContentObject, TextObject]
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


def create_content_artifacts(artifact_conf: ArtifactsConfiguration) -> int:
    exit_code = 0

    # Create content artifacts direcotry
    create_artifacts_dirs(artifact_conf)

    with ProcessPoolExecutor(artifact_conf.cpus) as pool:
        futures = {}
        # Iterate over all packs in content/Packs
        for pack_name, pack in artifact_conf.content.packs.items():
            if pack_name not in IGNORED_PACKS:
                futures[pool.submit(dump_pack, artifact_conf, pack_name, pack)] = f'Pack {pack.path}'
        # Iterate over all test-playbooks in content/TestPlaybooks
        if not artifact_conf.only_content_packs:
            for test_playbook in artifact_conf.content.test_playbooks:
                futures[pool.submit(dump_test_conditionally, artifact_conf,
                                    test_playbook)] = f'TestPlaybooks {test_playbook.path}'
        # Dump content descriptor from content/content-descriptor.json
        futures[pool.submit(dump_content_descriptor, artifact_conf)] = 'descriptor.json'
        # Dump content documentation from content/Documentation
        futures[pool.submit(dump_content_documentations, artifact_conf)] = 'Documentation'
        # Wait for all future to be finished - catch exception if occurred - before zip
        exit_code |= wait_futures_complete(futures)
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
            exit_code |= wait_futures_complete(futures)
        log_results(artifact_conf)

    return exit_code


def wait_futures_complete(futures: Dict[Future, str]) -> int:
    """Wait for all futures to complete, Raise exception if occured.

    Args:
        futures: futures to wait for.
    """
    exit_code = 0
    for future in as_completed(futures):
        try:
            future.result()
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
        artifact_conf.content_packs_path.mkdir(exist_ok=True, parents=True)
    else:
        for artifact in [artifact_conf.content_test_path,
                         artifact_conf.content_new_path,
                         artifact_conf.content_packs_path]:
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
    for documentation in artifact_conf.content.documentations:
        log_created(artifact_conf.content_packs_path,
                    documentation.path,
                    documentation.dump(artifact_conf.content_packs_path / BASE_PACK / DOCUMENTATION_DIR),
                    artifact_conf.content.path)
        if not artifact_conf.only_content_packs:
            log_created(artifact_conf.content_new_path,
                        documentation.path,
                        documentation.dump(artifact_conf.content_new_path),
                        artifact_conf.content.path)


def dump_content_descriptor(artifact_conf: ArtifactsConfiguration):
    """ Dumping content/content descriptor.json in to:
            1. content_test
            2. content_new

    Args:
        artifact_conf: Command line configuration.

    Notes:
        1. content_descriptor.json created during build run time.
    """
    if not artifact_conf.only_content_packs and artifact_conf.content.content_descriptor:
        descriptor = artifact_conf.content.content_descriptor
        for dest in [artifact_conf.content_test_path,
                     artifact_conf.content_new_path]:
            log_created(dest,
                        descriptor.path,
                        descriptor.dump(dest),
                        artifact_conf.content.path)


def dump_pack(artifact_conf: ArtifactsConfiguration, pack_name: str, pack: Pack) -> None:
    """ Iterate on all required pack object and dump them conditionally, The following Pack object are excluded:
            1. Change_log files (Deprecated).
            2. Integration/Script/Playbook readme (Used for website documentation deployment).
            3. .pack-ignore (Interanl only).
            4. .secrets-ignore (Interanl only).

    Args:
        artifact_conf: Command line configuration.
        pack_name: Pack directory name.
        pack: Pack object.
    """
    for integration in pack.integrations:
        dump_pack_conditionally(artifact_conf, integration, pack_name, INTEGRATIONS_DIR)
    for script in pack.scripts:
        dump_pack_conditionally(artifact_conf, script, pack_name, SCRIPTS_DIR)
    for playbook in pack.playbooks:
        dump_pack_conditionally(artifact_conf, playbook, pack_name, PLAYBOOKS_DIR)
    for test_playbook in pack.test_playbooks:
        dump_pack_conditionally(artifact_conf, test_playbook, pack_name, TEST_PLAYBOOKS_DIR)
    for report in pack.reports:
        dump_pack_conditionally(artifact_conf, report, pack_name, REPORTS_DIR)
    for layout in pack.layouts:
        dump_pack_conditionally(artifact_conf, layout, pack_name, LAYOUTS_DIR)
    for dashboard in pack.dashboards:
        dump_pack_conditionally(artifact_conf, dashboard, pack_name, DASHBOARDS_DIR)
    for incident_field in pack.incident_fields:
        dump_pack_conditionally(artifact_conf, incident_field, pack_name, INCIDENT_FIELDS_DIR)
    for incident_type in pack.incident_types:
        dump_pack_conditionally(artifact_conf, incident_type, pack_name, INCIDENT_TYPES_DIR)
    for indicator_field in pack.indicator_fields:
        dump_pack_conditionally(artifact_conf, indicator_field, pack_name, INDICATOR_FIELDS_DIR)
    for indicator_type in pack.indicator_types:
        dump_pack_conditionally(artifact_conf, indicator_type, pack_name, INDICATOR_TYPES_DIR)
    for connection in pack.connections:
        dump_pack_conditionally(artifact_conf, connection, pack_name, CONNECTIONS_DIR)
    for classifier in pack.classifiers:
        dump_pack_conditionally(artifact_conf, classifier, pack_name, CLASSIFIERS_DIR)
    for widget in pack.widgets:
        dump_pack_conditionally(artifact_conf, widget, pack_name, WIDGETS_DIR)
    for release_note in pack.release_notes:
        created_files = release_note.dump(artifact_conf.content_packs_path / pack_name / RELEASE_NOTES_DIR)
        log_created(artifact_conf.content_packs_path, release_note.path, created_files, artifact_conf.content.path)
    for tool in pack.tools:
        packs_files = tool.dump(artifact_conf.content_packs_path / pack_name / TOOLS_DIR)
        log_created(artifact_conf.content_packs_path, tool.path, packs_files, artifact_conf.content.path)
        if not artifact_conf.only_content_packs:
            new_files = [safe_copyfile(file, artifact_conf.content_new_path / file.name, artifact_conf.execution_start)
                         for file in packs_files]
            log_created(artifact_conf.content_new_path, tool.path, new_files, artifact_conf.content.path)
    if pack.pack_metadata:
        created_files = pack.pack_metadata.dump(artifact_conf.content_packs_path / pack_name)
        log_created(artifact_conf.content_packs_path, pack.pack_metadata.path, created_files, artifact_conf.content.path)
    if pack.readme:
        created_files = pack.readme.dump(artifact_conf.content_packs_path / pack_name)
        log_created(artifact_conf.content_packs_path, pack.readme.path, created_files, artifact_conf.content.path)


def dump_pack_conditionally(artifact_conf: ArtifactsConfiguration, content_object: ContentObject,
                            pack_name: str, pack_dir: str) -> None:
    """ Dump pack object by the following logic:
            1. content_packs:
                a. If to_version/toVersion value is bigger from SUPPORTED_BOUND_VERSION.
            2. content_new:
                a. Not from TestPlaybooks directory.
                b. If from_version/fromVersion value is stricly lower than SUPPORTED_BOUND_VERSION.
            3. content_test:
                a. Only from TestPlaybooks directory.
                b. If from_version/fromVersion value is stricly lower than SUPPORTED_BOUND_VERSION.

    Args:
        artifact_conf: Command line configuration.
        content_object: content_object (e.g. Integration/Script/Layout etc)
        pack_name: Pack directory name (e.g. Sample)
        pack_dir: interanl pack dir name (Integrations/Scripts etc... (Use constants).
    """
    content_pack_files: List[Path] = []
    content_new_files: List[Path] = []
    rm_files: List[Path] = []
    with content_files_handler(artifact_conf, pack_name, content_object, rm_files):
        # Content packs filter
        if content_object.to_version >= FIRST_MARKETPLACE_VERSION:
            content_pack_files.extend(
                content_object.dump(dest_dir=artifact_conf.content_packs_path / pack_name / pack_dir,
                                    change_log=False,
                                    readme=False))
            rm_files.extend(
                [created_file for created_file in content_pack_files if created_file.name.endswith('_45.yml')])
            real_pack_files = list(set(content_pack_files).difference(set(rm_files)))
            log_created(artifact_conf.content_packs_path,
                        content_object.path,
                        real_pack_files,
                        artifact_conf.content.path)
        else:
            log_ignored(artifact_conf.content_packs_path,
                        content_object.path,
                        artifact_conf.content.path,
                        f'To version < {FIRST_MARKETPLACE_VERSION}')

        if not artifact_conf.only_content_packs:
            if TEST_PLAYBOOKS_DIR == pack_dir:
                # Content test filter
                dump_test_conditionally(artifact_conf, content_object, content_pack_files)
            else:
                # Content new filter
                if content_object.from_version < FIRST_MARKETPLACE_VERSION:
                    if content_pack_files:
                        for file in content_pack_files:
                            content_new_files.append(safe_copyfile(src=file,
                                                                   dst=artifact_conf.content_new_path / file.name,
                                                                   execution_start=artifact_conf.execution_start))
                    else:
                        content_new_files.extend(content_object.dump(dest_dir=artifact_conf.content_new_path,
                                                                     readme=False,
                                                                     change_log=False))
                    log_created(artifact_conf.content_new_path,
                                content_object.path,
                                content_new_files,
                                artifact_conf.content.path)
                else:
                    log_ignored(artifact_conf.content_new_path,
                                content_object.path,
                                artifact_conf.content.path,
                                f"From version >= {FIRST_MARKETPLACE_VERSION}")


def dump_test_conditionally(artifact_conf: ArtifactsConfiguration, content_object: ContentObject,
                            created_files: Optional[List[Path]] = None) -> None:
    """ Dump test scripts/playbooks conditionally by the following logic:
            1. If from_version/fromVersion value is stricly lower than SUPPORTED_BOUND_VERSION.

    Args:
        created_files:
        artifact_conf: Command line configuration
        content_object: content_object (e.g. Integration/Script/Layout etc)
    """
    content_test_files: List[Path] = []
    if IGNORED_TEST_PLAYBOOKS_DIR not in content_object.path.parts:
        if content_object.from_version < FIRST_MARKETPLACE_VERSION:
            if created_files:
                for file in created_files:
                    content_test_files.append(safe_copyfile(src=file,
                                                            dst=artifact_conf.content_test_path / file.name,
                                                            execution_start=artifact_conf.execution_start))
            else:
                target = artifact_conf.content_test_path / content_object.path.name

                if target.exists() and target.stat().st_mtime >= artifact_conf.execution_start:
                    raise BaseException(f"Duplicate file in content repo: {content_object.path.name}")
                else:
                    content_test_files = content_object.dump(dest_dir=artifact_conf.content_test_path,
                                                             readme=False,
                                                             change_log=False)
            log_created(artifact_conf.content_test_path,
                        content_object.path,
                        content_test_files,
                        artifact_conf.content.path)
        else:
            log_ignored(artifact_conf.content_test_path,
                        content_object.path,
                        artifact_conf.content.path,
                        f"From version >= {FIRST_MARKETPLACE_VERSION}")


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


@contextmanager
def content_files_handler(artifact_conf: ArtifactsConfiguration, pack_name: str, content_object: ContentObject,
                          files_rm: List[Path]):
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
        pack_name: Pack directory name (e.g. Sample)
        files_rm: files to be remove in close
    """

    if pack_name == BASE_PACK and isinstance(content_object, Script) and \
            content_object.code_path and content_object.code_path.name == 'CommonServerPython.py':
        # modify_common_server_parameters(content_object.code_path)
        modify_common_server_constants(content_object.code_path,
                                       content_version=artifact_conf.content_version,
                                       branch_name=artifact_conf.content.git().active_branch)
    yield

    if pack_name == BASE_PACK and isinstance(content_object, Script) and \
            content_object.code_path and content_object.code_path.name == 'CommonServerPython.py':
        # modify_common_server_parameters(content_object.code_path)
        modify_common_server_constants(content_object.code_path,
                                       content_version='0.0.0',
                                       branch_name='master')

    # Delete yaml which created by Unifier in packs and to_version/toVersion lower than NEWEST_SUPPORTED_VERSION
    for file_path in files_rm:
        file_path.unlink()


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


def log_created(target: Path, file_path: Path, new_files: List[Path], content_path: Path):
    files = ", ".join([str(file.relative_to(target)) for file in new_files])
    msg = f'{target.name} - {Colors.Fg.green}Add{Colors.reset} - {file_path.relative_to(content_path)}' \
          f' {Colors.Fg.blue}to{Colors.reset} {files}'
    logger.info(msg)


def log_ignored(target: Path, file_path: Path, content_path: Path, reason: str):
    msg = f'{target.name} - {Colors.Fg.red}Ignore{Colors.reset} - {file_path.relative_to(content_path)} - ' \
          f'{Colors.Fg.red}Reason {reason}{Colors.reset}'
    logger.info(msg)


def log_results(artifact_conf: ArtifactsConfiguration):
    for artifact in [artifact_conf.content_test_path,
                     artifact_conf.content_new_path,
                     artifact_conf.content_packs_path]:
        if artifact_conf.zip_artifacts:
            logger.info(f"Created - {Colors.Fg.blue}{artifact.with_suffix('.zip')}{Colors.reset}")
        else:
            logger.info(f"Created - {Colors.Fg.blue}{artifact}{Colors.reset}")
