"""
Common elements within documents, used as HTML class names or attributes to structure text.
"""

# Grouping element class names:

ORIGINAL = "original"
"""Generic element representing an original text."""

RESULT = "result"
"""Generic result of a processing step."""

GROUP = "group"
"""Generic combination of elements."""

CHUNK = "chunk"
"""Use when chunking a document for processing."""

# Text blocks class names:

FULL_TEXT = "full-text"
DESCRIPTION = "description"
SUMMARY = "summary"

# Inline class name:

SPEAKER_LABEL = "speaker-label"
"""Inline class name for a speaker."""

CITATION = "citation"
"""Inline class name for a citation."""

TIMESTAMP_LINK = "timestamp-link"
"""Inline class name for a timestamp link."""


# Paragraph class names:

ANNOTATED_PARA = "annotated-para"
"""Paragraph with annotations."""

PARA = "para"
"""Original paragraph."""

PARA_CAPTION = "para-caption"
"""Caption for a paragraph."""

# Concepts class names:

CONCEPTS = "concepts"
"""A list of concepts."""

# Data attributes:

DATA_SOURCE_PATH = "data-src"
"""Path to a source file."""

DATA_TIMESTAMP = "data-timestamp"
"""Timestamp into an audio or video."""

DATA_SPEAKER_ID = "data-speaker-id"
"""Identifier for a speaker."""
