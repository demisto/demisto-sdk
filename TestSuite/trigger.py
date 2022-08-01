from pathlib import Path

from TestSuite.json_based import JSONBased


class Trigger(JSONBased):
    def __init__(self, name: str, trigger_dir_path: Path, json_content: dict = {}):
        self.trigger_tmp_path = trigger_dir_path / f"{name}.json"
        self.name = name

        super().__init__(trigger_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_trigger()

    def create_default_trigger(self):
        self.write_json({
            'trigger_id': self.name,
            'trigger_name': self.name,
        })
