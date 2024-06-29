from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

custom_style = Style.from_dict(
    {
        # TODO: Styling.
        # "dialog": "bg:#1a1a1a #ddddde",
        # "dialog frame.label": "bg:#ec9384 #ddddde bold",
        # "dialog.body": "bg:#1a1a1a #ddddde",
        # "dialog shadow": "bg:#bbbbbb",
        # "dialog.body text-area": "bg:#1a1a1a #ddddde",
        # "dialog.body text-area.cursor": "bg:#ddddde #1a1a1a",
        # "dialog frame.button": "bg:#ec9384 #ddddde",
        # "dialog frame.button.focused": "bg:#6cc581 #1a1a1a bold",
    }
)


def prompt_simple_string(prompt_text: str):
    """
    Simple prompt from the user for a simple string.
    """
    session = PromptSession(style=custom_style)
    user_input = session.prompt(prompt_text)
    return user_input
