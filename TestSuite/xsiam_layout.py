from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMLayout(JSONBased):
    def __init__(self, name: str, xsiam_layout_dir_path: Path, json_content: dict = None):
        self.xsiam_dashboard_tmp_path = xsiam_layout_dir_path / f"{name}.json"
        self.name = name

        super().__init__(xsiam_layout_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_xsiam_dashboard()

    def create_default_xsiam_dashboard(self):
        self.write_json({
            "kind": "kind_test",
            "layout": {
                "id": "id_test",
                "name": self.name,
                "version": -1,
                "kind": "kind_test",
                "typeId": "typeId_test",
                "sections": [
                    {
                        "description": "",
                        "fields": [
                            {
                                "fieldId": "filedId_test",
                                "isVisible": True
                            }
                        ],
                        "isVisible": True,
                        "name": self.name,
                        "query": None,
                        "queryType": "",
                        "readOnly": False,
                        "type": ""
                    }
                ]
            },
            "fromVersion": "5.0.0",
            "toVersion": "5.9.9",
            "typeId": "typeId_test",
            "version": -1,
            "description": ""
        })
