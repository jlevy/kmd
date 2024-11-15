from enum import Enum

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fasthtml.common import Body, Div, H2, Head, Html, P, Pre, Span, Style, to_xml

from kmd.config.logger import get_logger
from kmd.file_storage.file_store import FileStore
from kmd.help.command_help import explain_command
from kmd.model.paths_model import StorePath
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


styles = Style(
    """
    body {
        background-color: #f0f0f0e4;
        color: #222222;
        font-family: sans-serif;
        line-height: 1.2;
        font-size: 0.9rem;
    }

    h1 {
        font-size: 1.1rem;
        font-weight: bold;
    }

    h2 {
        font-size: 1.0rem;
        font-weight: italic;
    }

    h3 {
        font-size: 1rem;
        font-weight: italic;
    }

    p {
        margin: 10px 0;
    }

    pre {
        font-size: 0.75rem;
    }
    """
)


@router.get(Route.view_item)
def view_item(store_path: str, ws_name: str):
    item = server_get_workspace(ws_name).load(StorePath(store_path))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return HTMLResponse(
        to_xml(
            Html(
                Head(styles),
                Body(
                    Div(
                        H2(item.title),
                        P(Span("Type: "), Span(item.type.value)),
                        P(Span("State: "), Span(item.state.value)),
                        P(item.description or "No description available"),
                    )
                ),
            )
        )
    )


@router.get(Route.explain)
def explain(text: str, ws_name: str):
    help_str = explain_command(text, use_assistant=True)
    if not help_str:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return HTMLResponse(to_xml(Html(Head(styles), Body(Pre(help_str)))))


# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             await websocket.send_text(f"Message received: {data}")
#     except WebSocketDisconnect:
#         log.info("WebSocket disconnected")
