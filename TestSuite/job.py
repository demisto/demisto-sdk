from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import DEFAULT_JOB_FROM_VERSION
from TestSuite.json_based import JSONBased


class Job(JSONBased):
    def __init__(self, pure_name: str, jobs_dir_path: Path, is_feed: bool, selected_feeds: Optional[List[str]] = None,
                 details: str = ''):
        super().__init__(jobs_dir_path, pure_name, "job")
        self.pure_name = pure_name
        self.is_feed = is_feed
        self.selected_feeds = selected_feeds or []
        self.details = details

        self.create_default_job()

    def create_default_job(self):
        self.write_json({
            'fromVersion': DEFAULT_JOB_FROM_VERSION,
            'id': self.pure_name,
            'name': self.pure_name,
            'isFeed': self.is_feed,
            'details': self.details,
            'selectedFeeds': self.selected_feeds or [],
            'isAllFeeds': self.is_feed and not self.selected_feeds,
            'playbookId': f'{self.pure_name}_playbookId',  # todo can we assume it exists? otherwise, tests may fail
        })
