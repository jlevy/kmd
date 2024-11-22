import asyncio
import threading
from pathlib import Path

from cachetools import cached

from kmd.config.logger import get_logger
from kmd.config.settings import (
    global_settings,
    LOCAL_SERVER_LOG_FILE,
    resolve_and_create_dirs,
    update_global_settings,
)
from kmd.server import server_routes
from kmd.server.port_tools import find_available_local_port
from kmd.util.format_utils import fmt_path


log = get_logger(__name__)

should_exit = threading.Event()

server_lock = threading.Lock()
server_instance = None


@cached({})
def log_file_path(port: int) -> Path:
    # Use a different log file for each port (server instance).
    return resolve_and_create_dirs(LOCAL_SERVER_LOG_FILE.format(port=port))


@cached({})
def _server_setup():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    global app
    app = FastAPI()

    app.include_router(server_routes.router)

    # Map common exceptions to HTTP codes.
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_exception_handler(request: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"message": f"File not found: {exc}"},
        )


def _run_server():
    import uvicorn

    global server_instance

    settings = global_settings()
    host = settings.local_server_host
    port = find_available_local_port(
        host,
        range(
            settings.local_server_ports_start,
            settings.local_server_ports_start + settings.local_server_ports_max,
        ),
    )
    with update_global_settings() as settings:
        settings.local_server_port = port

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": str(log_file_path(port)),
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
            },
        },
    )
    server = uvicorn.Server(config)
    with server_lock:
        server_instance = server

    async def serve():
        try:
            log.message(
                "Starting local server on %s:%s",
                host,
                port,
            )
            log.message("Local server logs: %s", fmt_path(log_file_path(port)))
            await server.serve()
        finally:
            should_exit.set()

    try:
        asyncio.run(serve())
    except Exception as e:
        log.error("Server failed with error: %s", e)
    finally:
        with server_lock:
            server_instance = None


def start_server():
    _server_setup()

    with server_lock:
        if server_instance:
            log.info("Server already running: %s", server_instance)
            return

        should_exit.clear()
        server_thread = threading.Thread(target=_run_server, daemon=True)
        server_thread.start()
        log.info("Created new local server: %s", server_instance)


def stop_server():
    global server_instance
    with server_lock:
        if not server_instance:
            log.warning("Server already stopped.")
            return  # Server not running.
        server_instance.should_exit = True

    if not should_exit.wait(timeout=5.0):  # Wait up to 5 seconds for server to stop.
        log.warning("Server did not shut down within 5 seconds.")

    with server_lock:
        server_instance = None
        log.warning("Server stopped.")
