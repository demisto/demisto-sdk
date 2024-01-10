from pathlib import Path

from TestSuite.json_based import JSONBased


class GenericDefinition(JSONBased):
    def __init__(
        self, name: str, generic_definition_dir_path: Path, json_content: dict = None
    ):
        self.generic_definition_file_path = generic_definition_dir_path / f"{name}.json"
        super().__init__(
            dir_path=generic_definition_dir_path,
            name=name,
            prefix="",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "version": -1,
                "fromVersion": "6.10.0",
                "id": self.id,
                "name": self.id,
                "pluralName": self.id,
            }
        )
