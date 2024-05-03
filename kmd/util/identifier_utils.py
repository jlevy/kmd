"""Some tools for string identifiers.

Note we prefer base 36 as it's shorter and friendlier than base64 or
hex, and is case insensitive so suitable for filesystem use.
"""

# TODO: Consider moving these to strif lib, which has some other related tools.

import hashlib
import re

import regex

_NON_ALPHANUM_CHARS = re.compile("[^a-z0-9]+", re.IGNORECASE)


def clean_alphanum(string, max_length=128):
    """Convert a string to a clean, readable identifier that includes the
    (first) alphanumeric characters of the given string.

    This mapping is for readability only, and so can easily have
    collisions on different inputs.
    """
    return _NON_ALPHANUM_CHARS.sub("_", string)[:max_length]


def clean_alphanum_hash(string, max_length=128, max_hash_len=None):
    """Convert a string to a clean, readable identifier that includes the
    (first) alphanumeric characters of the given string.

    This includes a SHA1 hash so collisions are unlikely.
    """
    hash = hash_string_base36(string, algorithm="sha1")
    if max_hash_len:
        hash = hash[:max_hash_len]
    if max_length < len(hash) + 1:
        return hash
    else:
        return clean_alphanum(string, max_length=max_length - len(hash)) + "_" + hash


def base36_encode(n):
    """Base 36 encode an integer."""

    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    encoded = ""

    while n > 0:
        n, remainder = divmod(n, 36)
        encoded = chars[remainder] + encoded

    return encoded


def hash_string_base36(string, algorithm="sha1"):
    """Hash string and return in base 36, which is good for short, friendly
    identifiers."""

    h = hashlib.new(algorithm)
    h.update(string.encode("utf8"))
    return base36_encode(int.from_bytes(h.digest(), byteorder="big"))


def slugify_string(string):
    return regex.sub("[^a-z0-9]+", "-", string.lower())
