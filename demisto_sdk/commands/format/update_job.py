import traceback

import click

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

DEFAULT_JOB_FROM_VERSION = '6.5.0'

SELECTED_FEEDS = 'selectedFeeds'
IS_ALL_FEEDS = 'isAllFeeds'
IS_FEED = 'isFeed'


class JobJSONFormat(BaseUpdateJSON):
    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False, verbose: bool = False, **kwargs):
        super().__init__(input, output, path, from_version, no_validate, verbose, **kwargs)
        self.is_feed_defined = IS_FEED in self.data
        self.selected_feeds_defined = SELECTED_FEEDS in self.data
        self.is_all_feeds_defined = IS_ALL_FEEDS in self.data

        self.is_feed = self.data.get(IS_FEED)
        self.selected_feeds = self.data.get(SELECTED_FEEDS)
        self.is_all_feeds = self.data.get(IS_ALL_FEEDS)

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
                if (not self.selected_feeds_defined) and (
                        self.is_all_feeds or  # all feeds -> selectedFeeds should be empty
                        (not self.is_feed)  # not related to feed -> selectedFeeds should be empty
                ):
                    self.selected_feeds_defined = True
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
        # _attempt_infer_is_feed() # todo decide whether to use

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            self.update_id()
            self.attempt_infer_feed_fields()
            super().update_json()
            self.remove_unnecessary_keys()
            self.set_from_server_version_to_default()

            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE

        except Exception as err:
            print(''.join(traceback.format_exception(etype=type(err), value=err, tb=err.__traceback__)))
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self):
        format_result = self.run_format()
        result_code = self.initiate_file_validator() if format_result == SUCCESS_RETURN_CODE else SKIP_RETURN_CODE
        return format_result, result_code

    def set_from_server_version_to_default(self, location=None):
        self.set_default_value('fromServerVersion', DEFAULT_JOB_FROM_VERSION, location=location)
