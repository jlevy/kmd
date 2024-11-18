from enum import Enum

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from kmd.config.logger import get_logger
from kmd.file_storage.file_store import FileStore
from kmd.help.command_help import explain_command
from kmd.model.paths_model import StorePath
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


@router.get(Route.view_item)
def view_item(store_path: str, ws_name: str):
    item = server_get_workspace(ws_name).load(StorePath(store_path))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return HTMLResponse(
        render_web_template(
            "base_webpage.html.jinja",
            {
                "title": item.title or "Untitled",
                "content": render_web_template("item_view.html.jinja", {"item": item}),
            },
        )
    )


@router.get(Route.explain)
def explain(text: str):
    help_str = explain_command(text, use_assistant=True)
    if not help_str:
        raise HTTPException(status_code=404, detail="Explanation not found")

    return HTMLResponse(
        render_web_template(
            "base_webpage.html.jinja",
            {
                "title": f"Help: {text}",
                "content": render_web_template("explain_view.html.jinja", {"help_str": help_str}),
            },
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
