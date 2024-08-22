"""
Common elements within documents, used as HTML class names or attributes to structure text.
"""

# Grouping elements:
ORIGINAL = "original"
"""Generic element representing an original text."""

RESULT = "result"
"""Generic result of a processing step."""

GROUP = "group"
"""Generic combination of elements."""

CHUNK = "chunk"
"""Use when chunking a document for processing."""

# Text blocks:

FULL_TEXT = "full-text"
DESCRIPTION = "description"
SUMMARY = "summary"

# Inline annotations:

SPEAKER_LABEL = "speaker-label"
"""Inline annotation for a speaker."""

CITATION = "citation"
"""Inline annotation for a citation."""

# Paragraphs:

ANNOTATED_PARA = "annotated-para"
"""Paragraph with annotations."""

PARA = "para"
"""Original paragraph."""

PARA_CAPTION = "para-caption"
"""Caption for a paragraph."""

# Concepts:

CONCEPTS = "concepts"
"""A list of concepts."""

# Data attributes:

DATA_TIMESTAMP = "data-timestamp"
DATA_SPEAKER_ID = "data-speaker-id"
