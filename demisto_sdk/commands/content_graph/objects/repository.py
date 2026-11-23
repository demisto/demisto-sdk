import gc
import multiprocessing
import os
import shutil
import sys
import threading
import time
import traceback
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import tqdm
from pydantic import BaseModel, DirectoryPath

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_LOG_FILE_PATH,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import (
    DEFAULT_FILE_THRESHOLD,
    FILE_FORMAT,
    LOGURU_DIAGNOSE,
    calculate_log_dir,
    logger,
)
from demisto_sdk.commands.common.string_to_bool import string_to_bool
from demisto_sdk.commands.content_graph.common import (
    PackDestination,
)
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.pack_metadata import get_version_info
from demisto_sdk.commands.content_graph.parsers.repository import RepositoryParser
from demisto_sdk.commands.prepare_content.markdown_images_handler import (
    MarkdownImagesCollector,
    collect_markdown_images,
    get_active_markdown_images_collector,
)

json = JSON_Handler()

# Fixed zip member metadata, so the zip bytes depend only on file paths and contents.
_ZIP_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
_ZIP_COMPRESS_LEVEL = (
    6  # the zlib default, made explicit so the bytes never depend on a library default
)
_ZIP_CREATE_SYSTEM = 3  # Unix
_ZIP_FILE_EXTERNAL_ATTR = 0o644 << 16
_ZIP_DIR_EXTERNAL_ATTR = (0o755 << 16) | 0x10  # 0x10 is the MS-DOS directory flag


def _fixed_zip_info(arcname: str, external_attr: int) -> zipfile.ZipInfo:
    """A ``ZipInfo`` whose metadata does not depend on the file system (mtime, mode, OS)."""
    zip_info = zipfile.ZipInfo(arcname, date_time=_ZIP_FIXED_DATE_TIME)
    zip_info.create_system = _ZIP_CREATE_SYSTEM
    zip_info.external_attr = external_attr
    return zip_info


def _list_tree_entries(src_dir: Path, top_level_name: str) -> List[Tuple[str, Path]]:
    """Return sorted ``(arcname, path)`` pairs for ``src_dir/top_level_name`` and everything below it.

    Arcnames use POSIX separators and are relative to ``src_dir``; directory arcnames end with "/".
    Directory entries are included, so empty directories survive extraction, as with
    ``shutil.make_archive``. A directory arcname is a prefix of its children's, so it sorts first.
    """
    top_level_path = src_dir / top_level_name
    if not top_level_path.is_dir():
        return [(top_level_name, top_level_path)]
    entries = [(f"{top_level_name}/", top_level_path)]
    for dir_path, dir_names, file_names in os.walk(top_level_path):
        relative_dir = Path(dir_path).relative_to(src_dir).as_posix()
        entries.extend(
            (f"{relative_dir}/{name}/", Path(dir_path, name)) for name in dir_names
        )
        entries.extend(
            (f"{relative_dir}/{name}", Path(dir_path, name)) for name in file_names
        )
    return sorted(entries)


def _top_level_sort_key(top_level_name: str) -> str:
    """Sort pack directories by their arcname (``name/``), so the whole zip is in sorted arcname order."""
    return f"{top_level_name}/"


