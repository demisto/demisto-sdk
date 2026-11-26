import zipfile
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import DirectoryPath

from demisto_sdk.commands.common.constants import (
    AGENTIX_FLOW_CODE_DIR,
    AGENTIX_FLOW_JSON_SUFFIX,
    AGENTIX_FLOW_LANGGRAPH_VERSION_KEY,
    AGENTIX_FLOW_ZIP_EXCLUDE_DIRS,
    AGENTIX_FLOW_ZIP_EXCLUDE_FILE_GLOBS,
    AGENTIX_FLOW_ZIP_INCLUDE_GLOBS,
    AGENTIX_FLOW_ZIP_PATH_KEY,
    AGENTIX_FLOWS_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import write_dict
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_base import AgentixBase
from demisto_sdk.commands.content_graph.strict_objects.agentix_flow import (
    StrictAgentixFlow,
)

json = JSON_Handler()

# Fixed zip entry metadata, so the same sources always give the same bytes.
_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)
_ZIP_FILE_MODE = 0o644 << 16
_ZIP_COMPRESSION = zipfile.ZIP_DEFLATED

# Every flow YAML schema key; an author can't set these through ``_flow.json``.
_SCHEMA_KEYS = frozenset(f.alias for f in StrictAgentixFlow.__fields__.values())


def build_flow_json(
    content: Dict[str, Any],
    author_fields: Dict[str, Any],
    zip_path: str,
    source: str = "",
) -> Dict[str, Any]:
    """Merge the shipped flow JSON: content, then author keys, then ``zip_path``.

    Reserved keys (flow YAML schema keys, keys in ``content`` and ``zip_path``)
    win over same-named author keys, with a warning; any other author key
    (e.g. ``langgraph_version``) is kept unchanged, in its original order.

    Today ``author_fields`` comes from ``<FlowName>_flow.json``. If the JSON
    becomes fully build-generated, callers pass the build-time values instead.
    """
    reserved = _SCHEMA_KEYS | set(content) | {AGENTIX_FLOW_ZIP_PATH_KEY}
    if overridden := [k for k in author_fields if k in reserved]:
        logger.warning(
            f"AgentixFlow {source}: ignoring author-set "
            f"{', '.join(repr(k) for k in overridden)}; these keys are generated "
            "from the flow YAML at build time"
        )
    return {
        **content,
        **{k: v for k, v in author_fields.items() if k not in reserved},
        AGENTIX_FLOW_ZIP_PATH_KEY: zip_path,
    }


