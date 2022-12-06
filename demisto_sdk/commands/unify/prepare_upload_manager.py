from pathlib import Path
from typing import Optional

import demisto_sdk.commands.content_graph.parsers.content_item as content_item
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

# This is to force unifying deprecated content items
content_item.MARKETPLACE_MIN_VERSION = '0.0.0'


class PrepareUploadManager:

    @staticmethod
    def prepare_for_upload(
            input: Path,
            output: Optional[Path] = None,
            marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
            force: bool = False,
            **kwargs) -> Path:
        # This is to be able to unify deprecated content as well

        if isinstance(input, str):
            input = Path(input)
        if not input.is_dir():
            input = input.parent
        if force:
            kwargs['force'] = True
        content_item = BaseContent.from_path(input)
        if not isinstance(content_item, ContentItem):
            raise ValueError(f"Unsupported input for {input}. Please provide a path to a content item. Got: {content_item}")
        if not output:
            output = input / content_item.normalize_file_name
        else:
            output = Path(output) / content_item.normalize_file_name
        data = content_item.prepare_for_upload(marketplace, **kwargs)
        if output.exists() and not force:
            raise FileExistsError(f"Output file {output} already exists. Use --force to overwrite.")
        with output.open('w') as f:
            content_item.handler.dump(data, f)
        return output
