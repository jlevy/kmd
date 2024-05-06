from typing import Set
from typing import NamedTuple


class Key(NamedTuple):
    name: str
    group: str


class Uniquifier:
    """
    Maintain a set of unique names, adding suffixes to ensure uniqueness when needed.
    """

    def __init__(self, init_values: Set[Key] = set(), template: str = "{name}_{suffix}"):
        if "{name}" not in template or "{suffix}" not in template:
            raise ValueError(f"Template must contain placeholders for name and suffix: {template}")

        self.keys: Set[Key] = set()
        self.template = template

        if init_values:
            self.keys.update(init_values)

    def uniquify(self, name: str, group: str = "") -> str:
        """
        Return a name that is the same as the input whenever possible, or with a numeric suffix
        added to ensure uniqueness among all names seen so far. If group is provided, it will only
        ensure uniqueness within that group.
        """

        if Key(name, group) not in self.keys:
            self.keys.add(Key(name, group))
            return name

        suffix = 1
        while Key(self.template.format(name=name, suffix=suffix), group) in self.keys:
            suffix += 1

        unique_name = self.template.format(name=name, suffix=suffix)
        self.keys.add(Key(unique_name, group))

        return unique_name

    def __len__(self) -> int:
        return len(self.keys)


def test_uniquifier():
    uniquifier = Uniquifier()

    # Uniqueness within the same group.
    assert uniquifier.uniquify("foo") == "foo"
    assert uniquifier.uniquify("foo") == "foo_1"
    assert uniquifier.uniquify("foo") == "foo_2"

    # Uniqueness across different groups.
    assert uniquifier.uniquify("foo", "group1") == "foo"
    assert uniquifier.uniquify("foo", "group2") == "foo"

    # Uniqueness within the same group after adding a new group.
    assert uniquifier.uniquify("foo", "group1") == "foo_1"

    # Test length of uniquifier.
    assert len(uniquifier) == 6


if __name__ == "__main__":
    test_uniquifier()
