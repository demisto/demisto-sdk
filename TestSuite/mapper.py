from pathlib import Path

from TestSuite.json_based import JSONBased


class Mapper(JSONBased):
    def __init__(self, name: str, mapper_dir_path: Path, json_content: dict = None):
        self.mapper_tmp_path = mapper_dir_path / f"{name}.json"
        super().__init__(
            dir_path=mapper_dir_path, name=name, prefix="", json_content=json_content
        )

    def create_default(self):
        self.write_json(
            {
                "description": "test description",
                "feed": False,
                "id": self.id,
                "keyTypeMap": {},
                "mapping": {
                    "dbot_classification_incident_type_all": {
                        "dontMapEventToLabels": True,
                    }
                },
                "name": self.id,
                "nameRaw": "test",
                "packID": "",
                "packName": "",
                "type": "mapping-incoming",
                "version": -1,
            }
        )