class OrderedPackZipWriter:
    """Byte-reproducible zip of the top-level entries (one directory per pack) of ``src_dir``.

    ``mark_pack_done`` may be called in any order. Entries are appended strictly in sorted
    top-level arcname order: every call flushes the longest prefix of that order whose entries are
    all done, and keeps the rest pending. Inside an entry, members are sorted by arcname, so all
    members of the zip are in sorted arcname order. Every member has fixed metadata, so the bytes
    depend only on paths and contents.
    """

    def __init__(
        self,
        src_dir: Path,
        zip_path: Path,
        top_level_names: Iterable[str],
        delete_after_write: bool = False,
    ) -> None:
        self.src_dir = Path(src_dir)
        self.zip_path = Path(zip_path)
        self.delete_after_write = delete_after_write
        self._ordered_names: List[str] = sorted(
            set(top_level_names), key=_top_level_sort_key
        )
        self._expected_names: Set[str] = set(self._ordered_names)
        self._done_names: Set[str] = set()
        self._next_index = 0
        self._zip_file = zipfile.ZipFile(
            self.zip_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=_ZIP_COMPRESS_LEVEL,
        )

    def __enter__(self) -> "OrderedPackZipWriter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            self._zip_file.close()
            return
        self.close()

    def mark_pack_done(self, top_level_name: str) -> None:
        """Record that ``src_dir/top_level_name`` is complete, then write every entry that is ready in order."""
        if top_level_name not in self._expected_names:
            raise ValueError(
                f"Unexpected zip entry {top_level_name!r}: it is not one of the expected top-level names"
            )
        if top_level_name in self._done_names:
            raise ValueError(f"Zip entry {top_level_name!r} was already marked as done")
        self._done_names.add(top_level_name)
        self._flush_ready_prefix()

    def close(self) -> None:
        """Close the zip; raise if any expected top-level entry was never marked as done."""
        try:
            missing_names = [
                name for name in self._ordered_names if name not in self._done_names
            ]
            if missing_names:
                raise ValueError(
                    f"Zip {self.zip_path} is incomplete, entries never marked as done: {missing_names}"
                )
        finally:
            self._zip_file.close()

    def _flush_ready_prefix(self) -> None:
        while (
            self._next_index < len(self._ordered_names)
            and self._ordered_names[self._next_index] in self._done_names
        ):
            self._write_top_level_entry(self._ordered_names[self._next_index])
            self._next_index += 1

    def _write_top_level_entry(self, top_level_name: str) -> None:
        for arcname, path in _list_tree_entries(self.src_dir, top_level_name):
            if arcname.endswith("/"):
                self._zip_file.writestr(
                    _fixed_zip_info(arcname, _ZIP_DIR_EXTERNAL_ATTR),
                    b"",
                    compress_type=zipfile.ZIP_STORED,
                )
            else:
                self._zip_file.writestr(
                    _fixed_zip_info(arcname, _ZIP_FILE_EXTERNAL_ATTR),
                    path.read_bytes(),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=_ZIP_COMPRESS_LEVEL,
                )
        if self.delete_after_write:
            top_level_path = self.src_dir / top_level_name
            if top_level_path.is_dir() and not top_level_path.is_symlink():
                shutil.rmtree(top_level_path)
            else:
                top_level_path.unlink()


def write_deterministic_zip(src_dir: Path, zip_path: Path) -> None:
    """Zip the whole ``src_dir`` tree into ``zip_path``; the bytes depend only on paths and contents."""
    src_dir = Path(src_dir)
    zip_path = Path(zip_path)
    if zip_path.resolve().is_relative_to(src_dir.resolve()):
        raise ValueError(
            f"Zip path {zip_path} must not be inside the zipped directory {src_dir}"
        )
    top_level_names = sorted(os.listdir(src_dir), key=_top_level_sort_key)
    with OrderedPackZipWriter(src_dir, zip_path, top_level_names) as writer:
        for top_level_name in top_level_names:
            writer.mark_pack_done(top_level_name)


@dataclass(frozen=True)
class DumpOutput:
    """One dump of ``ContentDTO.dump_many``: the same arguments ``ContentDTO.dump`` takes, plus the DTO."""

    content_dto: "ContentDTO"
    dir: Path
    zip: bool = True
    packs_to_dump: Optional[Sequence[str]] = None
    output_stem: str = "content_packs"  # without extension
    destination: Optional[PackDestination] = None

    @property
    def zip_path(self) -> Path:
        """Where the zip is written (unchanged from ``shutil.make_archive(dir.parent / output_stem, "zip", dir)``)."""
        return Path(self.dir).parent / f"{self.output_stem}.zip"


@dataclass(frozen=True)
class PackDumpResult:
    """The outcome of dumping one pack; small and picklable, so a forked worker can return it."""

    task_index: int
    output_index: int
    pack_id: str
    ok: bool
    seconds: float
    error_text: str = ""
    # ``MarkdownImagesCollector.export()`` of this pack's dump (also on failure: what it recorded until then).
    markdown_images: Dict[str, Any] = field(default_factory=dict)
    worker_pid: int = 0
    # ``ru_maxrss`` of the dumping process (KiB on Linux, bytes on macOS).
    max_rss: Optional[int] = None
    # 1..N for a fork pool worker, 0 for the in-process (``workers=1``) dump.
    worker_index: int = 0
    # The exception ``Pack.dump`` raised; in-process only (a worker returns ``None``, it may not pickle).
    exception: Optional[BaseException] = field(default=None, compare=False, repr=False)


