from pathlib import Path

from TestSuite.json_based import JSONBased


class IndicatorType(JSONBased):
    def __init__(
        self, name: str, indicator_type_dir_path: Path, json_content: dict = None
    ):
        self.indicator_type_file_path = indicator_type_dir_path / f"{name}.json"
        super().__init__(
            dir_path=indicator_type_dir_path,
            name=name,
            prefix="reputation",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "id": self.id,
                "details": self.id,
                "preProcessingScript": "",
                "fromVersion": "6.10.0",
            }
        )
