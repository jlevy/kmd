from textwrap import indent
from kmd.actions.registry import load_all_actions


def list_actions():
    """
    List all available actions.
    """

    print("\nAvailable kmd actions:\n")
    actions = load_all_actions()
    for action in actions.values():
        print(
            f"{action.name} - {action.friendly_name}:\n{indent(action.description, prefix="    ")}\n"
        )