@dataclass
class DumpReport:
    """What ``dump_many`` did: the worker count used and one result per pack, in the serial task order."""

    workers: int
    seconds: float = 0.0
    results: List[PackDumpResult] = field(default_factory=list)

    @property
    def errors(self) -> List[PackDumpResult]:
        return [result for result in self.results if not result.ok]


class PackDumpError(Exception):
    """A pack dump failed; carries the pack id, the output index, and the formatted traceback.

    With ``workers=1`` the exception ``Pack.dump`` raised is its ``__cause__``; a fork pool worker only
    returns the traceback text, so there it has no cause.
    """

    def __init__(
        self,
        pack_id: str,
        output_index: int,
        traceback_text: str,
        report: Optional[DumpReport] = None,
    ) -> None:
        super().__init__(pack_id, output_index, traceback_text)
        self.pack_id = pack_id
        self.output_index = output_index
        self.traceback_text = traceback_text
        self.report = report

    def __str__(self) -> str:
        return f"Failed dumping pack {self.pack_id} (output #{self.output_index}):\n{self.traceback_text}"


@dataclass(frozen=True)
class _DumpState:
    """Everything a dump task needs. Workers inherit it through fork; only task indices cross processes."""

    outputs: Tuple[DumpOutput, ...]
    output_packs: Tuple[Tuple[Pack, ...], ...]
    tasks: Tuple[
        Tuple[int, int], ...
    ]  # (output_index, pack_index), in the serial order
    marketplace: MarketplaceVersions
    pack_dump_kwargs: Dict[str, Any]

    def task_pack(self, task_index: int) -> Tuple[DumpOutput, Pack]:
        output_index, pack_index = self.tasks[task_index]
        return self.outputs[output_index], self.output_packs[output_index][pack_index]


# Set by ``dump_many`` only while its fork pool runs (cleared in ``finally``); read by the forked workers.
_DUMP_STATE: Optional[_DumpState] = None

# This process's dump worker number: set by ``_dump_worker_init`` in a forked worker, 0 in the parent.
_WORKER_INDEX = 0

DEFAULT_WORKER_LOG_PREFIX = "dump_worker"


def _worker_log_dir(outputs: Sequence[DumpOutput]) -> Path:
    """The SDK log directory (``DEMISTO_SDK_LOG_FILE_PATH``); without it, the parent of the first output dir."""
    if os.getenv(DEMISTO_SDK_LOG_FILE_PATH):
        return calculate_log_dir(None)
    log_dir = Path(outputs[0].dir).resolve().parent
    logger.info(
        f"{DEMISTO_SDK_LOG_FILE_PATH} is not set, writing the dump worker logs to {log_dir}"
    )
    return log_dir


def _worker_log_path(log_dir: Path, worker_log_prefix: str, worker_index: int) -> Path:
    return log_dir / f"{worker_log_prefix}_{worker_index}.log"


def _dump_worker_init(
    worker_counter: Any, log_dir: str, worker_log_prefix: str
) -> None:
    """Fork pool initializer: take the next worker number, then log to this worker's own file.

    The inherited sinks are removed: several processes writing (and rotating) the parent's log file is unsafe.
    WARNING and above also go to stderr, so failures still show in the job output. The file is line-buffered:
    a pool worker ends with ``os._exit``, which would drop a buffered tail.
    """
    global _WORKER_INDEX
    with worker_counter.get_lock():
        worker_counter.value += 1
        _WORKER_INDEX = worker_counter.value
    diagnose = string_to_bool(os.getenv(LOGURU_DIAGNOSE, "False"))
    logger.remove()
    logger.add(
        _worker_log_path(Path(log_dir), worker_log_prefix, _WORKER_INDEX),
        format=FILE_FORMAT,
        level=DEFAULT_FILE_THRESHOLD,
        colorize=False,
        diagnose=diagnose,
        enqueue=False,
        buffering=1,
    )
    logger.add(
        sys.stderr,
        format=f"[dump-worker {_WORKER_INDEX}] {{message}}",
        level="WARNING",
        colorize=False,
        diagnose=diagnose,
    )


