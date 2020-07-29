from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR, CONNECTIONS_DIR,
                                                   DASHBOARDS_DIR, INCIDENT_FIELDS_DIR, DOC_FILES_DIR,
                                                   INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR, INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR, LAYOUTS_DIR, PLAYBOOKS_DIR, RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR, WIDGETS_DIR, TOOLS_DIR)
from demisto_sdk.commands.common.content import (Integration, Script, Playbook, IncidentField, IncidentType, Classifier,
                                                 Connection, IndicatorField, IndicatorType, Report, Dashboard, Layout,
                                                 Widget, ReleaseNote, PackMetaData, SecretIgnore, Readme, ChangeLog,
                                                 PackIgnore, Tool, DocFile)
from demisto_sdk.commands.common.content.objects_factory import ContentObjectFacotry
from typing import Union, Iterator, Optional, Tuple, Callable


class Pack:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    def _content_files_list_generator_factory(self, dir_name, suffix: str) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob(patterns=[f"*.{suffix}", f"*/*.{suffix}"])
        for object_path in objects_path:
            yield ContentObjectFacotry.from_path(object_path)

    def _content_dirs_list_generator_factory(self, dir_name) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob(patterns=[f"*/"])
        for object_path in objects_path:
            yield ContentObjectFacotry.from_path(object_path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def integrations(self) -> Iterator[Integration]:
        return self._content_files_list_generator_factory(dir_name=INTEGRATIONS_DIR,
                                                          suffix="yml")

    @property
    def scripts(self) -> Iterator[Script]:
        return self._content_files_list_generator_factory(dir_name=SCRIPTS_DIR,
                                                          suffix="yml")

    @property
    def playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(dir_name=PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def reports(self) -> Iterator[Report]:
        return self._content_files_list_generator_factory(dir_name=REPORTS_DIR,
                                                          suffix="json")

    @property
    def dashboards(self) -> Iterator[Dashboard]:
        return self._content_files_list_generator_factory(dir_name=DASHBOARDS_DIR,
                                                          suffix="json")

    @property
    def incident_types(self) -> Iterator[IncidentType]:
        return self._content_files_list_generator_factory(dir_name=INCIDENT_TYPES_DIR,
                                                          suffix="json")

    @property
    def incident_fields(self) -> Iterator[IncidentField]:
        return self._content_files_list_generator_factory(dir_name=INCIDENT_FIELDS_DIR,
                                                          suffix="json")

    @property
    def layouts(self) -> Iterator[Layout]:
        return self._content_files_list_generator_factory(dir_name=LAYOUTS_DIR,
                                                          suffix="json")

    @property
    def classifiers(self) -> Iterator[Classifier]:
        return self._content_files_list_generator_factory(dir_name=CLASSIFIERS_DIR,
                                                          suffix="json")

    @property
    def indicator_types(self) -> Iterator[IndicatorType]:
        return self._content_files_list_generator_factory(dir_name=INDICATOR_TYPES_DIR,
                                                          suffix="json")

    @property
    def indicator_fields(self) -> Iterator[IndicatorField]:
        return self._content_files_list_generator_factory(dir_name=INDICATOR_FIELDS_DIR,
                                                          suffix="json")

    @property
    def connections(self) -> Iterator[Connection]:
        return self._content_files_list_generator_factory(dir_name=CONNECTIONS_DIR,
                                                          suffix="json")

    @property
    def test_playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def widgets(self) -> Iterator[Widget]:
        return self._content_files_list_generator_factory(dir_name=WIDGETS_DIR,
                                                          suffix="json")

    @property
    def release_notes(self) -> Iterator[ReleaseNote]:
        return self._content_files_list_generator_factory(dir_name=RELEASE_NOTES_DIR,
                                                          suffix="md")

    @property
    def tools(self) -> Iterator[Tool]:
        return self._content_dirs_list_generator_factory(dir_name=TOOLS_DIR)

    @property
    def doc_files(self) -> Iterator[DocFile]:
        return self._content_files_list_generator_factory(dir_name=DOC_FILES_DIR,
                                                          suffix="*")

    @property
    def pack_metadata(self) -> Optional[PackMetaData]:
        file = self._path / "pack_metadata.json"
        if file.exists():
            return PackMetaData(file)

    @property
    def secrets_ignore(self) -> Optional[SecretIgnore]:
        file = self._path / ".secrets-ignore"
        if file.exists():
            return SecretIgnore(file)

    @property
    def pack_ignore(self) -> Optional[PackIgnore]:
        file = self._path / ".pack-ignore"
        if file.exists():
            return PackIgnore(file)

    @property
    def readme(self) -> Optional[Readme]:
        file = self._path / "README.md"
        if file.exists():
            return Readme(file)

    @property
    def changelog(self) -> Optional[ChangeLog]:
        file = self._path / "CHANGELOG.md"
        if file.exists():
            return ChangeLog(file)

    @staticmethod
    def _dump_list(dest: Path, iterator: Iterator, **kwargs):
        for obj in iterator:
            obj.dump(dest, **kwargs)

    def dump(self, dest_dir: Union[str, Path], integrations: bool = True, scripts: bool = True, unify: bool = True,
             playbooks: bool = True, reports: bool = True, dashboards: bool = True, incident_types: bool = True,
             incident_fields: bool = True, layouts: bool = True, classifiers: bool = True, indicator_types: bool = True,
             indicator_fields: bool = True, connections: bool = True, test_playbooks: bool = True, widgets: bool = True,
             release_notes: bool = True, pack_metadata: bool = True, secrets_ignore: bool = True, readme: bool = True,
             tools: bool = True, change_log: bool = True, pack_ignore: bool = True, pre_hooks: Optional[Callable] = None,
             post_hooks: Optional[Callable] = None, filter: Optional[Callable] = None):
        dest = Path(dest_dir) / self.path.name
        dest.mkdir(parents=True, exist_ok=True)
        if integrations:
            self._dump_list(dest=dest / INTEGRATIONS_DIR, iterator=self.integrations, change_log=change_log,
                            readme=readme, unify=unify, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if scripts:
            self._dump_list(dest=dest / SCRIPTS_DIR, iterator=self.scripts, change_log=change_log, readme=readme,
                            unify=unify, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if playbooks:
            self._dump_list(dest=dest / PLAYBOOKS_DIR, iterator=self.playbooks, change_log=change_log, readme=readme,
                            pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if reports:
            self._dump_list(dest=dest / REPORTS_DIR, iterator=self.reports, change_log=change_log, readme=readme,
                            pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if dashboards:
            self._dump_list(dest=dest / DASHBOARDS_DIR, iterator=self.dashboards, change_log=change_log, readme=readme,
                            pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if incident_types:
            self._dump_list(dest=dest / INCIDENT_TYPES_DIR, iterator=self.incident_types, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if incident_fields:
            self._dump_list(dest=dest / INCIDENT_FIELDS_DIR, iterator=self.incident_fields, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if layouts:
            self._dump_list(dest=dest / LAYOUTS_DIR, iterator=self.layouts, change_log=change_log, readme=readme,
                            pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if classifiers:
            self._dump_list(dest=dest / CLASSIFIERS_DIR, iterator=self.classifiers, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if indicator_types:
            self._dump_list(dest=dest / INDICATOR_TYPES_DIR, iterator=self.indicator_types, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if indicator_fields:
            self._dump_list(dest=dest / INCIDENT_FIELDS_DIR, iterator=self.indicator_fields, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if connections:
            self._dump_list(dest=dest / CONNECTIONS_DIR, iterator=self.connections, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if test_playbooks:
            self._dump_list(dest=dest / TEST_PLAYBOOKS_DIR, iterator=self.test_playbooks, change_log=change_log,
                            readme=readme, pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if widgets:
            self._dump_list(dest=dest / WIDGETS_DIR, iterator=self.widgets, change_log=change_log, readme=readme,
                            pre_hooks=pre_hooks, post_hooks=post_hooks, filter=filter)
        if tools:
            self._dump_list(dest=dest / TOOLS_DIR, iterator=self.tools)
        if release_notes and self.release_notes:
            self._dump_list(dest=dest / RELEASE_NOTES_DIR, iterator=self.release_notes)
        if pack_metadata and self.pack_metadata:
            self.pack_metadata.dump(dest_dir=dest)
        if secrets_ignore and self.secrets_ignore:
            self.secrets_ignore.dump(dest_dir=dest)
        if pack_ignore and self.pack_ignore:
            self.secrets_ignore.dump(dest_dir=dest)
        if readme and self.readme:
            self.readme.dump(dest_dir=dest)
        if change_log and self.changelog:
            self.changelog.dump(dest_dir=dest)
