from pathlib import Path
from typing import List

import cv2
import numpy as np


def frames_are_similar(frame1: np.ndarray, frame2: np.ndarray, threshold: float = 0.95) -> bool:
    """
    Compare two frames to determine if they are similar based on structural similarity.
    Returns True if frames are similar above the threshold.
    """
    from skimage.metrics import structural_similarity

    # Convert frames to grayscale and compute structural similarity.
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    score, _ = structural_similarity(gray1, gray2, full=True)

    return score > threshold


def filter_similar_frames(frame_paths: List[Path], threshold: float = 0.95) -> List[int]:
    """
    Take a list of frame paths and return indices of unique frames,
    where each is sufficiently different from its predecessor.
    """
    if not frame_paths:
        return []

    unique_indices = [0]  # Always keep first frame

    for i in range(1, len(frame_paths)):
        curr_frame = cv2.imread(str(frame_paths[i]))
        prev_frame = cv2.imread(str(frame_paths[i - 1]))

        if not frames_are_similar(curr_frame, prev_frame, threshold):
            unique_indices.append(i)

    return unique_indices
