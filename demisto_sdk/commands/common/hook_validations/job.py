from distutils.version import LooseVersion

from demisto_sdk.commands.common.constants import DEFAULT_JOB_FROM_VERSION, JOB
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class JobValidator(ContentEntityValidator):

    def __init__(self, structure_validator, ignored_errors=False, print_as_warnings=False, json_file_path=None,
                 **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, json_file_path=json_file_path,
                         **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self._errors = []

    def get_errors(self):
        return "\n".join(self._errors)

    def is_valid_version(self):
        # not validated
        return True

    def is_valid_fromversion(self):
        if not self.from_version or LooseVersion(self.from_version) < LooseVersion(DEFAULT_JOB_FROM_VERSION):
            error_message, error_code = Errors.invalid_fromversion_in_job(self.from_version)
            formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
            if formatted_error:
                self._errors.append(error_message)
                return False
        return True

    def is_valid_feed_fields(self):
        is_feed = self.current_file.get('isFeed')
        selected_feeds = self.current_file.get('selectedFeeds')
        is_all_feeds = self.current_file.get('isAllFeeds')

        if is_feed:
            if selected_feeds and is_all_feeds:
                error_message, error_code = Errors.invalid_both_selected_and_all_feeds_in_job()
                formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
                if formatted_error:
                    self._errors.append(error_message)
                    return False

            elif selected_feeds:
                return True  # feeds are validated in the id_set

            elif is_all_feeds:
                return True

            else:  # neither selected_fields nor is_all_fields
                error_message, error_code = Errors.missing_field_values_in_feed_job()
                formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
                if formatted_error:
                    self._errors.append(error_message)
                    return False

        else:  # is_feed=false
            if selected_feeds or is_all_feeds:
                error_message, error_code = \
                    Errors.unexpected_field_values_in_non_feed_job(bool(selected_feeds), bool(is_all_feeds))
                formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
                if formatted_error:
                    self._errors.append(error_message)
                    return False

        return True

    def is_name_not_empty(self):
        name = self.current_file.get('name')
        if (not name) or (name.isspace()):
            error_message, error_code = Errors.empty_or_missing_job_name()
            formatted_error = self.handle_error(error_message, error_code, file_path=self.file_path)
            if formatted_error:
                self._errors.append(error_message)
                return False
        return True

    def is_valid_file(self, validate_rn=True):
        return all((
            self.is_valid_feed_fields(),
            self.is_name_not_empty(),
            self._is_id_equals_name(JOB),
            super().is_valid_file(validate_rn),  # includes is_fromversion_valid()
        ))
