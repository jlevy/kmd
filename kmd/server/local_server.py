import asyncio
import threading
from functools import cache, cached_property
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn
    from fastapi import FastAPI

from kmd.config.logger import get_logger
from kmd.config.settings import (
    global_settings,
    LOCAL_SERVER_LOG_FILE,
    resolve_and_create_dirs,
    update_global_settings,
)
from kmd.errors import InvalidInput, InvalidState
from kmd.server import server_routes
from kmd.server.port_tools import find_available_local_port
from kmd.util.format_utils import fmt_path

log = get_logger(__name__)


@cache
def log_file_path(port: int) -> Path:
    # Use a different log file for each port (server instance).
    return resolve_and_create_dirs(LOCAL_SERVER_LOG_FILE.format(port=port))


def _server_config(app: "FastAPI", host: str, port: int) -> "uvicorn.Config":
    import uvicorn

    return uvicorn.Config(
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


def _app_setup() -> "FastAPI":
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    app = FastAPI()

    app.include_router(server_routes.router)

    # Map common exceptions to HTTP codes.
    # FileNotFound first, since it might also be an InvalidInput.
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_exception_handler(request: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"message": f"File not found: {exc}"},
        )

    @app.exception_handler(InvalidInput)
    async def invalid_input_exception_handler(request: Request, exc: InvalidInput):
        return JSONResponse(
            status_code=400,
            content={"message": f"Invalid input: {exc}"},
        )

    # Global exception handler.
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error."},
        )

    return app


def _pick_port() -> int:
    """
    Pick an available port for the local server and update the global settings.
    """
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

    return port


class LocalServer:
    def __init__(self):
        self.server_lock = threading.RLock()
        self.server_instance: Optional["uvicorn.Server"] = None
        self.did_exit = threading.Event()

    @cached_property
    def app(self) -> "FastAPI":
        return _app_setup()

    def _run_server(self):
        import uvicorn

        port = _pick_port()
        host = global_settings().local_server_host
        config = _server_config(self.app, host, port)
        with self.server_lock:
            server = uvicorn.Server(config)
            self.server_instance = server

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
                self.did_exit.set()

        try:
            asyncio.run(serve())
        except Exception as e:
            log.error("Server failed with error: %s", e)
        finally:
            with self.server_lock:
                self.server_instance = None

    def start_server(self):
        with self.server_lock:
            if self.server_instance:
                log.warning(
                    "Server already running on %s:%s.",
                    self.server_instance.config.host,
                    self.server_instance.config.port,
                )
                return

            self.did_exit.clear()
            server_thread = threading.Thread(target=self._run_server, daemon=True)
            server_thread.start()
            log.info("Created new local server thread: %s", server_thread)

    def stop_server(self):
        with self.server_lock:
            if not self.server_instance:
                log.warning("Server already stopped.")
                return
            self.server_instance.should_exit = True

            # Wait a few seconds for the server to shut down.
            timeout = 5.0
            if not self.did_exit.wait(timeout=timeout):
                log.warning("Server did not shut down within %s seconds, forcing exit.", timeout)
                self.server_instance.force_exit = True
                if not self.did_exit.wait(timeout=timeout):
                    raise InvalidState(f"Server did not shut down within {timeout} seconds")

            self.server_instance = None
            log.warning("Server stopped.")

    def restart_server(self):
        self.stop_server()
        self.start_server()


# Singleton instance.
# Note this is quick to set up (lazy import).
_local_server = LocalServer()


def start_server():
    _local_server.start_server()


def stop_server():
    _local_server.stop_server()


def restart_server():
    _local_server.restart_server()
