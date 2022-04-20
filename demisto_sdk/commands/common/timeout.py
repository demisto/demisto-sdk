from contextlib import contextmanager
import signal


@contextmanager
def timeout(seconds: int = 0, minutes: int = 0, hours: int = 0):
    """context manager for timeout

    Args:
        seconds (int):  Number of seconds to timeout. Defaults to 0.
        minutes (int): Number of minutes to timeout. Defaults to 0.
        hours (int): Number of hours to timeout. Defaults to 0.

    Raises:
        TimeoutError: if reached timeout raise error
    """
    if not seconds and not minutes and not hours:  # run without timeout
        yield
        return

    def timeout_handler(signum, frame):
        raise TimeoutError(f'Timout after {hours} hours, {minutes} minutes, {seconds} seconds')
    total_seconds = hours * 3600 + minutes * 60 + seconds
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(total_seconds)
    try:
        yield
    finally:
        signal.alarm(0)