def _max_rss() -> Optional[int]:
    try:
        import resource
    except ImportError:  # not on Unix
        return None
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _select_packs(output: DumpOutput) -> List[Pack]:
    """The packs ``output`` dumps, in the DTO order: filtered by ``packs_to_dump``, then by ``destination``."""
    logger.debug(f"Got packs to dump: {output.packs_to_dump}")
    packs: List[Pack] = list(output.content_dto.packs)
    if output.packs_to_dump is not None:
        pack_ids_to_dump = set(output.packs_to_dump)
        packs = [pack for pack in packs if pack.object_id in pack_ids_to_dump]
    if output.destination is not None:
        packs = [pack for pack in packs if pack.destination == output.destination]
    if not packs:
        logger.debug("didn't got packs to dump, skipping")
        return []
    logger.debug(
        f"Starting repository dump for packs: {[pack.object_id for pack in packs]}"
    )
    return packs


def _validate_output_dirs(outputs: Sequence[DumpOutput]) -> None:
    """A zipped output's dir is zipped and removed as a whole, so no other output may share it."""
    outputs_by_dir: Dict[Path, DumpOutput] = {}
    for output in outputs:
        resolved_dir = Path(output.dir).resolve()
        other_output = outputs_by_dir.setdefault(resolved_dir, output)
        if other_output is not output and (output.zip or other_output.zip):
            raise ValueError(
                f"Dump outputs {other_output.output_stem!r} and {output.output_stem!r} share the directory "
                f"{output.dir}, which is zipped and removed; give each zipped output its own directory"
            )


def _build_dump_state(
    outputs: Sequence[DumpOutput],
    marketplace: MarketplaceVersions,
    pack_dump_kwargs: Dict[str, Any],
) -> _DumpState:
    output_packs: List[Tuple[Pack, ...]] = []
    tasks: List[Tuple[int, int]] = []
    for output_index, output in enumerate(outputs):
        Path(output.dir).mkdir(parents=True, exist_ok=True)
        packs = tuple(_select_packs(output))
        output_packs.append(packs)
        tasks.extend((output_index, pack_index) for pack_index in range(len(packs)))
    if tasks and "version_info" not in pack_dump_kwargs:
        # Evaluated once per dump instead of once per pack (it needs a git lookup).
        pack_dump_kwargs = {**pack_dump_kwargs, "version_info": get_version_info()}
    return _DumpState(
        outputs=tuple(outputs),
        output_packs=tuple(output_packs),
        tasks=tuple(tasks),
        marketplace=marketplace,
        pack_dump_kwargs=pack_dump_kwargs,
    )


def _run_dump_task(state: _DumpState, task_index: int) -> PackDumpResult:
    """Dump one pack, recording its markdown images in a fresh collector instead of the shared files."""
    output, pack = state.task_pack(task_index)
    collector = MarkdownImagesCollector()
    error_text = ""
    dump_exception: Optional[BaseException] = None
    start = time.monotonic()
    try:
        with collect_markdown_images(collector):
            pack.dump(
                ContentDTO._artifact_path(Path(output.dir), pack),
                state.marketplace,
                **state.pack_dump_kwargs,
            )
    except Exception as error:
        error_text = traceback.format_exc()
        dump_exception = error
    seconds = time.monotonic() - start
    logger.debug(f"dump of pack {pack.object_id} took {seconds:.1f}s")
    return PackDumpResult(
        task_index=task_index,
        output_index=state.tasks[task_index][0],
        pack_id=pack.object_id,
        ok=not error_text,
        seconds=seconds,
        error_text=error_text,
        markdown_images=collector.export(),
        worker_pid=os.getpid(),
        max_rss=_max_rss(),
        worker_index=_WORKER_INDEX,
        exception=dump_exception,
    )


def _run_dump_task_in_worker(task_index: int) -> PackDumpResult:
    """Fork pool entry point: receives only an index and reads everything else from ``_DUMP_STATE``."""
    state = _DUMP_STATE
    if state is None:
        raise RuntimeError(
            "_DUMP_STATE is not set: dump workers must be forked by ContentDTO.dump_many"
        )
    try:
        # The exception object stays in the worker: it may not pickle; the traceback text is returned.
        return replace(_run_dump_task(state, task_index), exception=None)
    except (
        BaseException
    ):  # e.g. SystemExit raised by a pack dump: report it with the pack id
        _, pack = state.task_pack(task_index)
        return PackDumpResult(
            task_index=task_index,
            output_index=state.tasks[task_index][0],
            pack_id=pack.object_id,
            ok=False,
            seconds=0.0,
            error_text=traceback.format_exc(),
            worker_pid=os.getpid(),
            worker_index=_WORKER_INDEX,
        )


