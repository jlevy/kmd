from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class StringTemplate:
    """
    A validated template string that supports only specified fields.
    Can subclass to have a type with a given set of `allowed_fields`.
    """

    template: str
    allowed_fields: List[str] = field(default_factory=lambda: ["title"])

    def __post_init__(self):
        if not isinstance(self.template, str):
            raise ValueError("Template must be a string")
        # Confirm only the allowed fields are in the template.
        try:
            placeholder_values = {field: "placeholder" for field in self.allowed_fields}
            self.template.format(**placeholder_values)
        except KeyError as e:
            raise ValueError(f"Template contains unsupported variable: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid template format: {e}")

    def format(self, **kwargs: str) -> str:
        unexpected_keys = set(kwargs.keys()) - set(self.allowed_fields)
        if unexpected_keys:
            raise ValueError(f"Unexpected keyword arguments: {', '.join(unexpected_keys)}")
        return self.template.format(**kwargs)
