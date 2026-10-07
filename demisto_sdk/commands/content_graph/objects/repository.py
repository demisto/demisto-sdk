import shutil
import time
from functools import lru_cache
from multiprocessing.pool import Pool
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tqdm
from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    PackDestination,
)
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.repository import RepositoryParser

json = JSON_Handler()

USE_MULTIPROCESSING = False  # toggle this for better debugging


@lru_cache
def from_path(
    path: Path = CONTENT_PATH,
    packs_to_parse: Optional[Tuple[str]] = None,
    connectors_to_parse: Optional[Tuple[str, ...]] = None,
):
    """
    Returns a ContentDTO object with all the packs and connectors of the content repository.

    This function is outside of the class for better caching.
    The class function uses this function so the behavior is the same.

    Narrowing matrix (must stay symmetric for packs and connectors):
        - no packs filter, no connectors filter  -> parse ALL packs + ALL connectors
        - packs filter,    no connectors filter  -> parse those packs, no connectors
        - no packs filter, connectors filter     -> parse no packs, those connectors
        - both filters                           -> parse those packs + those connectors

    Args:
        path: Repository root.
        packs_to_parse: Optional subset of pack names. When omitted *and*
            ``connectors_to_parse`` is also omitted, all packs are parsed.
            When ``connectors_to_parse`` is provided but ``packs_to_parse`` is
            not, no packs are parsed.
        connectors_to_parse: Optional subset of connector directory names. When
            omitted *and* ``packs_to_parse`` is also omitted, all connectors
            under ``connectors/`` are parsed. When ``packs_to_parse`` is
            provided but ``connectors_to_parse`` is not, no connectors are
            parsed (callers that want a partial update of both must pass both
            explicitly, mirroring the pack-narrowing semantics).
    """
    repo_parser = RepositoryParser(path)
    if packs_to_parse:
        packs = tuple(repo_parser.iter_packs(packs_to_parse))
    elif connectors_to_parse is not None:
        # connectors-only narrowing: do not parse any packs
        packs = ()
    else:
        # full scan only when both filters are unset
        packs = tuple(repo_parser.iter_packs(None))

    if connectors_to_parse is not None:
        connectors = tuple(repo_parser.iter_connectors(connectors_to_parse))
    elif not packs_to_parse:
        connectors = tuple(repo_parser.iter_connectors())
    else:
        connectors = ()
    with tqdm.tqdm(
        total=len(packs) + len(connectors),
        unit="items",
        desc="Parsing packs and connectors",
        position=0,
        leave=True,
    ) as progress_bar:
        repo_parser.parse(
            packs_to_parse=packs,
            progress_bar=progress_bar,
            connectors_to_parse=connectors,
        )
    return ContentDTO.from_orm(repo_parser)


