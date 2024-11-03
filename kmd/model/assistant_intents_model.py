from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import Annotated, List, Literal, Optional, Type, Union

from pydantic import BaseModel, Field, TypeAdapter
from pydantic.dataclasses import dataclass

from kmd.model.assistant_commands_model import Command, SuggestedCommand
from kmd.model.items_model import ItemType
from kmd.shell.shell_output import fill_text, Wrap
from kmd.util.type_utils import not_none


class IntentClassification(Enum):
    """
    The type of intent for the assistant to help the user achieve.
    """

    elicit_goals = "ElicitGoal"
    select_files = "SelectFiles"
    process_files = "ProcessFiles"
    # local_system_task = "LocalSystemTask"
    # download_content = "DownloadContent"
    # research = "Research"
    general_conversation = "GeneralConversation"
    something_else = "SomethingElse"


class InfoRequest(BaseModel):
    """
    Information that is needed to complete the user's intent.
    """

    description: str
    """
    A description of the information that is needed.
    """


@dataclass
class FileInput:
    """
    A file input to a processing step. We always need a description of the input
    and we can fill in the value once we know it.
    """

    file_needed: InfoRequest

    path: Optional[Path] = None
    """
    The path to the input file, if known.
    """


@dataclass
class FileOutput:
    """
    An output from a processing step. We always need a description of the output
    and we can fill in a suggested name if known.
    """

    description: str
    """A simple description of the output."""

    suggested_name: Optional[str] = None
    """A suggested name for the output, if known, such as the initial part of the filename."""

    item_type: Optional[ItemType] = None
    """The expected type of item that is the output."""


class BaseIntent(BaseModel):
    """
    Base class for all intents. An intent is something it appears the
    user wants to do, and may need help from the assistant to achieve.
    """

    intent_type: str  # Discriminator field, but no special Field annotation here.

    def intent_fields(self) -> set[str]:
        return self.model_fields_set - {"intent_type"}

    def unset_fields(self) -> List[str]:
        return sorted(field for field in self.intent_fields() if not getattr(self, field))

    def description_str(self) -> str:
        return fill_text(
            f"""{self.intent_type}: {dedent(self.__doc__ or "(no description)").strip()}""",
            text_wrap=Wrap.WRAP_FULL,
        )

    def full_str(self) -> str:
        return f"{self.intent_type}: " + "\n".join(
            f"{field}: {getattr(self, field)}" for field in self.intent_fields()
        )


class GeneralConversation(BaseIntent):
    """
    A general conversational intent where the user just seems to want to
    chat or be friendly but has no other goal yet.
    """

    intent_type: Literal["Conversation"] = "Conversation"

    facts: List[str] = Field(default_factory=list)
    """
    Specific facts that the user mentioned that the assistant should remember.
    Each should be about once sentence long, such as "The user's name is Ferdinand"
    or "The user likes to write in Python" or "The user is building a tool called Kmd".
    """


class ElicitGoal(BaseIntent):
    """
    Elicit from the user what they want to do.
    This should be the initial intent if the user asks for help doing anything
    and no more specific intent is known.
    """

    intent_type: Literal["ElicitGoal"] = "ElicitGoal"

    next_intent: Optional[IntentClassification] = None
    """
    The next intent the user desires.
    """

    next_intent_details: Optional[str] = None
    """
    A more detailed description of the goal, if available.
    """


class SelectFiles(BaseIntent):
    """
    Search or find and select files that match a description. There is a human-readable
    description of the selection criteria, and if known, the commands to execute to
    select the files.
    """

    intent_type: Literal["SelectFiles"] = "SelectFiles"

    selection_criteria: Optional[str] = None
    """
    A human-readable description of the selection criteria.
    """

    selection_commands: List[SuggestedCommand] = Field(default_factory=list)
    """
    Commands to execute to find and select the files.
    """


class ProcessFiles(BaseIntent):
    """
    Process files with required inputs and desired output.
    """

    intent_type: Literal["ProcessFiles"] = "ProcessFiles"

    processing_description: Optional[str] = None
    """
    A human-readable description of the processing to be done.
    """

    required_inputs: List[FileInput] = Field(default_factory=list)

    desired_output: Optional[FileOutput] = None


class SomethingElse(BaseIntent):
    """
    A catch-all for any other intent that doesn't fit the above.
    """

    intent_type: Literal["SomethingElse"] = "SomethingElse"

    intent_description: Optional[str] = None
    """
    A description of what the user wanted to do, if available.
    """


_INTENT_CLASSES = [ElicitGoal, SelectFiles, ProcessFiles, GeneralConversation, SomethingElse]


IntentUnion = Union[ElicitGoal, SelectFiles, ProcessFiles, GeneralConversation, SomethingElse]

AnnotatedIntent = Annotated[
    # XXX Have to list these explicitly instead of via get_all_intents() to keep typing working?
    IntentUnion,
    Field(discriminator="intent_type"),
]
"""
The annotated union type for all intent types.
"""


def get_intents_enum() -> Type[Enum]:
    """
    Dynamically create an Enum class with all registered intent types.
    """
    return type("IntentTypes", (Enum,), {name: name for name in _INTENT_CLASSES})


## Tests


def test_intents():
    intent1 = ProcessFiles(
        required_inputs=[
            FileInput(file_needed=InfoRequest(description="some thing")),
            FileInput(file_needed=InfoRequest(description="another thing")),
        ],
        desired_output=FileOutput(description="output", suggested_name="outfile"),
    )
    serialized_intent1 = intent1.model_dump()
    print("Serialized intent1:", serialized_intent1)

    adapter = TypeAdapter(AnnotatedIntent)
    deserialized_intent1 = adapter.validate_python(serialized_intent1)
    print("Deserialized intent1:", deserialized_intent1)
    print("Type:", type(deserialized_intent1))

    assert isinstance(deserialized_intent1, ProcessFiles)
    assert len(deserialized_intent1.required_inputs) == 2
    assert deserialized_intent1.required_inputs[0].file_needed.description == "some thing"
    assert not_none(deserialized_intent1.desired_output).description == "output"

    intent2 = SelectFiles(
        selection_criteria="Select all .txt files",
        selection_commands=[
            SuggestedCommand(
                comment="Find all .txt files",
                command=Command(name="find", args=["."], options=["-name", "*.txt"]),
            )
        ],
    )
    serialized_intent2 = intent2.model_dump()
    print("\nSerialized intent2:", serialized_intent2)

    deserialized_intent2 = adapter.validate_python(serialized_intent2)
    print("Deserialized intent2:", deserialized_intent2)
    print("Type:", type(deserialized_intent2))

    assert isinstance(deserialized_intent2, SelectFiles)
    assert deserialized_intent2.selection_criteria == "Select all .txt files"
    assert len(deserialized_intent2.selection_commands) == 1
    assert deserialized_intent2.selection_commands[0].command.name == "find"
    assert "*.txt" in deserialized_intent2.selection_commands[0].command.options
