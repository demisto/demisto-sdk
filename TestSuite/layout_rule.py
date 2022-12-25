from pathlib import Path

from TestSuite.json_based import JSONBased


class LayoutRule(JSONBased):
    def __init__(self, name: str, layout_rule_dir_path: Path, json_content: dict = None):
        self.layout_rule_tmp_path = layout_rule_dir_path / f"{name}.json"
        self.name = name

        super().__init__(layout_rule_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_trigger()

    def create_default_trigger(self):
        self.write_json({
            'rule_id': self.name,
            'rule_name': self.name,
        })
