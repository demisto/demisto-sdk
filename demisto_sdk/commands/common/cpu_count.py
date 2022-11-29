import os

MAX_DEMISTO_SDK_THREADS = 'MAX_DEMISTO_SDK_THREADS'


def cpu_count():
    max_available_cpus = os.cpu_count() or 1
    try:
        max_allowed_cpus = int(os.environ[MAX_DEMISTO_SDK_THREADS])
        requsted_cpus = min(max_allowed_cpus, max_available_cpus)
        return max(1, requsted_cpus)
    except Exception:
        pass
    return max_available_cpus
