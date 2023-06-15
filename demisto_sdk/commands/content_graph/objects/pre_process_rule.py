from typing import Set

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class PreProcessRule(BaseContent, content_type=ContentType.PREPROCESS_RULE):
    def metadata_fields(self) -> Set[str]:
        raise NotImplementedError("PreprocessRule not included in metadata")
