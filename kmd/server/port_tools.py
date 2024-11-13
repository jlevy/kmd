import socket
import time

from kmd.config.logger import get_logger


log = get_logger(__name__)


def wait_for_local_port(host: str, port: int, timeout: int = 0):
    """
    Check if the specified port is free. Will log a warning if the port is in
    use and wait until it becomes available.
    """
    start_time = time.time()
    errors = 0
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                if errors > 0:
                    log.message("Port %s:%s is free again!", host, port)
                return
            except OSError:
                elapsed_time = time.time() - start_time
                if timeout and elapsed_time > timeout:
                    log.error(
                        "Port %s:%s still in use after %s seconds. Giving up.",
                        host,
                        port,
                        timeout,
                    )
                    raise RuntimeError("Port in use")
                if errors == 0:
                    log.warning(
                        "Cannot bind to %s:%s. Will wait for port to become free.",
                        host,
                        port,
                    )
                errors += 1
                time.sleep(2)
