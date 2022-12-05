from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class PrepareUploadManager:

    @staticmethod
    def prepare_for_upload(
            input: Path,
            output: Optional[Path] = None,
            marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
            force: bool = False,
            **kwargs) -> Path:
        if isinstance(input, str):
            input = Path(input)
        if not input.is_dir():
            input = input.parent
        if force:
            kwargs['force'] = True
        content_item = BaseContent.from_path(input)
        if not isinstance(content_item, ContentItem):
            raise ValueError(f"Unsupported input. Please provide a path to a content item. Got: {content_item}")
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
