from pathlib import Path

from TestSuite.json_based import JSONBased


class Trigger(JSONBased):
    def __init__(self, name: str, trigger_dir_path: Path, json_content: dict = None):
        self.trigger_tmp_path = trigger_dir_path / f"{name}.json"
        self.name = name

        super().__init__(trigger_dir_path, name, "")

        if json_content:
            # Write exactly what the test provided; do not auto-normalize.
            self.write_json(json_content)
        else:
            self.create_default_trigger()

    def create_default_trigger(self):
        self.write_json(
            {
                "id": self.id,
                "trigger_id": self.id,
                "name": self.id,
                "playbook_id": "mock playbook",
                "suggestion_reason": "mock reason",
                "description": "desc",
                "trigger_name": self.id,
                "alerts_filter": {
                    "filter": {
                        "AND": [
                            {
                                "SEARCH_FIELD": "alert_name",
                                "SEARCH_TYPE": "EQ",
                                "SEARCH_VALUE": "multiple unauthorized action attempts detected by a user",
                            }
                        ]
                    }
                },
            }
        )