class ContentDTO(BaseModel):
    path: DirectoryPath = Path(CONTENT_PATH)  # type: ignore
    packs: List[Pack]
    connectors: List[Connector] = []

    @staticmethod
    def from_path(
        path: Path = CONTENT_PATH,
        packs_to_parse: Optional[Tuple[str, ...]] = None,
        connectors_to_parse: Optional[Tuple[str, ...]] = None,
    ):
        """
        Returns a ContentDTO object with all the packs and connectors of the content repository.
        """
        return from_path(path, packs_to_parse, connectors_to_parse)

    def dump(
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
        zip: bool = True,
        packs_to_dump: Optional[list] = None,
        output_stem: str = "content_packs",  # without extension
        destination: Optional[PackDestination] = None,
        **kwargs,
    ):
        """Dump all packs, or only those matching ``destination``; ``kwargs`` (e.g. ``strip_internal``) are forwarded to ``Pack.dump``."""
        dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Got packs to dump: {packs_to_dump}")
        packs_to_dump = (
            [pack for pack in self.packs if pack.object_id in packs_to_dump]
            if packs_to_dump is not None
            else self.packs
        )

        if destination is not None:
            packs_to_dump = [
                pack for pack in packs_to_dump if pack.destination == destination
            ]

        if not packs_to_dump:
            logger.debug("didn't got packs to dump, skipping")
            return

        logger.debug(
            f"Starting repository dump for packs: {[pack.object_id for pack in packs_to_dump]}"
        )
        start_time = time.time()
        if USE_MULTIPROCESSING:
            # Pool.starmap can't forward **kwargs, so we rebuild the args
            # tuple including only positional arguments. ``Pack.dump`` accepts
            # ``**kwargs`` (e.g. ``strip_internal``, ``tpb``), so we pass them
            # via ``functools.partial`` instead.
            from functools import partial

            dump_fn = partial(Pack.dump, **kwargs)
            with Pool(processes=cpu_count()) as pool:
                pool.starmap(
                    dump_fn,
                    (
                        (pack, self._artifact_path(dir, pack), marketplace)
                        for pack in packs_to_dump
                    ),
                )

        else:
            for pack in packs_to_dump:
                pack.dump(
                    self._artifact_path(dir, pack),
                    marketplace,
                    **kwargs,
                )

        time_taken = time.time() - start_time
        logger.debug(f"Repository dump ended. Took {time_taken} seconds")

        if zip:
            shutil.make_archive(str(dir.parent / output_stem), "zip", dir)
            shutil.rmtree(dir)

    @staticmethod
    def _artifact_path(output_dir: Path, pack: Pack) -> Path:
        """Artifact directory name for a pack: the derived id for a twin, else ``pack.path.name``."""
        if getattr(pack, "is_derived", False):
            return output_dir / pack.object_id
        return output_dir / pack.path.name

    def get_pack_destination_mapping(self) -> Dict[str, PackDestination]:
        """Returns ``{pack_id: destination}`` for all packs."""
        return {pack.object_id: pack.destination for pack in self.packs}

    def get_derived_pack_mapping(self) -> Dict[str, str]:
        """Returns ``{derived_pack_id: original_pack_id}`` for derived packs."""
        return {
            pack.object_id: pack.derived_from
            for pack in self.packs
            if getattr(pack, "is_derived", False) and pack.derived_from
        }

    def write_pack_destinations(
        self,
        output_path: Path,
        artifacts_dir: Optional[Path] = None,
        managed_artifacts_dir: Optional[Path] = None,
    ) -> None:
        """Write ``pack_destinations.json``: destination, ``current_version`` (empty -> None) and ``artifact_path`` rooted at the pack's dump dir."""
        entries: List[Dict[str, Any]] = []
        no_managed_artifacts = (
            artifacts_dir is not None and managed_artifacts_dir is None
        )
        for pack in self.packs:
            # Surfaced from the graph, with an empty value normalized to ``None``.
            graph_current_version = getattr(pack, "current_version", None)
            current_version: Optional[str] = (
                graph_current_version
                if isinstance(graph_current_version, str) and graph_current_version
                else None
            )
            entry: Dict[str, Any] = {
                "pack_id": pack.object_id,
                "pack_name": pack.name,
                "current_version": current_version,
                "destination": pack.destination.value.upper(),
                "source_path": str(pack.path),
                "is_derived": getattr(pack, "is_derived", False),
                "parent_pack_id": getattr(pack, "derived_from", None),
                "managed": pack.managed or False,
                "source": pack.source or "",
            }
            # Managed packs go to ``managed_artifacts_dir``, regular ones to ``artifacts_dir``; legacy calls fall back to the JSON's dir.
            base_dir: Optional[Path]
            if artifacts_dir is None:
                base_dir = output_path.parent
            elif pack.managed:
                base_dir = (
                    None
                    if managed_artifacts_dir is None
                    else managed_artifacts_dir.absolute()
                )
            else:
                base_dir = artifacts_dir.absolute()
            # Reuse ``dump()``'s helper so the recorded segment cannot drift from the real one.
            entry["artifact_path"] = (
                "" if base_dir is None else str(self._artifact_path(base_dir, pack))
            )
            if getattr(pack, "is_derived", False):
                entry["content_items"] = [
                    f"{ci.content_type.value}-{ci.object_id}"
                    for ci in pack.content_items
                    if pack._is_item_tightly_coupled(ci)
                ]
            entries.append(entry)

        if no_managed_artifacts:
            managed_count = sum(1 for pack in self.packs if pack.managed)
            if managed_count:
                logger.info(
                    f"No managed_artifacts_dir supplied: {managed_count} managed packs written with an empty artifact_path"
                )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(json.dumps({"packs": entries}, indent=2))
        logger.info(
            f"Wrote pack_destinations.json with {len(entries)} entries to {output_path}"
        )

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
