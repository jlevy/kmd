from kmd.commands.command_defs import show
from kmd.exec.action_registry import kmd_action
from kmd.model.actions_model import ActionInput, ActionResult
from kmd.model.commands_model import Command
from kmd.model.compound_actions_model import SequenceAction
from kmd.model.output_model import CommandOutput
from kmd.preconditions.precondition_defs import has_text_body, is_html


@kmd_action(for_each_item=True)
class ShowAsHtml(SequenceAction):
    def __init__(self):
        super().__init__(
            name="show_as_html",
            action_names=["webpage_config", "webpage_generate"],
            description="Show text, Markdown, or HTML as a nicely formatted webpage.",
            precondition=is_html | has_text_body,
        )

    def run(self, items: ActionInput) -> ActionResult:
        result = super().run(items)
        result.command_output = CommandOutput(display_command=Command(show))
        return result
