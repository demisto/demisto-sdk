from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMDashboard(JSONBased):
    def __init__(
        self,
        name: str,
        xsiam_dashboard_dir_path: Path,
        json_content: dict = {},
    ):
        self.xsiam_dashboard_tmp_path = (
            xsiam_dashboard_dir_path / f'{name}.json'
        )
        self.name = name

        super().__init__(xsiam_dashboard_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_xsiam_dashboard()

    def create_default_xsiam_dashboard(self):
        self.write_json(
            {'dashboards_data': [{'global_id': self.name, 'name': self.name}]}
        )
