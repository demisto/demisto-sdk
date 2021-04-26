import base64
import glob

from demisto_sdk.commands.common.constants import (
    DEFAULT_DBOT_IMAGE_BASE64, DEFAULT_IMAGE_BASE64, IMAGE_REGEX,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_yaml, os, re


class ImageValidator(BaseValidator):
    """ImageValidator was designed to make sure we use images within the permitted limits.

    Attributes:
        file_path (string): Path to the checked file.
        _is_valid (bool): the attribute which saves the valid/in-valid status of the current file.
    """
    IMAGE_MAX_SIZE = 10 * 1024  # 10kB

    def __init__(self, file_path, ignored_errors=None, print_as_warnings=False, suppress_print=False,
                 json_file_path=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self._is_valid = True
        self.file_path = ''
        if file_path.endswith('.png'):
            self.file_path = file_path
        # For integrations that are not in a package format, the image is within the yml
        else:
            data_dictionary = get_yaml(file_path)
            if not data_dictionary:
                return
            # For old integration in which image is inside the yml.
            elif data_dictionary.get('image', ''):
                self.file_path = file_path
            # For new integrations -  Get the image from the folder.
            else:
                try:
                    self.file_path = glob.glob(os.path.join(os.path.dirname(file_path), '*.png'))[0]
                except IndexError:
                    error_message, error_code = Errors.no_image_given()
                    self.file_path = file_path.replace('.yml', '_image.png')
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        self._is_valid = False

    def is_valid(self):
        """Validate that the image exists and that it is in the permitted size limits."""
        if self._is_valid is False:  # In case we encountered an IndexError in the init - we don't have an image
            return self._is_valid

        is_existing_image = False
        self.oversize_image()
        if '.png' not in self.file_path:
            is_existing_image = self.is_existing_image()
        if is_existing_image or '.png' in self.file_path:
            self.is_not_default_image()

        return self._is_valid

    def oversize_image(self):
        """Check if the image if over sized, bigger than IMAGE_MAX_SIZE"""
        if re.match(IMAGE_REGEX, self.file_path, re.IGNORECASE):
            if os.path.getsize(self.file_path) > self.IMAGE_MAX_SIZE:  # disable-secrets-detection
                error_message, error_code = Errors.image_too_large()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False

        else:
            data_dictionary = get_yaml(self.file_path)

            if not data_dictionary:
                return

            image = data_dictionary.get('image', '')

            if ((len(image) - 22) / 4.0) * 3 > self.IMAGE_MAX_SIZE:  # disable-secrets-detection
                error_message, error_code = Errors.image_too_large()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False

    def is_existing_image(self):
        """Check if the integration has an image."""
        is_image_in_yml = False
        is_image_in_package = False

        data_dictionary = get_yaml(self.file_path)

        if not data_dictionary:
            return False

        if data_dictionary.get('image'):
            is_image_in_yml = True
        if not re.match(PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, self.file_path, re.IGNORECASE):
            package_path = os.path.dirname(self.file_path)
            image_path = glob.glob(package_path + '/*.png')
            if image_path:
                is_image_in_package = True
        if is_image_in_package and is_image_in_yml:
            error_message, error_code = Errors.image_in_package_and_yml()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        if not (is_image_in_package or is_image_in_yml):
            error_message, error_code = Errors.no_image_given()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True

    def load_image_from_yml(self):
        data_dictionary = get_yaml(self.file_path)

        if not data_dictionary:
            error_message, error_code = Errors.not_an_image_file()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False

        image = data_dictionary.get('image', '')

        if not image:
            error_message, error_code = Errors.no_image_field_in_yml()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False

        image_data = image.split('base64,')
        if image_data and len(image_data) == 2:
            return image_data[1]

        else:
            error_message, error_code = Errors.image_field_not_in_base64()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False

    def load_image(self):
        if re.match(IMAGE_REGEX, self.file_path, re.IGNORECASE):
            with open(self.file_path, "rb") as image:
                image_data = image.read()
                image = base64.b64encode(image_data)  # type: ignore
                if isinstance(image, bytes):
                    image = image.decode("utf-8")

        else:
            image = self.load_image_from_yml()

        return image

    def is_not_default_image(self):
        """Check if the image is the default one"""
        image = self.load_image()

        if image in [DEFAULT_IMAGE_BASE64, DEFAULT_DBOT_IMAGE_BASE64]:  # disable-secrets-detection
            error_message, error_code = Errors.default_image_error()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True
