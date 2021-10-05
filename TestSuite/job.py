from pathlib import Path
from typing import List, Optional

from TestSuite.file import File
from TestSuite.json_based import JSONBased


class Job:
    def __init__(self,
                 jobs_path: Path,
                 pure_name: str,
                 repo,
                 is_feed: bool,
                 selected_feeds: Optional[List[str]] = None):
        self.pure_name = pure_name
        self.is_feed = is_feed
        self.selected_feeds = selected_feeds

        self._repo = repo
        self.jobs_path = jobs_path
        self.jobs_path.mkdir(exist_ok=True)
        self.path = str(self.jobs_path)

        self.json = JSONBased(self.jobs_path, pure_name, 'job')
        self.readme = File(self.jobs_path / f'{self.pure_name}_README.md', self._repo.path)
        self.description = File(self.jobs_path / f'{self.pure_name}_description.md', self._repo.path)
        self.changelog = File(self.jobs_path / f'{self.pure_name}_CHANGELOG.md', self._repo.path)

        self.create_default_job()

    def build(
            self,
            json_: Optional[dict] = None,
            readme: Optional[str] = None,
            description: Optional[str] = None,
            changelog: Optional[str] = None,
    ):
        """Writes not None objects to files """
        if json_ is not None:
            self.json.write_json(json_)
        if readme is not None:
            self.readme.write(readme)
        if description is not None:
            self.description.write(description)
        if changelog is not None:
            self.changelog.write(changelog)

    def create_default_job(self):
        self.build({
            'name': self.pure_name,
            'minutesToTimeout': 0,  # todo
            'description': "",
            'playbookId': "",  # todo
            'id': self.pure_name,  # todo
            'fromServerVersion': '6.5.0',
            'currentIncidentId': 1,
            'lastRunTime': '',  # todo
            'nextRunTime': '',  # todo
            'displayNextRunTime': '',  # todo
            'disabledNextRunTime': '',  # todo
            'schedulingStatus': 'enabled',
            'previousRunStatus': 'idle',  # todo
            'tags': [],
            'shouldTriggerNew': False,
            'closePrevRun': False,
            'notifyOwner': False,
            'isFeed': self.is_feed,
            'selectedFeeds': self.selected_feeds or [],
            'isAllFeeds': self.is_feed and not self.selected_feeds
        })
