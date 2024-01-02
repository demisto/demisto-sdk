from pathlib import Path

from TestSuite.json_based import JSONBased


class GenericType(JSONBased):
    def __init__(
        self, name: str, generic_type_dir_path: Path, json_content: dict = None
    ):
        self.generic_type_file_path = generic_type_dir_path / f"{name}.json"
        super().__init__(
            dir_path=generic_type_dir_path,
            name=name,
            prefix="",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "id": self.name,
                "name": self.name,
                "definitionId": self.name,
                "fromVersion": "6.10.0",
            }
        )
