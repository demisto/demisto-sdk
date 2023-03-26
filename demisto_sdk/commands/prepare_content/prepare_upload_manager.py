import shutil
from pathlib import Path
from typing import Optional, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.pack import Pack


class PrepareUploadManager:
    @staticmethod
    def prepare_for_upload(
        in_path: Path,
        out_path: Optional[Path] = None,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        force: bool = False,
        graph: bool = False,
        skip_update: bool = False,
        **kwargs,
    ) -> Path:
        if isinstance(in_path, str):
            in_path = Path(in_path)
        if isinstance(out_path, str):
            out_path = Path(out_path)

        if force:
            kwargs["force"] = True
        content_item = BaseContent.from_path(in_path)
        if not isinstance(content_item, (ContentItem, Pack)):
            raise ValueError(
                f"Unsupported input for {in_path}. Please provide a path to a content item or a pack."
            )

        if graph:
            # enrich the content item with the graph
            with Neo4jContentGraphInterface(should_update=not skip_update) as interface:
                content_item = interface.from_path(
                    path=content_item.path,
                    marketplace=marketplace,
                )
        content_item: Union[Pack, ContentItem]  # (for mypy)
        if not out_path:
            if not in_path.is_dir():
                in_path = in_path.parent
            out_path = in_path / content_item.normalize_name
        elif out_path.is_dir():
            out_path = out_path / content_item.normalize_name
        out_path: Path  # Output is not optional anymore (for mypy)
        if isinstance(content_item, Pack):
            Pack.dump(content_item, out_path, marketplace)
            shutil.make_archive(str(out_path), "zip", out_path)
            shutil.rmtree(out_path)
            return out_path.with_suffix(".zip")
        if not isinstance(content_item, ContentItem):
            raise ValueError(
                f"Unsupported input for {in_path}. Please provide a path to a content item. Got: {content_item}"
            )
        data = content_item.prepare_for_upload(marketplace, **kwargs)
        if out_path.exists() and not force:
            raise FileExistsError(
                f"Output file {out_path} already exists. Use --force to overwrite."
            )
        with out_path.open("w") as f:
            content_item.handler.dump(data, f)

        return out_path
