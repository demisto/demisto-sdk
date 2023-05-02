import contextlib
import logging
import os

logger = logging.getLogger(
    "demisto-sdk"
)  # not using the standard logger, due to circular import


DEMISTO_SDK_MAX_CPU_CORES = "DEMISTO_SDK_MAX_CPU_CORES"


def cpu_count() -> int:
    max_available_cpus = os.cpu_count() or 1
    with contextlib.suppress(TypeError, ValueError, KeyError):
        max_allowed_cpus = int(os.environ[DEMISTO_SDK_MAX_CPU_CORES])
        requsted_cpus = min(max_allowed_cpus, max_available_cpus)
        return max(1, requsted_cpus)
    logger.debug(f"cpu_count={max_allowed_cpus}")
    return max_available_cpus
