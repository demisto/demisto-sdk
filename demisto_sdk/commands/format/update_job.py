import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from TestSuite.job import DEFAULT_JOB_FROM_VERSION

SELECTED_FEEDS = 'selectedFeeds'
IS_ALL_FEEDS = 'isAllFeeds'
IS_FEED = 'isFeed'


class JobJSONFormat(BaseUpdateJSON):
    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = DEFAULT_JOB_FROM_VERSION,
                 no_validate: bool = False, verbose: bool = False, **kwargs):
        self.is_feed_defined = IS_FEED in self.data
        self.selected_feeds_defined = SELECTED_FEEDS in self.data
        self.is_all_feeds_defined = IS_ALL_FEEDS in self.data

        self.is_feed = self.data.get(IS_FEED)
        self.selected_feeds = self.data.get(SELECTED_FEEDS)
        self.is_all_feeds = self.data.get(IS_ALL_FEEDS)

        super().__init__(input, output, path, from_version, no_validate, verbose, **kwargs)

    def attempt_infer_feed_fields(self):
        """
        Calls inferring methods by their preferred order, correcting them if possible (in obvious cases)
        """

        def _set_default_selected_feeds_when_applicable():  # todo better name?
            """
            Sets missing selectedFeeds field with an empty list as default,
            When the job certainly shouldn't have any values there. (not isFeed, OR feed and allFeeds)
            """
            if self.is_feed_defined:
                if (not self.selected_feeds_defined) \
                        and (self.is_all_feeds or (not self.is_feed)):
                    self.data['selectedFeeds'] = []

        def _attempt_infer_is_feed():
            """
            uses isAllFeeds and selectedFeed values (when exist) to determine isFeed and set it
            better call after set_default_selected_feeds_when_applicable
            """
            if not self.is_feed_defined:
                if self.is_all_feeds or self.selected_feeds:
                    self.is_feed = True

                elif self.selected_feeds_defined and self.is_all_feeds_defined \
                        and not any((self.selected_feeds, self.is_all_feeds)):
                    self.is_feed = False

        # order matters
        _set_default_selected_feeds_when_applicable()
        _attempt_infer_is_feed()

    def run_format(self):
        try:
            super().update_json()
            self.update_id()
            self.attempt_infer_feed_fields()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as e:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {e}', fg='red')
            return ERROR_RETURN_CODE
