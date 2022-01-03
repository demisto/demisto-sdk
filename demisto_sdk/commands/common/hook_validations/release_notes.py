from __future__ import print_function

import itertools
import os
import re

from demisto_sdk.commands.common.constants import (
    PACKS_DIR, RN_HEADER_BY_FILE_TYPE, SKIP_RELEASE_NOTES_FOR_TYPES)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (find_type,
                                               get_latest_release_notes_text,
                                               get_pack_name,
                                               get_release_notes_file_path,
                                               get_ryaml)
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class ReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        release_notes_file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
    """

    def __init__(self, release_notes_file_path, modified_files=None, pack_name=None, added_files=None, ignored_errors=None,
                 print_as_warnings=False, suppress_print=False, json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.release_notes_file_path = release_notes_file_path
        self.modified_files = modified_files
        self.added_files = added_files
        self.pack_name = pack_name
        self.pack_path = os.path.join(PACKS_DIR, self.pack_name)
        self.release_notes_path = get_release_notes_file_path(self.release_notes_file_path)
        self.latest_release_notes = get_latest_release_notes_text(self.release_notes_path)

    def are_release_notes_complete(self):
        is_valid = True
        modified_added_files = itertools.chain.from_iterable((self.added_files or [], self.modified_files or []))
        if modified_added_files:
            for file in modified_added_files:
                # renamed files will appear in the modified list as a tuple: (old path, new path)
                if isinstance(file, tuple):
                    file = file[1]
                checked_file_pack_name = get_pack_name(file)

                if find_type(file) in SKIP_RELEASE_NOTES_FOR_TYPES:
                    continue
                elif checked_file_pack_name and checked_file_pack_name == self.pack_name:
                    # Refer image and description file paths to the corresponding yml files
                    file = UpdateRN.change_image_or_desc_file_path(file)
                    update_rn_util = UpdateRN(pack_path=self.pack_path, modified_files_in_pack=set(),
                                              update_type=None, added_files=set(), pack=self.pack_name)
                    file_name, file_type = update_rn_util.get_changed_file_name_and_type(file)
                    if file_name and file_type:
                        if (RN_HEADER_BY_FILE_TYPE[file_type] not in self.latest_release_notes) or \
                                (file_name not in self.latest_release_notes):
                            entity_name = update_rn_util.get_display_name(file)
                            error_message, error_code = Errors.missing_release_notes_entry(file_type, self.pack_name,
                                                                                           entity_name)
                            if self.handle_error(error_message, error_code, self.release_notes_file_path):
                                is_valid = False
        return is_valid

    def has_release_notes_been_filled_out(self):
        release_notes_comments = self.strip_exclusion_tag(self.latest_release_notes)
        if len(release_notes_comments) == 0:
            error_message, error_code = Errors.release_notes_file_empty()
            if self.handle_error(error_message, error_code, file_path=self.release_notes_file_path):
                return False
        elif '%%UPDATE_RN%%' in release_notes_comments:
            error_message, error_code = Errors.release_notes_not_finished()
            if self.handle_error(error_message, error_code, file_path=self.release_notes_file_path):
                return False
        return True

    def is_docker_image_same_as_yml(self):
        """
        Iterates on all modified yaml files, 
        checking if the yaml is related to one of the sections in the RN and if there's a docker-image version update mentioned in the RN.
        If so, make sure the versions match.

        Return:
            True if for all the modified yaml files, if there was a change in the docker image in the RN, it's the same version as the yaml.
            Otherwise, return False and a release_notes_docker_image_not_match_yaml Error
        """
        splited_release_notes = self.get_categories_from_rn("\n" + self.latest_release_notes)
        # renamed files will appear in the modified list as a tuple: (old path, new path)
        modified_files_list = [file[1] if isinstance(file, tuple) else file for file in (self.modified_files or [])]
        modified_yml_list = [file for file in modified_files_list if file.endswith('.yml')]
        error_list = [self.release_notes_file_path[self.release_notes_file_path.rindex('/')+1:]]
        for key, field in zip(['Integrations', 'Scripts'], ['display', 'name']):
            if(key in splited_release_notes):
                splited_sections_dict = self.get_categories_from_rn(splited_release_notes.get(key), "##### ")
                for modified_yml_file in modified_yml_list:
                    modified_yml_dict = get_ryaml(modified_yml_file)        
                    if modified_yml_dict and modified_yml_dict.get(field) in splited_sections_dict:
                        docker_version = self.get_docker_version_from_rn(splited_sections_dict.get(modified_yml_dict.get(field)) + "\n")
                        if docker_version and modified_yml_dict.get("script").get("dockerimage") != docker_version:
                            error_list.append({'name':modified_yml_dict.get(field),
                                            'rs_version':docker_version,
                                            'yml_version':modified_yml_dict.get("script").get("dockerimage")})
        if len(error_list) > 1:
            error_message, error_code = Errors.release_notes_docker_image_not_match_yaml(error_list)
            if self.handle_error(error_message, error_code, file_path=self.release_notes_file_path):
                return False

        return True    
    
    @staticmethod
    def get_docker_version_from_rn(section):
        """
        Strips the docker image version from the relevant section in the RN if noted.
        Args:
            section : the section to search its docker image version note
        Return:
            str. The docker image version if exists. otherwiser, return None.
        """
        updates_list = section.split("- ")
        for update in updates_list:
            if "Docker image" in update and "demisto/" in update:
                return (re.search('(demisto/.+:([0-9]+)(((\.)[0-9]+)+))', update).group(1)) 
        return None 

    @staticmethod
    def get_categories_from_rn(rn:str, splitter:str="\n#### "):
        """
            Extract the various categories from the release note according to the splitter
            rn : the relese notes
            splitter: a string to split by
        Return:
            dict. dictionary where each entry is the category name in the relese notes
            and its value is the additions for that category.
        """
        splitted_text = (rn).split(splitter) 
        splitted_categories_dict = {}  
        for category in splitted_text:
            if category:
                splitted_categories_dict[category[0:category.index("\n")]] = category[category.index("\n") + 1:] 
        return splitted_categories_dict

    @staticmethod
    def strip_exclusion_tag(release_notes_comments):
        """
        Strips the exclusion tag (<!-- -->) from the release notes since release notes should never
        be empty as this is poor user experience.
        Return:
            str. Cleaned notes with tags and contained notes removed.
        """
        return re.sub(r'<\!--.*?-->', '', release_notes_comments, flags=re.DOTALL)

    def is_file_valid(self):
        """Checks if given file is valid.

        Return:
            bool. True if file's release notes are valid, False otherwise.
        """
        validations = [
            self.has_release_notes_been_filled_out(),
            self.are_release_notes_complete(),
            self.is_docker_image_same_as_yml()
        ]

        return all(validations)