def _effective_workers(workers: int, task_count: int) -> int:
    if workers < 1:
        raise ValueError(f"workers must be at least 1, got {workers}")
    workers = min(workers, task_count)
    if workers > 1 and "fork" not in multiprocessing.get_all_start_methods():
        logger.warning(
            f"The 'fork' start method is not available on this platform, dumping serially instead of with {workers} workers"
        )
        return 1
    return max(workers, 1)


def _submission_order(state: _DumpState) -> List[int]:
    """Largest packs first (by content item count), so a big pack does not start last; ties keep the serial order."""
    weights = [
        sum(1 for _ in state.task_pack(task_index)[1].content_items)
        for task_index in range(len(state.tasks))
    ]
    return sorted(
        range(len(state.tasks)),
        key=lambda task_index: (-weights[task_index], task_index),
    )


def _partial_zip_path(output: DumpOutput) -> Path:
    """The zip is streamed here and renamed to ``zip_path`` on success, so a failed dump leaves no partial zip."""
    return output.zip_path.with_name(f".{output.zip_path.name}.partial")


class _DumpSession:
    """Parent-side bookkeeping of one ``dump_many``: results, streamed zips, timings, and the final writes."""

    def __init__(self, state: _DumpState, started_at: float, workers: int) -> None:
        self.state = state
        self.started_at = started_at
        self.report = DumpReport(workers=workers)
        self.results: Dict[int, PackDumpResult] = {}
        self.output_started_at: List[Optional[float]] = [None] * len(state.outputs)
        self.output_remaining_tasks = Counter(
            output_index for output_index, _ in state.tasks
        )
        # Per zipped output: how many tasks still have to finish before a pack directory is complete.
        self.remaining_tasks_by_dir_name: Dict[int, Counter] = {}
        self.zip_writers: Dict[int, OrderedPackZipWriter] = {}

    def open_zip_writers(self) -> None:
        for output_index, output in enumerate(self.state.outputs):
            packs = self.state.output_packs[output_index]
            if not (output.zip and packs):
                continue
            output_dir = Path(output.dir)
            # ``Pack.dump`` creates no directory for a pack whose source path is missing, so it is not expected.
            remaining_tasks = Counter(
                ContentDTO._artifact_path(output_dir, pack).name
                for pack in packs
                if pack.path.exists()
            )
            # ``make_archive`` zipped the whole directory, so entries that were already there are zipped too.
            preexisting_names = set(os.listdir(output_dir)) - set(remaining_tasks)
            writer = OrderedPackZipWriter(
                output_dir,
                _partial_zip_path(output),
                [*remaining_tasks, *preexisting_names],
            )
            self.zip_writers[output_index] = writer
            self.remaining_tasks_by_dir_name[output_index] = remaining_tasks
            for name in sorted(preexisting_names):
                writer.mark_pack_done(name)

    def mark_output_started(self, output_index: int) -> None:
        if self.output_started_at[output_index] is None:
            self.output_started_at[output_index] = time.monotonic()

    def handle(self, result: PackDumpResult) -> None:
        """Record a result; on success, stream its pack into the zip, and finalize the output after its last pack."""
        self.results[result.task_index] = result
        output_index = result.output_index
        self.output_remaining_tasks[output_index] -= 1
        if not result.ok:
            return
        if output_index in self.zip_writers:
            self._mark_pack_dir_done(result)
        if self.output_remaining_tasks[output_index] == 0:
            self._finalize_output(output_index)

    def _mark_pack_dir_done(self, result: PackDumpResult) -> None:
        output, pack = self.state.task_pack(result.task_index)
        dir_name = ContentDTO._artifact_path(Path(output.dir), pack).name
        remaining_tasks = self.remaining_tasks_by_dir_name[result.output_index]
        if dir_name not in remaining_tasks:
            return
        remaining_tasks[dir_name] -= 1
        if remaining_tasks[dir_name] == 0:
            self.zip_writers[result.output_index].mark_pack_done(dir_name)

    def _finalize_output(self, output_index: int) -> None:
        """As the old ``dump`` did right after its packs: zip the output dir, then remove it."""
        output = self.state.outputs[output_index]
        writer = self.zip_writers.pop(output_index, None)
        if writer is not None:
            writer.close()
            os.replace(_partial_zip_path(output), output.zip_path)
            shutil.rmtree(output.dir)
        started_at = self.output_started_at[output_index] or self.started_at
        pack_count = len(self.state.output_packs[output_index])
        # ``parse_artifacts_step.py`` keys on this line.
        logger.info(
            f"dump[{output.output_stem}] of {pack_count} packs took {time.monotonic() - started_at:.1f}s"
        )

    def pack_error(self, result: PackDumpResult) -> PackDumpError:
        # Format arguments are not parsed for color markup (a traceback may contain "<module>").
        logger.error("Failed dumping pack {}:\n{}", result.pack_id, result.error_text)
        error = PackDumpError(
            result.pack_id, result.output_index, result.error_text, self._report()
        )
        error.__cause__ = result.exception
        return error

    def log_pack_worker(self, result: PackDumpResult) -> None:
        """Which worker dumped the pack, so its log lines can be found in that worker's log file."""
        output = self.state.outputs[result.output_index]
        logger.info(
            f"dump[{output.output_stem}] pack {result.pack_id} -> worker {result.worker_index} "
            f"(pid {result.worker_pid}) took {result.seconds:.1f}s"
        )

    def worker_died_error(self, task_index: int, error: BaseException) -> PackDumpError:
        unfinished_pack_ids = [
            self.state.task_pack(index)[1].object_id
            for index in range(len(self.state.tasks))
            if index not in self.results
        ]
        _, pack = self.state.task_pack(task_index)
        message = (
            f"A dump worker died ({error!r}); {len(unfinished_pack_ids)} packs did not finish, "
            f"for example: {unfinished_pack_ids[:20]}"
        )
        logger.error("{}", message)
        return PackDumpError(
            pack.object_id, self.state.tasks[task_index][0], message, self._report()
        )

    def write_markdown_images(self) -> None:
        """Merge the per-pack records in the serial task order (not completion order) and write each file once."""
        batches = [
            self.results[task_index].markdown_images
            for task_index in sorted(self.results)
            if self.results[task_index].markdown_images
        ]
        outer_collector = get_active_markdown_images_collector()
        collector = outer_collector or MarkdownImagesCollector()
        collector.merge(batches)
        if outer_collector is None:
            collector.write_files()

    def finish(self) -> DumpReport:
        if len(self.results) != len(self.state.tasks) or self.zip_writers:
            raise RuntimeError(
                f"Dump finished with {len(self.results)} results for {len(self.state.tasks)} packs"
                f" and {len(self.zip_writers)} unfinished zips"
            )
        logger.debug(
            f"Repository dump ended. Took {time.monotonic() - self.started_at} seconds"
        )
        self.write_markdown_images()
        max_rss_values = [
            result.max_rss for result in self.results.values() if result.max_rss
        ]
        logger.debug(
            f"dump used {self.report.workers} workers; max ru_maxrss: {max(max_rss_values, default=None)}"
        )
        return self._report()

    def abort(self, error: BaseException) -> None:
        """Leave what the serial path left on failure: the unzipped dirs, the markdown images recorded so far, no partial zip."""
        try:
            if isinstance(error, PackDumpError):
                self.write_markdown_images()
        finally:
            for output_index, writer in self.zip_writers.items():
                writer.__exit__(type(error), error, error.__traceback__)
                _partial_zip_path(self.state.outputs[output_index]).unlink(
                    missing_ok=True
                )
            self.zip_writers.clear()

    def _report(self) -> DumpReport:
        self.report.seconds = time.monotonic() - self.started_at
        self.report.results = [self.results[index] for index in sorted(self.results)]
        return self.report


