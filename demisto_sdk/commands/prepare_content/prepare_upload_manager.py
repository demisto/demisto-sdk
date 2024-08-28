import shutil
from pathlib import Path
from typing import Optional, Union

from demisto_sdk.commands.common.constants import (
    DEFAULT_JSON_INDENT,
    DEFAULT_YAML_INDENT,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    write_dict,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack


class PrepareUploadManager:
    @staticmethod
    def prepare_for_upload(
        input: Path,
        output: Optional[Path] = None,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        force: bool = False,
        graph: bool = False,
        skip_update: bool = False,
        **kwargs,
    ) -> Path:
        if isinstance(input, str):
            input = Path(input)
        if isinstance(output, str):
            output = Path(output)
        if not isinstance(marketplace, MarketplaceVersions):
            marketplace = MarketplaceVersions(marketplace)
        if force:
            kwargs["force"] = True
        content_item = BaseContent.from_path(input)
        if not isinstance(content_item, (ContentItem, Pack)):
            raise ValueError(
                f"Unsupported input for {input}. Please provide a path to a content item or a pack."
            )

        if graph:
            # enrich the content item with the graph
            with ContentGraphInterface() as interface:
                if not skip_update:
                    update_content_graph(
                        interface, use_git=True, output_path=interface.output_path
                    )
                content_item = interface.from_path(
                    path=content_item.path,
                    marketplace=marketplace,
                )
        content_item: Union[Pack, ContentItem]  # (for mypy)
        if not output:
            if not input.is_dir():
                input = input.parent
            output = input / content_item.normalize_name
        elif output.is_dir():
            output = output / content_item.normalize_name
        output: Path  # Output is not optional anymore (for mypy)
        if isinstance(content_item, Pack):
            Pack.dump(content_item, output, marketplace)
            shutil.make_archive(str(output), "zip", output)
            shutil.rmtree(output)
            return output.with_suffix(".zip")
        if not isinstance(content_item, ContentItem):
            raise ValueError(
                f"Unsupported input for {input}. Please provide a path to a content item. Got: {content_item}"
            )
        content_item: ContentItem
        data = content_item.prepare_for_upload(marketplace, **kwargs)
        if output.exists() and not force:
            raise FileExistsError(
                f"Output file {output} already exists. Use --force to overwrite."
            )

        write_dict(
            output,
            data=data,
            handler=content_item.handler,
            indent=(
                DEFAULT_JSON_INDENT
                if isinstance(content_item.handler, JSON_Handler)
                else DEFAULT_YAML_INDENT
            ),
        )

        logger.info(f"<green>Output saved in: {str(output.absolute())}</green>")
        return output
