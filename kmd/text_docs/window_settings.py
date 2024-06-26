from kmd.text_docs.sliding_transforms import WINDOW_BR_SEP, WindowSettings
from kmd.text_docs.text_doc import Unit

WINDOW_2K_WORDTOKS = WindowSettings(
    Unit.WORDTOKS, size=2048, shift=2048 - 256, min_overlap=8, separator=WINDOW_BR_SEP
)
"""
Sliding, overlapping word-based window. Useful for finding paragraph breaks.
2K wordtoks is several paragraphs.
"""

WINDOW_1_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=1, shift=1, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 1 paragraph at a time."""

WINDOW_2_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=2, shift=2, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 2 paragraphs at a time."""

WINDOW_4_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=4, shift=4, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 4 paragraph at a time."""

WINDOW_8_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=8, shift=8, min_overlap=0, separator=WINDOW_BR_SEP
)
"""Process 8 paragraphs at a time."""
