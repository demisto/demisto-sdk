from json.decoder import JSONDecodeError
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import DEFAULT_JOB_FROM_VERSION
from TestSuite.json_based import JSONBased


class Job(JSONBased):
    def __init__(self, pure_name: str, jobs_dir_path: Path, is_feed: bool, selected_feeds: Optional[List[str]] = None,
                 details: str = ''):
        super().__init__(jobs_dir_path, pure_name, "job")
        self.pure_name = pure_name
        self.create_default_job(
            is_feed=is_feed,
            selected_feeds=selected_feeds or [],
            details=details
        )

    def create_default_job(self, is_feed: bool, selected_feeds: list, details: str):
        self.write_json({
            'fromVersion': DEFAULT_JOB_FROM_VERSION,
            'id': self.pure_name,
            'name': self.pure_name,
            'isFeed': is_feed,
            'details': details,
            'selectedFeeds': selected_feeds,
            'isAllFeeds': is_feed and not selected_feeds,
            'playbookId': self.playbook_name
        })

    @property
    def playbook_name(self):
        default = f'job-{self.pure_name}_playbook'

        try:
            return (self.read_json_as_dict() or {}).get('playbookId', default)

        except JSONDecodeError:  # file not yet written
            return default
