from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import extract_docker_image_from_text

json = JSON_Handler()


class NativeImageSupport:

    """
    Class that defines whether a native image should be supported in a docker image or not by the following criterias:

    1) if the docker image that the integration/script uses is one of the base docker images (python3, py3-tools, python3-deb)
    2) if the integration/script is part of the malware/phishing use-cases.
    3) if the integration/script is not ignored in the configuration file.

    Args:
        _id (str): the ID that the script/integration has.
        docker_image (str): the docker image that the integration/script uses.
        native_image_config_file_path (str): a path to the native image configuration file.
        supported_base_docker_images (tuple): a list of the base docker images that should be supported in nativeImage.
    """
    def __init__(self, _id: str, docker_image: str, native_image_config_file_path: str, supported_base_docker_images: tuple | None = None):
        self.id = _id
        self.docker_image = extract_docker_image_from_text(text=docker_image, with_no_tag=False)
        with open(native_image_config_file_path, 'r') as file:
            self.native_image_config = json.load(file)
        if supported_base_docker_images:
            self.supported_base_docker_images = supported_base_docker_images
        else:
            self.supported_base_docker_images = ('python3', 'py3-tools', 'python3-deb')
        
    def is_part_of_docker_images(self):
        return self.docker_image in self.supported_base_docker_images

    def should_be_ignored(self):
        pass

    def is_part_of_phishing_or_malware(self):
        pass

    def __bool__(self):
        return self.is_part_of_docker_images() and not self.should_be_ignored() and self.is_part_of_phishing_or_malware()





