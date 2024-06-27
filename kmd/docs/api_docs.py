from kmd.docs.assemble_source_code import model_src, base_action_defs_src, text_tool_src

__doc__: str = f"""
KMD ITEM AND ACTION MODEL

Here is the kmd source code representing the data model of Python classes for
items and actions:

{model_src}


EXAMPLES OF KMD ACTION DEFINITIONS

For context and in case you need to write new actions, we also give you some of the kmd source code
for actions, to give examples of how actions are written in Python. You can use as examples of how
to define new actions if the existing functionality of current kmd actions is insufficient:

{base_action_defs_src}


LIBRARY OF LANGUAGE AND FORMATTING TOOLS

When writing any Python code, use the following tools whenever possible for formatting HTML
and Markdown and processing text.

- When segmenting text into sentences, use `split_sentences_fast()`.

- When processing text documents and navigating paragraphs or sentences, use `TextDoc.from_text()`.

{text_tool_src}
"""
