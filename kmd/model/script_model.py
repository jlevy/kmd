import re
from typing import List, Optional

from pydantic import BaseModel

from kmd.model.args_model import Signature
from kmd.model.commands_model import as_comment, Command, CommentedCommand


class BareComment(BaseModel):
    """
    A comment that is not associated with a command.
    """

    text: str

    def script_str(self) -> str:
        return as_comment(self.text)


class Script(BaseModel):
    """
    A script of commands to be executed by the assistant. Also useful for lists of
    commented commands, such as for Kmd example docs.
    """

    signature: Optional[Signature]
    """
    The signature of the script, which is the signature of the first command.
    """

    commands: List[BareComment | CommentedCommand]
    """
    Comments or commands to be executed.
    """

    def formatted_signature(self) -> Optional[str]:
        if not self.signature:
            return None
        else:
            return f"# Signature: {self.signature.human_str()}"

    def script_str(self) -> str:
        return "\n\n".join(
            filter(
                None,
                [
                    self.formatted_signature(),
                    *[cmd.script_str() for cmd in self.commands],
                ],
            )
        )

    @classmethod
    def parse(cls, text: str) -> "Script":
        """
        Parse a script from text, breaking it into paragraphs and converting each into
        either a BareComment or CommentedCommand.
        """
        # Split into paragraphs (2+ newlines).
        paragraphs = re.split(r"\n{2,}", text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        commands = []

        for para in paragraphs:
            # Split paragraph into lines.
            lines = para.split("\n")
            current_comment = None  # For accumulating comment lines

            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("#"):
                    # Line is a comment
                    comment_line = stripped_line.lstrip("#").strip()
                    if current_comment:
                        current_comment += "\n" + comment_line
                    else:
                        current_comment = comment_line
                elif stripped_line:
                    # Line is a command.
                    cmd = Command.from_command_str(stripped_line)
                    commands.append(CommentedCommand(comment=current_comment, command=cmd))
                    current_comment = None  # Reset after attaching to command.

            # If there's a comment with no command following it.
            if current_comment:
                commands.append(BareComment(text=current_comment))
                current_comment = None

        return cls(signature=None, commands=commands)