def _dump_serially(state: _DumpState, session: _DumpSession) -> None:
    """In-process, in the serial task order, stopping at the first failure (as the old loop did)."""
    for task_index, (output_index, _) in enumerate(state.tasks):
        session.mark_output_started(output_index)
        result = _run_dump_task(state, task_index)
        session.handle(result)
        if not result.ok:
            raise session.pack_error(result)


def _dump_in_fork_pool(
    state: _DumpState, session: _DumpSession, workers: int, worker_log_prefix: str
) -> None:
    """Fork ``workers`` processes that inherit ``state`` and dump packs by task index; stop at the first failure.

    Each worker logs to ``<log dir>/<worker_log_prefix>_<n>.log`` (n = 1..workers).
    """
    global _DUMP_STATE
    log_dir = _worker_log_dir(state.outputs)
    _DUMP_STATE = state
    gc.collect()
    gc.freeze()  # keep the GC from writing to inherited objects, which would copy their pages in every worker
    if threading.active_count() > 1:
        logger.warning(
            f"Forking dump workers while {threading.active_count()} threads are running"
        )
    executor: Optional[ProcessPoolExecutor] = None
    try:
        mp_context = multiprocessing.get_context("fork")
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=mp_context,
            initializer=_dump_worker_init,
            initargs=(mp_context.Value("i", 0), str(log_dir), worker_log_prefix),
        )
        for output_index in range(len(state.outputs)):
            session.mark_output_started(output_index)
        futures = {
            executor.submit(_run_dump_task_in_worker, task_index): task_index
            for task_index in _submission_order(state)
        }
        for future in as_completed(futures):
            try:
                result = future.result()
            except BrokenProcessPool as error:
                raise session.worker_died_error(futures[future], error) from error
            session.log_pack_worker(result)
            session.handle(result)
            if not result.ok:
                raise session.pack_error(result)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        gc.unfreeze()
        _DUMP_STATE = None
        worker_log_paths = [
            str(_worker_log_path(log_dir, worker_log_prefix, worker_index))
            for worker_index in range(1, workers + 1)
        ]
        logger.info(f"dump worker log files: {worker_log_paths}")


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
    ) -> DumpReport:
        """Dump all packs, or only those matching ``destination``; ``kwargs`` (e.g. ``strip_internal``) are forwarded to ``Pack.dump``.

        A serial (``workers=1``) wrapper over ``dump_many``.
        """
        return ContentDTO.dump_many(
            [
                DumpOutput(
                    content_dto=self,
                    dir=dir,
                    zip=zip,
                    packs_to_dump=packs_to_dump,
                    output_stem=output_stem,
                    destination=destination,
                )
            ],
            marketplace,
            workers=1,
            **kwargs,
        )

    @staticmethod
    def dump_many(
        outputs: Sequence[DumpOutput],
        marketplace: MarketplaceVersions,
        workers: int = 1,
        worker_log_prefix: str = DEFAULT_WORKER_LOG_PREFIX,
        **kwargs,
    ) -> DumpReport:
        """Dump several outputs (e.g. regular and managed packs) as one flat task list, optionally with a fork pool.

        Tasks are the outputs in the given order and, inside each, its packs in the DTO order (the serial order).
        ``workers=1`` runs them in-process in that order. ``workers>1`` forks a process pool (explicit "fork"
        context; serial fallback where fork is unavailable); workers receive only task indices and read the
        packs from the inherited ``_DUMP_STATE``, so no ``Pack`` is pickled. Precondition for ``workers>1``:
        no open Neo4j driver (the dump uses only the in-memory DTO).

        Markdown images records are merged in the serial order and each file is written once, so the files
        match the serial output. A zipped output is streamed into a deterministic zip at
        ``dir.parent / f"{output_stem}.zip"`` as its packs finish, and ``dir`` is removed afterwards.

        With ``workers>1``, each worker logs to ``<log dir>/<worker_log_prefix>_<n>.log`` (n = 1..workers),
        where the log dir is ``DEMISTO_SDK_LOG_FILE_PATH``, or, when it is unset, the parent of the first
        output dir; the parent logs which worker dumped each pack.

        Raises:
            PackDumpError: on the first failed pack (with its id and traceback; with ``workers=1`` the
                original exception is its ``__cause__``). The remaining packs are not dumped, no zip is
                written, and the dumped directories are kept.
        """
        _validate_output_dirs(outputs)
        started_at = time.monotonic()
        state = _build_dump_state(outputs, marketplace, kwargs)
        if not state.tasks:
            return DumpReport(workers=0)
        effective_workers = _effective_workers(workers, len(state.tasks))
        session = _DumpSession(state, started_at, effective_workers)
        try:
            session.open_zip_writers()
            if effective_workers == 1:
                _dump_serially(state, session)
            else:
                _dump_in_fork_pool(state, session, effective_workers, worker_log_prefix)
        except BaseException as error:
            session.abort(error)
            raise
        return session.finish()

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
