"""
Make docs and source code for kmd available to itself.
"""

from functools import cache
from pathlib import Path
from textwrap import dedent

from kmd.config.logger import get_logger
from kmd.docs.assemble_source_code import load_source_code, SourceCode
from kmd.util.lazyobject import lazyobject
from kmd.util.string_template import StringTemplate


log = get_logger(__name__)


def _load_help_src(path: str) -> str:
    if not path.endswith(".md"):
        path += ".md"
    base_dir = Path(__file__).parent
    topic_file = base_dir / path
    if not topic_file.exists():
        raise ValueError(f"Unknown doc: {topic_file}")

    return topic_file.read_text()


def _lazy_load(path: str):
    @lazyobject
    def content() -> str:
        return _load_help_src(path)

    return content


welcome = _lazy_load("markdown/welcome")
what_is_kmd = _lazy_load("markdown/topics/a1_what_is_kmd")
progress = _lazy_load("markdown/topics/a2_progress")
installation = _lazy_load("markdown/topics/a3_installation")
getting_started = _lazy_load("markdown/topics/a4_getting_started")
tips_for_use_with_other_tools = _lazy_load("markdown/topics/a5_tips_for_use_with_other_tools")
development = _lazy_load("markdown/topics/a6_development")

philosophy_of_kmd = _lazy_load("markdown/topics/b0_philosophy_of_kmd")
kmd_overview = _lazy_load("markdown/topics/b1_kmd_overview")
workspace_and_file_formats = _lazy_load("markdown/topics/b2_workspace_and_file_formats")
modern_shell_tool_recommendations = _lazy_load(
    "markdown/topics/b3_modern_shell_tool_recommendations"
)
faq = _lazy_load("markdown/topics/b4_faq")


@lazyobject
def source_code() -> SourceCode:
    return load_source_code()


@lazyobject
def api_docs() -> str:
    template_str = _load_help_src("markdown/api_docs_template")
    template_vars = list(source_code.__dict__.keys())
    template = StringTemplate(template_str, template_vars)
    return template.format(**source_code.__dict__)


structured_response_template = StringTemplate(
    dedent(
        """
        If a user asks a question, you may offer commentary, a direct answer, and suggested
        commands. Each one is optional.

        You will provide the answer in an AssistantResponse structure.
        Here is a description of how to structure your response, in the form of a Pydantic class
        with documentation on how to use each field:

        {assistant_response_model}

        DO NOT include scripts with shell commands in the `response_text` field.
        Use `suggested_commands` for this, so these commands are not duplicated.

        In response text field, you may mention shell commands within the text `back_ticks` like
        this.

        Within `suggested_commands`, you can return commands that can be used, which can be
        shell commands but usually for content-related tasks will be things like `strip_html` or
        `summarize_as_bullets`.

        In some cases if there is no action available, you can suggest Python code to the user,
        including writing new actions.
        Use the `python_code` field to hold all Python code.
        """
    ),
    ["assistant_response_model"],
)


@cache
def assistant_instructions(is_structured: bool) -> str:
    template = StringTemplate(
        _load_help_src("markdown/assistant_instructions_template"),
        ["structured_response_instructions"],
    )
    if is_structured:
        response_model_src = load_source_code().assistant_response_model_src
        structured_response_instructions = structured_response_template.format(
            assistant_response_model=response_model_src
        )
    else:
        structured_response_instructions = ""

    instructions = template.format(
        structured_response_instructions=structured_response_instructions
    )
    instructions_lines = len(instructions.strip().splitlines())

    structured_instructions_len = len(structured_response_instructions.strip().splitlines())
    log.info(
        "Loaded assistant instructions: %s lines, structured instructions: %s lines",
        instructions_lines,
        structured_instructions_len,
    )
    assert instructions_lines > 100 and (not is_structured or structured_instructions_len > 10)
    return instructions
