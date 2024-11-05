from typing import List, Optional

from pydantic import BaseModel

from kmd.model.args_model import Signature
from kmd.model.commands_model import CommentedCommand
from kmd.shell.shell_output import fill_text, Wrap


class Script(BaseModel):
    """
    A script of commands to be executed by the assistant.
    """

    description: Optional[str]
    """
    A short description of what the script does.
    """

    signature: Optional[Signature]
    """
    The signature of the script, which is the signature of the first command.
    """

    commands: List[CommentedCommand]
    """
    The commands to be executed by the assistant.
    """

    @property
    def formatted_description(self) -> Optional[str]:
        if not self.description:
            return None
        else:
            return fill_text(self.description, text_wrap=Wrap.WRAP_FULL, extra_indent="# ")

    def formatted_input_check(self) -> Optional[str]:
        if not self.signature:
            return None
        else:
            return f"# Signature: {self.signature.human_str()}"

    def script_str(self) -> str:
        return "\n\n".join(
            filter(
                None,
                [
                    self.formatted_description,
                    self.formatted_input_check(),
                    *[cmd.script_str() for cmd in self.commands],
                ],
            )
        )
