import contextlib
import os

from demisto_sdk.commands.common.logger import logger

DEMISTO_SDK_MAX_CPU_CORES = "DEMISTO_SDK_MAX_CPU_CORES"


def cpu_count() -> int:
    max_available_cpus = os.cpu_count() or 1
    with contextlib.suppress(TypeError, ValueError, KeyError):
        max_allowed_cpus = int(os.environ[DEMISTO_SDK_MAX_CPU_CORES])
        requsted_cpus = min(max_allowed_cpus, max_available_cpus)
        return max(1, requsted_cpus)
    logger.debug(f"cpu_count={max_allowed_cpus}")
    return max_available_cpus
