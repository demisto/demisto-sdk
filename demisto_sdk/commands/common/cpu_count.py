import logging
import os

logger = logging.getLogger(
    "demisto-sdk"
)  # not using the standard logger, due to circular import


DEMISTO_SDK_MAX_CPU_CORES = "DEMISTO_SDK_MAX_CPU_CORES"


def cpu_count() -> int:
    result = max_available_cpus = os.cpu_count() or 1

    # best to use CPU_COUNT-1
    if result > 1:  # but when CPU_COUNT==1, we'd get 0
        result -= 1

    if (raw_env_var := os.getenv(DEMISTO_SDK_MAX_CPU_CORES)) is not None:
        try:
            max_allowed_cpus = int(raw_env_var)
            requsted_cpus = min(max_allowed_cpus, max_available_cpus)
            result = max(1, requsted_cpus)
        except (TypeError, ValueError):
            logger.exception(
                f"failed converting DEMISTO_SDK_MAX_CPU_CORES={raw_env_var} to integer, using default cpu count instead"
            )
    logger.debug(f"cpu_count={result}")
    return result
