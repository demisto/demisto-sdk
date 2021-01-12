import base64
import os
from pathlib import Path
from typing import Union

from demisto_sdk.commands.common.constants import (DEFAULT_DBOT_IMAGE_BASE64,
                                                   DEFAULT_IMAGE_BASE64)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_yaml

IMAGE_MAX_SIZE = 10 * 1024  # 10kB


class Image:
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        if str(path).endswith('.yml'):
            self.integration_path = path
            integration = get_yaml(str(path))
            is_unified_integration = integration.get('script', {}).get('script', '') not in {'-', ''}
            if is_unified_integration:
                self.path = path
                self.unified = True

            else:
                if os.path.exists(str(path).replace('.yml', '_image.png')):
                    self.path = Path(str(path).replace('.yml', '_image.png'))

                else:
                    self.path = Path(str(path).replace('.yml', '.png'))
                self.unified = False

        else:
            self.integration_path = Path(str(path).replace('_image', '').replace('.png', '.yml'))
            self.path = path
            self.unified = False

        self.base = base if base else BaseValidator()

    def validate(self):
        return self.is_valid_image()

    def is_valid_image(self):
        """Validate that the image exists and that it is in the permitted size limits."""
        is_valid = self.is_existing_image()
        if not is_valid:
            return False

        return all([
            self.is_not_oversize_image(),
            self.is_not_default_image()
        ])

    def is_not_oversize_image(self):
        """Check if the image if over sized, bigger than IMAGE_MAX_SIZE"""
        if not self.unified:
            if os.path.getsize(self.path) > IMAGE_MAX_SIZE:  # disable-secrets-detection
                error_message, error_code = Errors.image_too_large()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        else:
            integration = get_yaml(str(self.integration_path))
            image = integration.get('image', '')

            if ((len(image) - 22) / 4.0) * 3 > IMAGE_MAX_SIZE:  # disable-secrets-detection
                error_message, error_code = Errors.image_too_large()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False
        return True

    def is_existing_image(self):
        """Check if the integration has an image."""
        is_image_in_yml = False
        is_image_in_package = False

        # if this is an image - check that is exists
        if str(self.path).endswith('.png'):
            if not os.path.exists(str(self.path)):
                error_message, error_code = Errors.no_image_given()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        integration = get_yaml(str(self.integration_path))
        image_path = Path(str(self.path).replace('.yml', '_image.png'))

        if integration.get('image'):
            is_image_in_yml = True

        if not self.unified:
            if os.path.exists(str(image_path)):
                is_image_in_package = True

        if is_image_in_package and is_image_in_yml:
            error_message, error_code = Errors.image_in_package_and_yml()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        if not (is_image_in_package or is_image_in_yml):
            error_message, error_code = Errors.no_image_given()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def load_image_from_yml(self):
        integration = get_yaml(str(self.integration_path))

        image = integration.get('image', '')

        if not image:
            error_message, error_code = Errors.no_image_field_in_yml()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return None, False

        image_data = image.split('base64,')
        if image_data and len(image_data) == 2:
            return image_data[1], True

        else:
            error_message, error_code = Errors.image_field_not_in_base64()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return None, False

    def load_image(self):
        valid = True
        if not self.unified:
            with open(str(self.path), "rb") as image:
                image_data = image.read()
                image = base64.b64encode(image_data)  # type: ignore
                if isinstance(image, bytes):
                    image = image.decode("utf-8")

        else:
            image, valid = self.load_image_from_yml()

        return image, valid

    def is_not_default_image(self):
        """Check if the image is the default one"""
        image, valid = self.load_image()

        if not valid:
            return False

        if image in [DEFAULT_IMAGE_BASE64, DEFAULT_DBOT_IMAGE_BASE64]:  # disable-secrets-detection
            error_message, error_code = Errors.default_image_error()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True
