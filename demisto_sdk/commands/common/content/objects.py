from typing import Union

from wcmatch.pathlib import Path

from code_object import CodeObject
from demisto_sdk.commands.common.content.generic_objects.yaml_object import YAMLObject
from json_object import JSONObject
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.common.constants import SCRIPTS_DIR


class Integration(CodeObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "integration"

    def unify(self, dest) -> Path:
        if not self.is_unify():
            try:
                unifier = Unifier(input=str(self.yaml_path.parent), output=dest, force=True)
                unified_file_path: str = unifier.merge_script_package_to_yml()[0]
            except Exception as e:
                raise BaseException(f"Unable to unify integration {self.yaml_path}, Full error: {e}")
        else:
            raise BaseException(f"Integration allready unified - {self.yaml_path}")

        return Path(unified_file_path)


class Script(CodeObject):
    def __init__(self, path: Union[Path, str]) -> Path:
        super().__init__(path)
        self._prefix = "script"

    def unify(self, dest):
        if not self.is_unify():
            try:
                unifier = Unifier(input=str(self.yaml_path.parent), dir_name=SCRIPTS_DIR, output=dest, force=True)
                unified_file_path: str = unifier.merge_script_package_to_yml()[0]
            except Exception as e:
                raise BaseException(f"Unable to unify integration {self.yaml_path}, Full error: {e}")
        else:
            raise BaseException(f"Script allready unified - {self.yaml_path}")

        return Path(unified_file_path)


class Playbook(YAMLObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "playbook"


class Report(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "report"


class Dashboard(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "dashboard"


class IncidentType(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "incidenttype"


class IncidentField(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "incidentfield"


class Layout(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = ""


class Classifier(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "classifier"


class IndicatorType(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "indicatortype"


class IndicatorField(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "indicatorfield"


class Connection(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "connection"


class Widget(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._prefix = "widget"

