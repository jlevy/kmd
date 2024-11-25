from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from kmd.config import colors
from kmd.config.logger import get_logger
from kmd.file_storage.file_store import FileStore
from kmd.help.command_help import explain_command
from kmd.model.paths_model import StorePath
from kmd.server.local_urls import local_url
from kmd.web_gen.template_render import render_web_template
from kmd.workspaces.workspace_names import check_strict_workspace_name

log = get_logger(__name__)


router = APIRouter()


def server_get_workspace(ws_name: str) -> FileStore:
    from kmd.workspaces.workspaces import get_workspace

    ws_name = check_strict_workspace_name(ws_name)
    file_store = get_workspace(ws_name)
    if not file_store:
        raise HTTPException(status_code=404, detail=f"Workspace not found: `{ws_name}`")
    return file_store


class Route(str, Enum):
    view_item = "/view/item"
    read_item = "/read/item"
    explain = "/explain"


@router.api_route(Route.view_item, methods=["GET", "HEAD"])
def view_item(request: Request, store_path: str, ws_name: str):
    item = server_get_workspace(ws_name).load(StorePath(store_path))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.is_binary:
        # Return the item itself.
        # TODO: Could make this thumbnails for images, PDF, etc.

        mime_type = item.format and item.format.mime_type()
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

        # Serve a webpage with info about the item
        page_url = local_url(Route.view_item, store_path=store_path, ws_name=ws_name)

        body_text = None
        if item.body and len(item.body) > 10 * 1024 * 1024:
            body_text = "Item body is too large to display!"
        elif not item.is_binary:
            body_text = item.body_text()

        return HTMLResponse(
            render_web_template(
                "base_webpage.html.jinja",
                {
                    "title": item.display_title(),
                    "content": render_web_template(
                        "item_view.html.jinja",
                        {"item": item, "page_url": page_url, "body_text": body_text},
                    ),
                },
                css_overrides={"color-bg": colors.web.bg_translucent},
            )
        )


@router.get(Route.explain)
def explain(text: str):
    help_str = explain_command(text, use_assistant=True)
    if not help_str:
        raise HTTPException(status_code=404, detail="Explanation not found")

    page_url = local_url(Route.explain, text=text)

    return HTMLResponse(
        render_web_template(
            "base_webpage.html.jinja",
            {
                "title": f"Help: {text}",
                "content": render_web_template(
                    "explain_view.html.jinja", {"help_str": help_str, "page_url": page_url}
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
