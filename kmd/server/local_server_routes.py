from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from kmd.config import colors
from kmd.config.logger import get_logger, record_console
from kmd.config.settings import global_settings
from kmd.errors import InvalidFilename
from kmd.file_storage.file_store import FileStore
from kmd.help.command_help import explain_command
from kmd.model.items_model import Item
from kmd.model.paths_model import StorePath
from kmd.shell.rich_html import RICH_HTML_TEMPLATE
from kmd.shell.shell_output import Wrap
from kmd.shell.shell_printing import print_file_info
from kmd.util.strif import abbreviate_str
from kmd.util.type_utils import not_none
from kmd.web_gen.template_render import render_web_template

log = get_logger(__name__)


router = APIRouter()


def server_get_workspace(ws_name: str) -> FileStore:
    from kmd.workspaces.workspaces import get_workspace

    file_store = get_workspace(ws_name)
    if not file_store:
        raise HTTPException(status_code=404, detail=f"Workspace not found: `{ws_name}`")
    return file_store


def format_local_url(route_path: str, **params: Optional[str]) -> str:
    """
    URL to content on the local server.
    """
    from kmd.server.local_server import LOCAL_SERVER_HOST

    settings = global_settings()
    route_path = route_path.strip("/")
    url = f"http://{LOCAL_SERVER_HOST}:{settings.local_server_port}/{route_path}"
    if params:
        query_params = {k: v for k, v in params.items() if v is not None}
        if query_params:
            query_string = urlencode(query_params)
            url += f"?{query_string}"
    return url


class Route(str, Enum):
    view_file = "/file/view"
    view_item = "/item/view"
    read_item = "/item/read"
    explain = "/explain"


class _LocalUrl:
    def view_file(self, path: Path) -> str:
        return format_local_url(Route.view_file, path=str(path))

    def view_item(self, store_path: StorePath, ws_name: str) -> str:
        return format_local_url(
            Route.view_item, store_path=store_path.display_str(), ws_name=ws_name
        )

    def explain(self, text: str) -> str:
        return format_local_url(Route.explain, text=text)


local_url = _LocalUrl()
"""Create URLs for the local server."""


@router.api_route(Route.view_file, methods=["GET", "HEAD"])
def view_file(request: Request, path: str):
    # Treat the file like an external path for the purposes of viewing.
    try:
        p = Path(path)
        item = Item.from_external_path(p)
        body_text, footer_note = None, None
        if not item.is_binary:
            body_text, footer_note = _read_lines(p)
        page_url = local_url.view_file(p)

        return _serve_item(request, item, page_url, body_text, footer_note)
    except (InvalidFilename, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")


@router.api_route(Route.view_item, methods=["GET", "HEAD"])
def view_item(request: Request, store_path: str, ws_name: str):
    sp = StorePath(store_path)
    item = server_get_workspace(ws_name).load(sp)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # URL to serve a webpage with info about the item.
    page_url = local_url.view_item(store_path=sp, ws_name=ws_name)

    body_text, footer_note = _truncate_text(item.body_text())
    if footer_note:
        body_text += "\n…"

    return _serve_item(request, item, page_url, body_text, footer_note)


@router.api_route(Route.explain, methods=["GET"])
def explain(text: str):
    with record_console() as console:
        explain_command(text, use_assistant=True)
    help_html = console.export_html(code_format=RICH_HTML_TEMPLATE, theme=colors.rich_terminal)

    page_url = local_url.explain(text)

    return HTMLResponse(
        render_web_template(
            "base_webpage.html.jinja",
            {
                "title": f"Help: {text}",
                "content": render_web_template(
                    "explain_view.html.jinja", {"help_html": help_html, "page_url": page_url}
                ),
            },
            css_overrides={"color-bg": colors.web.bg_translucent},
        )
    )


MAX_LINES = 200


def _read_lines(path: Path, max_lines: int = MAX_LINES) -> Tuple[str, Optional[str]]:
    lines = []
    # frontmatter_str, offset = fmf_read_frontmatter_raw(path)
    with open(path, "r") as f:
        # f.seek(offset)
        for i, line in enumerate(f):
            if i >= max_lines:
                return "\n".join(lines), f"Text truncated, showing first {max_lines} lines."
            lines.append(line.rstrip("\n"))
    return "\n".join(lines), None


def _truncate_text(text: str, max_lines: int = MAX_LINES) -> Tuple[str, Optional[str]]:
    num_lines = text.count("\n")
    if num_lines > max_lines:
        lines = text.split("\n", max_lines + 1)
        footer_note = f"Text truncated, showing first {max_lines} of {num_lines} lines."
        return "\n".join(lines[:max_lines]), footer_note
    return text, None


def _serve_item(
    request: Request,
    item: Item,
    page_url: str,
    body_text: Optional[str] = None,
    footer_note: Optional[str] = None,
) -> StreamingResponse | HTMLResponse:
    if item.is_binary:
        # Return the item itself.
        # TODO: Could make this thumbnails for images, PDF, etc.

        mime_type = item.format and item.format.mime_type
        if not mime_type:
            mime_type = "application/octet-stream"

        # Return headers only for HEAD requests.
        if request.method == "HEAD":
            return HTMLResponse(status_code=200, headers={"Content-Type": mime_type})

        # Serve the binary item.
        path = item.store_path or item.external_path
        if not path:
            raise HTTPException(status_code=500, detail="Binary item has no path")

        def file_iterator():
            try:
                with open(path, "rb") as f:
                    while chunk := f.read(8192):  # 8KB chunks
                        yield chunk
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Item not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error streaming file: {e}")

        return StreamingResponse(
            file_iterator(),
            media_type=mime_type,
        )
    else:
        # Return headers only for HEAD requests
        if request.method == "HEAD":
            return HTMLResponse(status_code=200, headers={"Content-Type": "text/html"})

        with record_console() as console:
            print_file_info(
                Path(not_none(item.store_path or item.external_path)),
                show_size_details=True,
                show_format=True,
                text_wrap=Wrap.WRAP,
            )
        file_info_html = console.export_html(
            code_format=RICH_HTML_TEMPLATE, theme=colors.rich_terminal
        )
        log.info(
            "File info html: length %s: %s", len(file_info_html), abbreviate_str(file_info_html)
        )

        return HTMLResponse(
            render_web_template(
                "base_webpage.html.jinja",
                {
                    "title": item.display_title(),
                    "content": render_web_template(
                        "item_view.html.jinja",
                        {
                            "item": item,
                            "page_url": page_url,
                            "file_info_html": file_info_html,
                            "body_text": body_text,
                            "footer_note": footer_note,
                        },
                    ),
                },
                css_overrides={"color-bg": colors.web.bg_translucent},
            )
        )


# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await websocket.send_text(f"Message received: {data}")
#     except WebSocketDisconnect:
#         log.info("WebSocket disconnected")
