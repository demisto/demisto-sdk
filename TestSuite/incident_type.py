from pathlib import Path

from TestSuite.json_based import JSONBased


class IncidentType(JSONBased):
    def __init__(
        self, name: str, incident_type_dir_path: Path, json_content: dict = None
    ):
        self.incident_type_file_path = incident_type_dir_path / f"{name}.json"
        super().__init__(
            dir_path=incident_type_dir_path,
            name=name,
            prefix="incidenttype",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "id": self.id,
                "description": "test description",
                "name": self.id,
                "hours": 0,
                "days": 3,
                "weeks": 1,
                "preProcessingScript": "",
                "fromVersion": "6.10.0",
            }
        )