class AgentixFlow(AgentixBase, content_type=ContentType.AGENTIX_FLOW):
    """Represents an AgentixFlow content item.

    The item folder ``Packs/<PackName>/AgentixFlows/<FlowName>/`` holds:
    - ``<FlowName>.yml``: the content item (top-level ``id`` and ``version``,
      no ``commonfields``). This is the only file parsed into the graph.
    - ``<FlowName>_flow.json``: flow-engine metadata (``langgraph_version``).
    - ``src/**``: the LangGraph code.

    ``dump`` writes the YAML plus ``agentixflow-<FlowName>.json`` (the shipped
    YAML, any missing ``fromversion`` / ``toversion`` / ``supportedModules``,
    the author keys and ``zip_path``) and ``agentixflow-<FlowName>.zip``
    (the code).
    """

    supportedModules: Optional[list[str]] = None

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Match an AgentixFlow ``<FlowName>.yml`` file under ``AgentixFlows/``."""
        if (
            path.suffix in {".yml", ".yaml"}
            and not path.stem.endswith("_test")
            and AGENTIX_FLOWS_DIR in path.parts
        ):
            return True
        return False

    @property
    def flow_dir(self) -> Path:
        return (self.path_to_read or self.path).parent

    @property
    def flow_json_path(self) -> Path:
        return self.flow_dir / f"{self.flow_dir.name}{AGENTIX_FLOW_JSON_SUFFIX}"

    @property
    def flow_zip_name(self) -> str:
        """The shipped zip file name, also used as the JSON ``zip_path`` value
        (relative to the JSON's own folder). Keep this the single source."""
        return f"{Path(self.normalize_name).stem}.zip"

    def dump(  # type: ignore[override]
        self,
        dir: DirectoryPath,
        marketplace: MarketplaceVersions,
        **kwargs,
    ) -> None:
        """Dump the flow YAML, its companion JSON and the zipped ``src/`` code.

        The YAML data is prepared once and is both the shipped YAML and the
        start of the JSON, so the two never disagree. The JSON then gets
        ``fromversion``, ``toversion`` and ``supportedModules`` when missing,
        the author keys from ``<FlowName>_flow.json`` and ``zip_path``.

        Raises:
            ValueError: if the companion JSON is missing/invalid, has no
                non-empty ``langgraph_version``, or ``src/`` has no code files.
        """
        if not self.path.exists():
            logger.warning(f"Could not find file {self.path}, skipping dump")
            return
        # Validate the companion files before writing anything.
        author_fields = self._read_flow_json()
        code_files = self._collect_code_files()

        # Prepare once and write the result twice (the YAML, and the start of
        # the JSON), as BaseScript.dump / ContentItemXSIAM.dump do; the base
        # ContentItem.dump makes this same call internally.
        prepared = self.prepare_for_upload(current_marketplace=marketplace, **kwargs)
        dir.mkdir(exist_ok=True, parents=True)
        write_dict(dir / self.normalize_name, data=prepared, handler=self.handler)

        # Add the values the shipped YAML may leave out, in this order:
        # - fromversion / toversion: the flow engine requires them, so the
        #   model's values (parser defaults if unset) are added.
        # - supportedModules: append_supported_modules strips it when it covers
        #   the pack's list. Read from the model (item, else pack), because
        #   prepare_for_upload mutated self.data in place.
        content = dict(prepared)
        modules = self.supportedModules or (
            self.in_pack.supportedModules if self.in_pack else None
        )
        for key, value in (
            ("fromversion", self.fromversion),
            ("toversion", self.toversion),
            ("supportedModules", modules),
        ):
            if value and key not in content:
                content[key] = value

        zip_name = self.flow_zip_name
        write_dict(
            dir / f"{Path(self.normalize_name).stem}.json",
            data=build_flow_json(
                content, author_fields, zip_name, source=str(self.flow_json_path)
            ),
            handler=json,
            indent=4,
        )
        self._write_zip(code_files, dir / zip_name)

    def _read_flow_json(self) -> dict:
        path = self.flow_json_path
        if not path.is_file():
            raise ValueError(f"AgentixFlow companion JSON not found: {path}")
        try:
            data = json.loads(path.read_text())
        except ValueError as e:
            raise ValueError(f"AgentixFlow {path} is invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"AgentixFlow {path} must contain a JSON object")
        version = data.get(AGENTIX_FLOW_LANGGRAPH_VERSION_KEY)
        if not isinstance(version, str) or not version.strip():
            raise ValueError(
                f"AgentixFlow {path} must set a non-empty string "
                f"'{AGENTIX_FLOW_LANGGRAPH_VERSION_KEY}'"
            )
        return data

    def _collect_code_files(self) -> List[Path]:
        """The files under ``src/`` to zip, sorted by their POSIX arcname."""
        code_dir = self.flow_dir / AGENTIX_FLOW_CODE_DIR
        files = set()
        for pattern in AGENTIX_FLOW_ZIP_INCLUDE_GLOBS:
            for file in code_dir.rglob(pattern):
                rel = file.relative_to(code_dir)
                if (
                    file.is_file()
                    and not any(
                        part in AGENTIX_FLOW_ZIP_EXCLUDE_DIRS or part.startswith(".")
                        for part in rel.parts[:-1]
                    )
                    and not any(
                        fnmatch(file.name, glob)
                        for glob in AGENTIX_FLOW_ZIP_EXCLUDE_FILE_GLOBS
                    )
                ):
                    files.add(file)
        if not files:
            raise ValueError(
                f"AgentixFlow {self.flow_dir} has no code files in "
                f"'{AGENTIX_FLOW_CODE_DIR}/' matching {AGENTIX_FLOW_ZIP_INCLUDE_GLOBS}"
            )
        return sorted(files, key=lambda f: f.relative_to(self.flow_dir).as_posix())

    def _write_zip(self, files: List[Path], zip_path: Path) -> None:
        """Write a deterministic zip; arcnames keep the ``src/`` prefix."""
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in files:
                info = zipfile.ZipInfo(
                    file.relative_to(self.flow_dir).as_posix(),
                    date_time=_ZIP_DATE_TIME,
                )
                info.external_attr = _ZIP_FILE_MODE
                info.compress_type = _ZIP_COMPRESSION
                zf.writestr(info, file.read_bytes())
        logger.debug(f"Wrote AgentixFlow code zip {zip_path} ({len(files)} files)")
