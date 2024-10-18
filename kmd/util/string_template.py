from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple, Type, Union


@dataclass(frozen=True)
class StringTemplate:
    """
    A validated template string that supports only specified fields.
    Can subclass to have a type with a given set of `allowed_fields`.
    Provide a type with a field name to allow validation of int/float format strings.

    Examples:
    >>> t = StringTemplate("{name} is {age} years old", ["name", "age"])
    >>> t.format(name="Alice", age=30)
    'Alice is 30 years old'

    >>> t = StringTemplate("{count:3d}@{price:.2f}", [("count", int), ("price", float)])
    >>> t.format(count=10, price=19.99)
    ' 10@19.99'
    """

    template: str

    allowed_fields: Sequence[Union[str, Tuple[str, Optional[Type]]]] = field(
        default_factory=lambda: ["title"]
    )
    """List of allowed field names. If `d` or `f` formats are used, give tuple with the type."""

    strict: bool = False
    """If True, raise a ValueError if the template is missing an allowed field."""

    def __post_init__(self):
        if not isinstance(self.template, str):
            raise ValueError("Template must be a string")

        # Confirm only the allowed fields are in the template.
        field_types = self._field_types()
        try:
            placeholder_values = {field: (type or str)(123) for field, type in field_types.items()}
            self.template.format(**placeholder_values)
        except KeyError as e:
            raise ValueError(f"Template contains unsupported variable: {e}")
        except ValueError as e:
            raise ValueError(
                f"Invalid template (forgot to provide a type when using non-str format strings?): {e}"
            )

    def _field_types(self) -> Dict[str, Optional[Type]]:
        return {
            field[0] if isinstance(field, tuple) else field: (
                field[1] if isinstance(field, tuple) else None
            )
            for field in self.allowed_fields
        }

    def format(self, **kwargs: Any) -> str:
        field_types = self._field_types()
        allowed_keys = field_types.keys()
        unexpected_keys = set(kwargs.keys()) - allowed_keys
        if self.strict and unexpected_keys:
            raise ValueError(f"Unexpected keyword arguments: {', '.join(unexpected_keys)}")

        # Type check the values, if types were provided.
        for f, expected_type in field_types.items():
            if f in kwargs and expected_type:
                if not isinstance(kwargs[f], expected_type):
                    raise ValueError(
                        f"Invalid type for '{f}': expected {expected_type.__name__} but got {repr(kwargs[f])} ({type(kwargs[f]).__name__})"
                    )

        return self.template.format(**kwargs)


## Tests


def test_string_template():
    t = StringTemplate("{name} is {age} years old", ["name", "age"])
    assert t.format(name="Alice", age=30) == "Alice is 30 years old"

    t = StringTemplate("{count:3d}@{price:.2f}", [("count", int), ("price", float)])
    assert t.format(count=10, price=19.99) == " 10@19.99"

    try:
        StringTemplate("{name} {age}", ["name"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Template contains unsupported variable: 'age'" in str(e)

    t = StringTemplate("{count:d}", [("count", int)])
    try:
        t.format(count="not an int")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid type for 'count': expected int but got 'not an int' (str)" in str(e)
