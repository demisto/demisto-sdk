from typing import List, Union
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


def pre_commit():
    # Get all changed integrations and scripts
    changed_file_paths = GitUtil().get_all_changed_integrations_and_scripts('origin/master')
    content_items: List[IntegrationScript] = [BaseContent.from_path(path) for path in changed_file_paths]  # type: ignore[misc]
    for content_item in content_items:
        docker_image = content_item.docker_image
        