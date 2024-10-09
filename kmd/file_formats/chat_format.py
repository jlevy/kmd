"""
YAML chat format is a simple file format for chat messages or commands that's just
YAML blocks separated by the usual YAML `---` separator, with a few conventions.

This format can represent data like OpenAI JSON chat history as well as any other
kind of command or message but has a few benefits:

- It's more readable and editable than JSON.

- Multiline strings are easy to read and edit if `|`-style literals
  are used for the content:
  https://yaml.org/spec/1.2.2/#812-literal-style

- New chat messages can be appended to a file easily.

Rules:

- The content is valid YAML blocks with standard `---` separators.

- An initial `---` is required (to make file type detection easier).

- Any YAML is valid in a block, as long as it contains `message_type`
  and `content` string fields.

- It's recommended but not required that `message_type` be one of the
  following: "system", "user", "assistant", "command", "output", or "template".

Note this is the same as any YAML frontmatter, but the `message_type`
field indicates the file is in chat format.

Chat example:

```
---
message_type: system
content: |
  You are a helpful assistant.
---
message_type: user
content: |
  Hello, how are you?
---
message_type: assistant
content: |
  I'm fine, thank you!
```

Command example:
```
---
message_type: command
content: |
  transcribe_video
---
message_type: output
content: |
  The video has been transcribed.
output_file: /path/to/video.txt
```

Template example:
```
---
message_type: template
template_vars: ["name", "body"]
content: |
  Hello, {name}! Here is your message:
  {body}
---
```

"""

from dataclasses import field
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

from pydantic.dataclasses import dataclass

from kmd.file_formats.yaml_util import custom_key_sort, from_yaml_string, new_yaml, to_yaml_string
from kmd.util.obj_utils import abbreviate_obj


class ChatType(str, Enum):
    """
    The type of message in a chat. Represents the "role" in LLM APIs but can also represent
    other types of messages, such as commands or output.
    """

    system = "system"
    user = "user"
    assistant = "assistant"
    command = "command"
    output = "output"
    template = "template"


_custom_key_sort = custom_key_sort(["message_type", "content"])


@dataclass
class ChatMessage:
    message_type: ChatType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, message_dict: Dict[str, Any]) -> "ChatMessage":
        try:
            message_type_str = message_dict.pop("message_type")
            if isinstance(message_type_str, str):
                message_type = ChatType(message_type_str)
            else:
                message_type = message_type_str
            content = message_dict.pop("content")
            metadata = message_dict

            return cls(message_type=message_type, content=content, metadata=metadata)
        except LookupError as e:
            raise ValueError("Could not parse chat message") from e

    def as_dict(self) -> Dict[str, Any]:
        data = {
            "message_type": (
                self.message_type.value
                if isinstance(self.message_type, Enum)
                else self.message_type
            ),
            "content": self.content,
        }
        data.update(self.metadata)
        return data

    @classmethod
    def from_yaml(cls, yaml_string: str) -> "ChatMessage":
        return cls.from_dict(from_yaml_string(yaml_string))

    def as_chat_completion(self) -> Dict[str, str]:
        return {
            "role": self.message_type.value,
            "content": self.content,
        }

    def to_yaml(self) -> str:
        return to_yaml_string(self.as_dict(), key_sort=_custom_key_sort)

    def as_str(self) -> str:
        return self.to_yaml()

    def as_str_brief(self) -> str:
        return abbreviate_obj(self)

    def __str__(self) -> str:
        return self.as_str_brief()


def append_message(path: Path | str, message: ChatMessage, make_parents: bool = True) -> None:
    """
    Append a chat message to a YAML file.
    """
    path = Path(path)
    if make_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write("---\n")
        file.write(message.to_yaml())
        file.write("\n")


@dataclass
class ChatHistory:
    messages: List[ChatMessage] = field(default_factory=list)

    def append(self, message: ChatMessage) -> None:
        self.messages.append(message)

    @classmethod
    def from_yaml(cls, yaml_string: str) -> "ChatHistory":
        yaml = new_yaml()
        message_dicts = yaml.load_all(yaml_string)
        messages = [
            ChatMessage.from_dict(message_dict) for message_dict in message_dicts if message_dict
        ]
        return cls(messages=messages)

    def as_chat_completion(self) -> List[Dict[str, str]]:
        return [message.as_chat_completion() for message in self.messages]

    def to_yaml(self) -> str:
        yaml = new_yaml(key_sort=_custom_key_sort)
        stream = StringIO()
        # Include the extra `---` at the front for consistency and to make this file identifiable.
        stream.write("---\n")
        yaml.dump_all([message.as_dict() for message in self.messages], stream)
        return stream.getvalue()

    def as_str(self) -> str:
        return self.to_yaml()

    def as_str_brief(self) -> str:
        return abbreviate_obj(self)

    def __str__(self) -> str:
        return self.as_str_brief()


## Tests


def test_chat_history_serialization():
    from textwrap import dedent

    yaml_input = dedent(
        """
        message_type: system
        content: |
          You are a helpful assistant.
        ---
        message_type: user
        content: |
          Hello, how are you?
        ---
        message_type: assistant
        content: |
          I'm fine, thank you!
        mood: happy
        ---
        message_type: command
        content: |
          transcribe_video
        ---
        message_type: output
        content: |
          The video has been transcribed.
        output_file: /path/to/video.txt
        ---
        message_type: template
        template_vars: ["name", "body"]
        content: |
          Hello, {name}! Here is your message:
          {body}
        """
    ).lstrip()

    chat_history = ChatHistory.from_yaml(yaml_input)
    yaml_output = chat_history.to_yaml()

    print("\nSerialized YAML output:")
    print(yaml_output)

    print("\nFirst message:")
    print(repr(chat_history.messages[0]))

    assert chat_history.messages[0] == ChatMessage(
        message_type=ChatType.system, content="You are a helpful assistant.\n", metadata={}
    )

    for message in chat_history.messages:
        assert isinstance(message.message_type, ChatType)

    # Tolerate no initial `---` or an extra final `---`.
    assert chat_history == ChatHistory.from_yaml(yaml_output)
    assert chat_history == ChatHistory.from_yaml("---\n" + yaml_input + "\n---\n")

    test_dict = {
        "message_type": "user",
        "content": "Testing message_type as string.",
    }
    message_from_string = ChatMessage.from_dict(test_dict)
    assert message_from_string.message_type == ChatType.user

    test_dict_enum = {
        "message_type": ChatType.assistant,
        "content": "Testing message_type as Enum.",
    }
    message_from_enum = ChatMessage.from_dict(test_dict_enum)
    assert message_from_enum.message_type == ChatType.assistant

    # Confirm we use multi-line literals.
    test_long_message = ChatMessage(
        message_type=ChatType.system,
        content="\n".join(["line " + str(i) for i in range(10)]),
    )
    print("test_long_message", test_long_message.to_yaml())
    yaml = test_long_message.to_yaml()
    assert len(yaml.splitlines()) > 10
    assert "content: |" in yaml
