"""Screenshot capture utilities."""

import base64
import subprocess
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


class Screenshot:
    """Screenshot data container."""

    def __init__(
        self,
        base64_data: str,
        width: int,
        height: int,
        format: str = "png"
    ):
        """
        Initialize Screenshot.

        Args:
            base64_data: Base64 encoded image data
            width: Image width in pixels
            height: Image height in pixels
            format: Image format ('png' or 'jpeg')
        """
        self.base64_data = base64_data
        self.width = width
        self.height = height
        self.format = format

    def to_data_url(self) -> str:
        """Convert to data URL for embedding in HTML/messages."""
        return f"data:image/{self.format};base64,{self.base64_data}"

    def save(self, path: str | Path) -> None:
        """Save screenshot to file."""
        data = base64.b64decode(self.base64_data)
        with open(path, "wb") as f:
            f.write(data)

    @classmethod
    def from_file(cls, path: str | Path) -> "Screenshot":
        """Load screenshot from file."""
        from PIL import Image

        with open(path, "rb") as f:
            data = f.read()

        img = Image.open(path)
        width, height = img.size

        # Detect format
        fmt = "png"
        if data[:2] == b"\xff\xd8":
            fmt = "jpeg"

        return cls(
            base64_data=base64.b64encode(data).decode("utf-8"),
            width=width,
            height=height,
            format=fmt
        )

    def resize(self, max_size: int = 1024) -> "Screenshot":
        """
        Resize screenshot if larger than max_size.

        Args:
            max_size: Maximum dimension (width or height)

        Returns:
            Resized screenshot (or self if no resize needed)
        """
        from PIL import Image
        import io

        if max(self.width, self.height) <= max_size:
            return self

        # Decode image
        data = base64.b64decode(self.base64_data)
        img = Image.open(io.BytesIO(data))

        # Calculate new size
        ratio = max_size / max(self.width, self.height)
        new_width = int(self.width * ratio)
        new_height = int(self.height * ratio)

        # Resize
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Encode back
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        new_data = buffer.getvalue()

        return Screenshot(
            base64_data=base64.b64encode(new_data).decode("utf-8"),
            width=new_width,
            height=new_height,
            format="jpeg"
        )


def take_screenshot(device_id: str | None = None) -> Screenshot:
    """
    Take screenshot using ADB.

    Args:
        device_id: ADB device ID (optional)

    Returns:
        Screenshot object
    """
    adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name

    try:
        # Capture screenshot
        remote_path = "/sdcard/screenshot_temp.png"
        capture_cmd = f"{adb_prefix} shell screencap -p {remote_path}"
        pull_cmd = f"{adb_prefix} pull {remote_path} {temp_path}"
        cleanup_cmd = f"{adb_prefix} shell rm {remote_path}"

        # Execute commands
        subprocess.run(capture_cmd, shell=True, check=True, capture_output=True)
        subprocess.run(pull_cmd, shell=True, check=True, capture_output=True)
        subprocess.run(cleanup_cmd, shell=True, capture_output=True)

        # Load and return
        return Screenshot.from_file(temp_path)

    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_current_app(device_id: str | None = None) -> dict[str, str]:
    """
    Get current foreground app info.

    Returns:
        Dict with 'package' and 'activity' keys
    """
    adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    cmd = f"{adb_prefix} shell dumpsys activity activities | grep mResumedActivity"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        output = result.stdout.strip()

        # Parse output like: mResumedActivity: ActivityRecord{xxx com.example.app/.MainActivity ...}
        if "mResumedActivity" in output and "/" in output:
            parts = output.split()
            for part in parts:
                if "/" in part and "." in part:
                    # Found component name
                    component = part.rstrip("}")
                    if "/" in component:
                        package, activity = component.split("/", 1)
                        return {"package": package, "activity": activity}

        return {"package": "unknown", "activity": "unknown"}

    except Exception:
        return {"package": "unknown", "activity": "unknown"}


def get_screen_orientation(device_id: str | None = None) -> int:
    """
    Get screen orientation.

    Returns:
        0: Portrait
        1: Landscape (rotated left)
        2: Portrait (upside down)
        3: Landscape (rotated right)
    """
    adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    cmd = f'{adb_prefix} shell dumpsys input | grep -m 1 "orientation="'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        output = result.stdout.strip()

        # Parse orientation
        import re
        match = re.search(r"orientation=(\d)", output)
        if match:
            return int(match.group(1))

    except Exception:
        pass

    return 0


def is_screen_on(device_id: str | None = None) -> bool:
    """Check if screen is on."""
    adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    cmd = f"{adb_prefix} shell dumpsys power | grep 'Display Power'"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return "state=ON" in result.stdout
    except Exception:
        return True  # Assume on if can't detect


def wake_screen(device_id: str | None = None) -> None:
    """Wake up screen if off."""
    adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    if not is_screen_on(device_id):
        # Press power button
        subprocess.run(f"{adb_prefix} shell input keyevent 26", shell=True, capture_output=True)
        # Swipe up to unlock (if needed)
        subprocess.run(f"{adb_prefix} shell input swipe 500 1000 500 300", shell=True, capture_output=True)


# Alias for backward compatibility with phone_agent.adb.screenshot
get_screenshot = take_screenshot
