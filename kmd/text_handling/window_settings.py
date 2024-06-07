from kmd.text_handling.sliding_transforms import WINDOW_BR_SEP, WindowSettings
from kmd.text_handling.text_doc import Unit

# Sliding, overlapping word-based window. 2K wordtoks is several paragraphs.
WINDOW_2K_WORDTOKS = WindowSettings(
    Unit.WORDTOKS, size=2048, shift=2048 - 256, min_overlap=8, separator=WINDOW_BR_SEP
)

# Process one or a few paragraphs at a time.
WINDOW_1_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=1, shift=1, min_overlap=0, separator=WINDOW_BR_SEP
)

WINDOW_2_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=2, shift=2, min_overlap=0, separator=WINDOW_BR_SEP
)

WINDOW_4_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=4, shift=4, min_overlap=0, separator=WINDOW_BR_SEP
)

WINDOW_8_PARA = WindowSettings(
    Unit.PARAGRAPHS, size=8, shift=8, min_overlap=0, separator=WINDOW_BR_SEP
)
