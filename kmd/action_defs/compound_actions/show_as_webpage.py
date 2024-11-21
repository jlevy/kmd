from typing import Tuple

from kmd.commands.files_commands import show
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ActionInput, ActionResult, Precondition
from kmd.model.commands_model import Command
from kmd.model.compound_actions_model import SequenceAction
from kmd.model.shell_model import ShellResult
from kmd.preconditions.precondition_defs import has_text_body, is_html


@kmd_action
class ShowAsWebpage(SequenceAction):

    name: str = "show_as_webpage"

    description: str = """
        Show text, Markdown, or HTML as a nicely formatted webpage.
        """

    action_names: Tuple[str, ...] = ("webpage_config", "webpage_generate")

    precondition: Precondition = is_html | has_text_body

    def run(self, items: ActionInput) -> ActionResult:
        result = super().run(items)
        result.shell_result = ShellResult(display_command=Command.assemble(show))
        return result
