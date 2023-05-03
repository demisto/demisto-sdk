import os

DEMISTO_SDK_MAX_CPU_CORES = "DEMISTO_SDK_MAX_CPU_CORES"


def cpu_count():
    max_available_cpus = os.cpu_count() or 1
    try:
        max_allowed_cpus = int(os.environ[DEMISTO_SDK_MAX_CPU_CORES])
        requsted_cpus = min(max_allowed_cpus, max_available_cpus)
        return max(1, requsted_cpus)
    except (TypeError, ValueError, KeyError):
        pass
    return max_available_cpus
