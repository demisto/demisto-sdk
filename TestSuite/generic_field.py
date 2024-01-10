from pathlib import Path

from TestSuite.json_based import JSONBased


class GenericField(JSONBased):
    def __init__(
        self, name: str, generic_field_dir_path: Path, json_content: dict = None
    ):
        self.generic_field_file_path = generic_field_dir_path / f"{name}.json"
        super().__init__(
            dir_path=generic_field_dir_path,
            name=name,
            prefix="",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "cliName": self.name.lower(),
                "id": self.id,
                "name": self.id,
                "definitionId": self.id,
                "type": "shortText",
                "fromVersion": "6.10.0",
            }
        )
