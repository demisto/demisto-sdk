from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR, CONNECTIONS_DIR,
                                                   DASHBOARDS_DIR, INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR, INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR, LAYOUTS_DIR, PLAYBOOKS_DIR, RELEASE_NOTES_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR, WIDGETS_DIR)
from objects import (Integration, Script, Playbook, IncidentField, IncidentType, Classifier, Connection,
                     IndicatorField, IndicatorType, Report, Dashboard, Layout, Widget)
from demisto_sdk.commands.common.content.generic_objects.code_object import CodeObject
from typing import Union, Iterator, Dict, Optional, Tuple


class Pack:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)

    def _content_files_list_generator_factory(self, content_object, dir_name, suffix: str) -> Tuple[str, object]:
        objects_path = (self._path / dir_name).glob(patterns=[f"*.{suffix}", f"{self.path.name}/*{suffix}"])
        for object_path in objects_path:
            yield content_object(object_path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def integrations(self) -> Iterator[Integration]:
        return self._content_files_list_generator_factory(content_object=Integration,
                                                          dir_name=INTEGRATIONS_DIR,
                                                          suffix="yml")

    @property
    def scripts(self) -> Iterator[Script]:
        return self._content_files_list_generator_factory(content_object=Script,
                                                          dir_name=SCRIPTS_DIR,
                                                          suffix="yml")

    @property
    def playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(content_object=Playbook,
                                                          dir_name=PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def reports(self) -> Iterator[Report]:
        return self._content_files_list_generator_factory(content_object=Report,
                                                          dir_name=REPORTS_DIR,
                                                          suffix="json")

    @property
    def dashboards(self) -> Iterator[Dashboard]:
        return self._content_files_list_generator_factory(content_object=Dashboard,
                                                          dir_name=DASHBOARDS_DIR,
                                                          suffix="json")

    @property
    def incident_types(self) -> Iterator[IncidentType]:
        return self._content_files_list_generator_factory(content_object=IncidentType,
                                                          dir_name=INCIDENT_TYPES_DIR,
                                                          suffix="json")

    @property
    def incident_fields(self) -> Iterator[IncidentField]:
        return self._content_files_list_generator_factory(content_object=IncidentField,
                                                          dir_name=INCIDENT_FIELDS_DIR,
                                                          suffix="json")

    @property
    def layouts(self) -> Iterator[Layout]:
        return self._content_files_list_generator_factory(content_object=Layout,
                                                          dir_name=LAYOUTS_DIR,
                                                          suffix="json")

    @property
    def classifiers(self) -> Iterator[Classifier]:
        return self._content_files_list_generator_factory(content_object=Classifier,
                                                          dir_name=CLASSIFIERS_DIR,
                                                          suffix="json")

    @property
    def indicator_types(self) -> Iterator[IndicatorType]:
        return self._content_files_list_generator_factory(content_object=IndicatorType,
                                                          dir_name=INDICATOR_TYPES_DIR,
                                                          suffix="json")

    @property
    def indicator_fields(self) -> Iterator[IndicatorField]:
        return self._content_files_list_generator_factory(content_object=IndicatorField,
                                                          dir_name=INDICATOR_FIELDS_DIR,
                                                          suffix="json")

    @property
    def connections(self) -> Iterator[Connection]:
        return self._content_files_list_generator_factory(content_object=Connection,
                                                          dir_name=CONNECTIONS_DIR,
                                                          suffix="json")

    @property
    def test_playbooks(self) -> Iterator[Playbook]:
        return self._content_files_list_generator_factory(content_object=Playbook,
                                                          dir_name=TEST_PLAYBOOKS_DIR,
                                                          suffix="yml")

    @property
    def widget(self) -> Iterator[Widget]:
        return self._content_files_list_generator_factory(content_object=Widget,
                                                          dir_name=WIDGETS_DIR,
                                                          suffix="json")

    @property
    def release_notes(self) -> Iterator[Path]:
        return self._path.glob(f"{RELEASE_NOTES_DIR}/*.md")

    @property
    def pack_metadata(self) -> Optional[Path]:
        return next(self._path.glob("pack_metadata.json"), None)

    @property
    def secrets_ignore(self) -> Optional[Path]:
        return next(self._path.glob(".secrets-ignore"), None)

    @property
    def readme(self) -> Optional[Path]:
        return next(self._path.glob("README.md"), None)

    @property
    def changelog(self) -> Optional[Path]:
        return next(self._path.glob("CHANGELOG.md"), None)

    @staticmethod
    def _dump_list(dest: Path, iterator: Iterator, change_log: bool, readme: bool):
        for obj in iterator:
            obj.dump(dest, change_log, readme)

    def dump(self, dest: Union[str, Path], integrations: bool = True, scripts: bool = True,
             playbooks: bool = True, reports: bool = True, dashboards: bool = True, incident_types: bool = True,
             incident_fields: bool = True, layouts: bool = True, classifiers: bool = True, indicator_types: bool = True,
             indicator_fields: bool = True, connections: bool = True, test_playbooks: bool = True, widget: bool = True,
             release_notes: bool = True, pack_metadata: bool = True, secrets_ignore: bool = True, readme: bool = True,
             change_log: bool = True):
        dest = Path(dest) / self.path.name
        dest.mkdir(parents=True, exist_ok=True)
        if integrations:
            self._dump_list(dest / INTEGRATIONS_DIR, self.integrations, change_log, readme)
        if scripts:
            self._dump_list(dest / SCRIPTS_DIR, self.scripts, change_log, readme)
        if playbooks:
            self._dump_list(dest / PLAYBOOKS_DIR, self.playbooks, change_log, readme)
        if reports:
            self._dump_list(dest / REPORTS_DIR, self.reports, change_log, readme)
        if dashboards:
            self._dump_list(dest / DASHBOARDS_DIR, self.dashboards, change_log, readme)
        if incident_types:
            self._dump_list(dest / INCIDENT_TYPES_DIR, self.incident_types, change_log, readme)
        if incident_fields:
            self._dump_list(dest / INCIDENT_FIELDS_DIR, self.incident_fields, change_log, readme)
        if layouts:
            self._dump_list(dest / LAYOUTS_DIR, self.layouts, change_log, readme)
        if classifiers:
            self._dump_list(dest / CLASSIFIERS_DIR, self.classifiers, change_log, readme)
        if indicator_types:
            self._dump_list(dest / INDICATOR_TYPES_DIR, self.indicator_types, change_log, readme)
        if indicator_fields:
            self._dump_list(dest / INCIDENT_FIELDS_DIR, self.indicator_fields, change_log, readme)
        if connections:
            self._dump_list(dest / CONNECTIONS_DIR, self.connections, change_log, readme)
        if test_playbooks:
            self._dump_list(dest / TEST_PLAYBOOKS_DIR, self.test_playbooks, change_log, readme)
        if widget:
            self._dump_list(dest / WIDGETS_DIR, self.widget, change_log, readme)
        # if release_notes:
        #     self._dump_list(dest / RELEASE_NOTES_DIR, self.release_notes)
        # if pack_metadata:
        #     self._dump_list(dest, self.pack_metadata)
        # if secrets_ignore:
        #     self._dump_list(dest, self.secrets_ignore)
        # if readme:
        #     self._dump_list(dest, self.readme)
        # if changelog:
        #     self._dump_list(dest, self.changelog)
