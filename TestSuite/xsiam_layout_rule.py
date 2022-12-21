from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMLayoutRule(JSONBased):
    def __init__(self, name: str, xsiam_layout_rule_dir_path: Path, json_content: dict = None):
        self.xsiam_layout_rule_tmp_path = xsiam_layout_rule_dir_path / f"{name}.json"
        self.name = name

        super().__init__(xsiam_layout_rule_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_trigger()

    def create_default_trigger(self):
        self.write_json({
            'xsiam_layout_rule_id': self.name,
            'xsiam_layout_rule_name': self.name,
        })
