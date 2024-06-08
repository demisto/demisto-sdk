
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.common.constants import (
    FILE_TYPE_BY_RN_HEADER,
    CUSTOM_CONTENT_FILE_ENDINGS,
    ENTITY_TYPE_TO_DIR,
)
from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_display_name,
)
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Pack


class RealseNoteInvalidContentNameHeaderValidator(BaseValidator[ContentTypes]):
    error_code = "RN114"
    description = ("Validate the 2nd headers (the content items) are exists in the pack and having the right display"
                   " name.")
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]
    related_file_type = [RelatedFileType.RELEASE_NOTES]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_headers:= self.valid_header_name(content_item)

            )
        ]

    def valid_header_name(self, content_item) -> str:
        # need to get the pack name, and all the modified dirs
        # need go get the headers name
        # if need to check if all modified items has header with the exact name:
        #   ok
        # else:
        # check if it is {New:} {header name}-
        #   ok if it is a content item as well
        # if it's new pack - no rl needed

        release_note_content = content_item.release_note.file_content
        content_type_dir_name = ENTITY_TYPE_TO_DIR.get(self.get_content_types())
        content_type_dir_list = get_files_in_dir(
            content_item.path,
            CUSTOM_CONTENT_FILE_ENDINGS,
            recursive=True,
            ignore_test_files=True,
        )
        content_items_display_names = set(
            filter(
                lambda x: isinstance(x, str),
                (get_display_name(item) for item in content_type_dir_list),
            )
        )

        for header in set(content_item).difference(content_items_display_names):
            print(f"ok {header}")

'''

   is_valid = True
        entity_type = FILE_TYPE_BY_RN_HEADER.get(content_type, "")

        content_type_dir_name = ENTITY_TYPE_TO_DIR.get(entity_type, entity_type)
        content_type_path = os.path.join(self.pack_path, content_type_dir_name)
        content_type_dir_list = get_files_in_dir(
            content_type_path,
            CUSTOM_CONTENT_FILE_ENDINGS,
            recursive=True,
            ignore_test_files=True,
        )
        if not content_type_dir_list:
            (
                error_message,
                error_code,
            ) = Errors.release_notes_invalid_content_type_header(
                content_type=content_type, pack_name=self.pack_name
            )
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                is_valid = False

        content_items_display_names = set(
            filter(
                lambda x: isinstance(x, str),
                (get_display_name(item) for item in content_type_dir_list),
            )
        )

        for header in set(content_items).difference(content_items_display_names):
            (
                error_message,
                error_code,
            ) = Errors.release_notes_invalid_content_name_header(
                content_name_header=header,
                pack_name=self.pack_name,
                content_type=entity_type,
            )
            if self.handle_error(
                error_message, error_code, self.release_notes_file_path
            ):
                is_valid = False
        return is_valid

'''



    

    
