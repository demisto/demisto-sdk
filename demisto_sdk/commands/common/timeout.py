from contextlib import contextmanager
import signal


@contextmanager
def timeout(seconds, minutes=0, hours=0):
    if seconds is None:
        yield

    def timeout_handler(signum, frame):
        raise TimeoutError(f'Timout after {hours} hours, {minutes} minutes, {seconds} seconds')
    total_seconds = hours * 3600 + minutes * 60 + seconds
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(total_seconds)
    yield
    signal.alarm(0)