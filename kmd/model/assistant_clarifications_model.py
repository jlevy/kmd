from typing import List

from pydantic import BaseModel, Field

from kmd.model.assistant_intents_model import BaseIntent, IntentClassification


class Question(BaseModel):
    """
    A question with a simple string answer, optionally from a set of choices.
    """

    question: str
    """
    The question to ask the user.
    """

    choices: List[str] = Field(default_factory=list)
    """
    The set of choices the user can select from, or empty if specific answers
    are not known.
    """


class Clarification(BaseModel):
    """
    A question along with the intent field that it fills in.
    """

    field: str
    """
    The name of the intent field that this question fills in.
    """

    question: Question
    """
    The question to ask the user.
    """


_CLARIFICATIONS = [
    Clarification(
        question=Question(
            question="What do you need help with?",
            choices=[intent.value for intent in IntentClassification],
        ),
        field="next_intent",
    ),
    Clarification(
        question=Question(
            question="Anything you can tell me about what you want to do?",
        ),
        field="next_intent_details",
    ),
    Clarification(
        question=Question(
            question="What files do you want to select?",
        ),
        field="selection_criteria",
    ),
    Clarification(
        question=Question(
            question="What do you want to do with the files?",
        ),
        field="processing_description",
    ),
]


def applicable_clarifications(intent: BaseIntent) -> List[Clarification]:
    """
    The set of clarification questions that are applicable to this intent,
    i.e. for fields that are empty or unset.
    """
    return [
        clarification
        for clarification in _CLARIFICATIONS
        if clarification.field in intent.unset_fields()
    ]
