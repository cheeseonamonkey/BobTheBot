import mss
import numpy as np
import cv2

class ColorMasks:
    # HSV Ranges for typical RuneLite overlays
    MAGENTA = (np.array([145, 100, 100]), np.array([155, 255, 255]))
    CYAN = (np.array([85, 100, 100]), np.array([95, 255, 255]))
    YELLOW = (np.array([25, 100, 100]), np.array([35, 255, 255]))
    GREEN = (np.array([55, 100, 100]), np.array([65, 255, 255]))

class OSBCVision:
    def __init__(self, display=":99", region=None):
        self.display = display
        self.sct = mss.mss()
        # Default OSRS client region or full screen
        self.region = region or {"top": 0, "left": 0, "width": 1024, "height": 768}

    def capture(self):
        """Capture the current screen region as a NumPy array (BGR)."""
        screenshot = self.sct.grab(self.region)
        return np.array(screenshot)[:, :, :3]  # Remove alpha channel

    def detect_color(self, img, color_range):
        """Find contours of a specific color in the image."""
        lower, upper = color_range
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours

    def get_center(self, contour):
        """Get the center (x, y) of a contour."""
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return None
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        return (cX + self.region["left"], cY + self.region["top"])

    def find_largest(self, contours):
        """Return the largest contour by area."""
        if not contours:
            return None
        return max(contours, key=cv2.contourArea)
