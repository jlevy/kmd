import json

from kmd.config.logger import get_logger
from kmd.errors import ApiResultError, InvalidInput
from kmd.exec.action_registry import kmd_action
from kmd.llms.fuzzy_parsing import fuzzy_parse_json
from kmd.llms.llm_completion import llm_template_completion
from kmd.model import Item, ItemType, LLM, Message, MessageTemplate, PerItemAction
from kmd.preconditions.precondition_defs import has_html_body, has_text_body
from kmd.preconditions.speaker_labels import find_speaker_labels
from kmd.text_formatting.html_in_md import html_speaker_id_span
from kmd.util.string_replace import replace_multiple

log = get_logger(__name__)


@kmd_action
class IdentifySpeakers(PerItemAction):
    def __init__(self):
        super().__init__(
            name="identify_speakers",
            description="Identify speakers in a transcript and replace placeholders with their names.",
            precondition=has_text_body | has_html_body,
        )

    def run_item(self, item: Item) -> Item:
        if not item.body:
            raise InvalidInput("Item must have a body")

        # Find all speaker labels and their offsets
        speaker_labels = find_speaker_labels(item.body)
        if not speaker_labels:
            log.warning("This document has no speaker labels! Skipping this action.")
            return item  # No changes needed.

        # Prepare the system message and template for LLM.
        system_message = Message("You are an assistant that identifies speakers in transcripts.")
        identification_template = MessageTemplate(
            """
            The transcript below includes speakers identified by IDs like 'SPEAKER 0' or 'SPEAKER 1'.
            Based on the transcript, provide a mapping from speaker IDs to actual speaker names.
            The mapping should be in JSON format like {{"0": "Alice", "1": "Bob"}}.
            If you are not sure from the content, leave the names as is, writing something like
            {{"0": "Alice", "1": "SPEAKER 1"}} or {{"0": "SPEAKER 0", "1": "SPEAKER 1"}}.
            Transcript:
            {body}
            """
        )

        # Perform LLM completion to get the speaker mapping.
        mapping_str = llm_template_completion(
            model=LLM.gpt_4o_mini,
            system_message=system_message,
            template=identification_template,
            input=item.body,
        )

        # Parse the mapping.
        try:
            speaker_mapping = fuzzy_parse_json(mapping_str)
            if not speaker_mapping:
                log.error("Could not parse speaker mapping: %s", mapping_str)
                raise ApiResultError("Could not parse speaker mapping")
            log.message("Identified speakers from transcript: %s", speaker_mapping)
        except json.JSONDecodeError as e:
            raise ApiResultError(f"Failed to parse speaker mapping from LLM output: {e}")

        # Prepare replacements.
        replacements = []
        for match in speaker_labels:
            speaker_id = match.attribute_value
            if not speaker_id:
                raise InvalidInput(f"Speaker id not found: {match}")
            new_speaker_name = speaker_mapping.get(speaker_id, f"SPEAKER {speaker_id}")
            # Prepare replacement text.
            new_span = html_speaker_id_span(f"**{new_speaker_name}:**", speaker_id)
            replacements.append((match.start_offset, match.end_offset, new_span))

        # Perform replacements.
        updated_body = replace_multiple(item.body, replacements)

        result_item = item.derived_copy(type=ItemType.doc, body=updated_body)
        return result_item
