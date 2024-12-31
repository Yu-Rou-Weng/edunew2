import itertools
import signal

from pathlib import Path

import psutil

from iotgui import config


__all__ = [
    'handle_signal_for_gunicorn',
    'SIGNALS_USED_BY_GUNICORN',
]

# Ref: https://docs.gunicorn.org/en/latest/signals.html#master-process
_OTHER_SIGNALS_USED_BY_GUNICORN = [
    signal.SIGHUP,
    signal.SIGTTIN,
    signal.SIGTTOU,
    signal.SIGUSR1,
    signal.SIGUSR2,
    signal.SIGWINCH,
]

# Ref: https://docs.gunicorn.org/en/latest/signals.html#master-process
_TERMINATE_SIGNALS_USED_BY_GUNICORN = [
    signal.SIGINT,
    signal.SIGTERM,
    signal.SIGQUIT,
]

SIGNALS_USED_BY_GUNICORN = list(
    itertools.chain(_OTHER_SIGNALS_USED_BY_GUNICORN, _TERMINATE_SIGNALS_USED_BY_GUNICORN)
)


def _get_pid_from_file(pid_file_name: str) -> int:
    """
    Get process pid from a pid file.

    :param pid_file_name: Process ID file name.
    :raise ValueError: If the specified pid file has non-digit characters.
    :return: A process ID or if the specified pid file does not exist or it is not a regular
             file or empty, -1 is returned.
    """
    pid_file = Path(pid_file_name)

    if not pid_file.exists() or not pid_file.is_file():
        return -1

    with pid_file.open() as f:
        return int(f.readline().strip() or -1)


def handle_signal_for_gunicorn(signal_number, _frame):
    """
    This function is used as a signal handler for those signals used by the Gunicorn.
    We will send the signal we received to the Gunicorn master process.
    """
    # Get the Gunicorn master process ID from the pid file
    gunicorn_pid = _get_pid_from_file(config.GUNICORN_PID_FILE_NAME)

    # Ref: https://psutil.readthedocs.io/en/latest/#psutil.Process
    process = psutil.Process(gunicorn_pid)

    # Send the received signal to the Gunicorn master process.
    #
    # Ref: https://psutil.readthedocs.io/en/latest/#psutil.Process.send_signal
    process.send_signal(signal_number)
