import json

from TestSuite.file import File


class JSONBased(File):
    def write_json(self, obj: dict):
        self._tmp_path.write_text(json.dumps(obj))
