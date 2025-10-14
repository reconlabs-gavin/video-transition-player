import numpy as np
from typing import Optional


class SlideTransition:
    """
    Vertical slide transition similar to short-form apps.

    Usage contract:
    - render(frame1, frame2, progress, direction='down') -> np.ndarray
      where:
        frame1: current frame (H, W, 3) uint8
        frame2: next frame (same shape)
        progress: float in [0, 1]
        direction: 'down' (default) or 'up'
    """

    def __init__(self, direction: str = 'down') -> None:
        self.direction = direction

    def render(self, frame1, frame2, progress: float, direction: Optional[str] = None, **_):
        h, w = frame1.shape[:2]

        # Clamp progress for safety
        p = float(max(0.0, min(1.0, progress)))
        offset = int(h * p)
        result = np.zeros_like(frame1)

        dir_eff = (direction or self.direction).lower()
        if dir_eff == 'down':
            # current goes up
            if offset < h:
                result[0:h - offset] = frame1[offset:h]
            # next comes from bottom
            if offset > 0:
                result[h - offset:h] = frame2[0:offset]
        else:  # 'up'
            # current goes down
            if offset < h:
                result[offset:h] = frame1[0:h - offset]
            # next comes from top
            if offset > 0:
                result[0:offset] = frame2[h - offset:h]

        return result