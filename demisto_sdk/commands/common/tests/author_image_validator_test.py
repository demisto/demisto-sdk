import os

import pytest

from demisto_sdk.commands.common.hook_validations.author_image import \
    AuthorImageValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path


class TestAuthorImageValidator:
    AUTHOR_IMAGE_FILES_PATH = os.path.normpath(os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files',
                                                            'AuthorImageValidator'))
    VALID_AUTHOR_IMAGE = os.path.join(AUTHOR_IMAGE_FILES_PATH, 'valid_author_image.png')
    EMPTY_AUTHOR_IMAGE = os.path.join(AUTHOR_IMAGE_FILES_PATH, 'empty_author_image.png')

    IS_VALID_INPUTS = [('path_does_not_exist', 'xsoar', AuthorImageValidator.IMAGE_MAX_SIZE, True),
                       ('path_does_not_exist', 'partner', AuthorImageValidator.IMAGE_MAX_SIZE, False),
                       (VALID_AUTHOR_IMAGE, 'xsoar', AuthorImageValidator.IMAGE_MAX_SIZE, True),
                       (EMPTY_AUTHOR_IMAGE, 'xsoar', AuthorImageValidator.IMAGE_MAX_SIZE, False),
                       (VALID_AUTHOR_IMAGE, 'partner', AuthorImageValidator.IMAGE_MAX_SIZE, True),
                       (EMPTY_AUTHOR_IMAGE, 'partner', AuthorImageValidator.IMAGE_MAX_SIZE, False),
                       (VALID_AUTHOR_IMAGE, 'xsoar', 100, False),
                       (VALID_AUTHOR_IMAGE, 'partner', 100, False),
                       ]

    @pytest.mark.parametrize('author_image_path, support_level, max_image_size, expected', IS_VALID_INPUTS)
    def test_is_valid(self, mocker, author_image_path: str, support_level: str, max_image_size: int, expected: bool):
        """
        Given:
        - 'author_image_path': path to where author image should be found.

        When:
        - Performing validations of author image if needed.
        Case a: XSOAR pack, image does not exist.
        Case b: Partner pack, image does not exist.
        Case c: XSOAR pack, valid image exists.
        Case d: XSOAR pack, empty image exists.
        Case e: Partner pack, valid image exists.
        Case f: Partner pack, empty image exists.
        Case g: XSOAR pack, image exists and is bigger than maximum size.
        Case h: Partner pack, image exists and is bigger than maximum size.

        Then:
        - Ensure expected validation status is made.
        Case a: Ensure true is returned.
        Case b: Ensure false is returned.
        Case c: Ensure true is returned.
        Case d: Ensure false is returned.
        Case e: Ensure true is returned.
        Case f: Ensure false is returned.
        Case g: Ensure false is returned.
        Case h: Ensure false is returned.

        """
        author_image_validator: AuthorImageValidator = AuthorImageValidator('', '', maximum_image_size=max_image_size)
        mocker.patch.object(author_image_validator, 'handle_error')
        author_image_validator.file_path = author_image_path
        author_image_validator.support_level = support_level
        assert author_image_validator.is_valid() == expected
