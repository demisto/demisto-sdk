from pathlib import Path

from TestSuite.json_based import JSONBased


class Classifier(JSONBased):
    def __init__(self, name: str, classifier_dir_path: Path, json_content: dict = None):
        self.classifier_tmp_path = classifier_dir_path / f"{name}.json"
        super().__init__(
            dir_path=classifier_dir_path,
            name=name,
            prefix="classifier",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "feed": False,
                "id": self.id,
                "keyTypeMap": {"Test": "Test type"},
                "mapping": None,
                "name": self.id,
                "nameRaw": self.id,
                "packID": "",
                "packName": "",
                "transformer": {"simple": "Field"},
                "type": "classification",
                "version": -1,
            }
        )
