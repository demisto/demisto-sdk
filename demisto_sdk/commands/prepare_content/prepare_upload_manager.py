import shutil
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
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
        **kwargs,
    ) -> Path:
        if isinstance(input, str):
            input = Path(input)
        if isinstance(output, str):
            output = Path(output)

        if force:
            kwargs["force"] = True
        content_item = BaseContent.from_path(input)
        if not content_item:
            raise ValueError(
                f"Unsupported input for {input}. Please provide a path to a content item or a pack."
            )
        if not output:
            if not input.is_dir():
                input = input.parent
            output = input / content_item.normalize_name
        else:
            if output.is_dir():
                output = output / content_item.normalize_name

        if isinstance(content_item, Pack):
            Pack.dump(content_item, output, marketplace)
            shutil.make_archive(str(output), "zip", output)
            shutil.rmtree(output)
            return output.with_suffix(".zip")
        if not isinstance(content_item, ContentItem):
            raise ValueError(
                f"Unsupported input for {input}. Please provide a path to a content item. Got: {content_item}"
            )
        data = content_item.prepare_for_upload(marketplace, **kwargs)
        if output.exists() and not force:
            raise FileExistsError(
                f"Output file {output} already exists. Use --force to overwrite."
            )
        with output.open("w") as f:
            content_item.handler.dump(data, f)

        return output
