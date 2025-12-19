"""
Bitfocus Companion HTTP API Integration

Provides integration with Bitfocus Companion for triggering buttons,
syncing state, and sharing preset information with Stream Deck.

Based on Companion v3+ API:
- Button press: /api/location/{page}/{row}/{column}/press
- Legacy API: /press/bank/{page}/{button}
- Button state: /api/location/{page}/{row}/{column}/style
"""
import requests
import json
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


class CompanionControlMode(Enum):
    """Control mode for camera operations"""
    DIRECT = "direct"  # Direct HTTP to camera (fastest)
    COMPANION = "companion"  # Via Companion module (for Stream Deck sync)
    HYBRID = "hybrid"  # Direct with Companion sync (recommended)


@dataclass
class CompanionButton:
    """Represents a Companion button location"""
    page: int
    row: int
    column: int

    @property
    def legacy_bank(self) -> int:
        """Calculate legacy bank number from row/column"""
        # Assuming 8 columns per row (Stream Deck XL layout)
        return (self.row - 1) * 8 + self.column

    def to_location_str(self) -> str:
        """Convert to location string format"""
        return f"{self.page}/{self.row}/{self.column}"


class CompanionAPI:
    """
    Bitfocus Companion HTTP API client.

    Provides methods to:
    - Trigger button presses
    - Query button states
    - Update button text/colors
    - Check Companion availability
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize Companion API client.

        Args:
            base_url: Companion web interface URL (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self._available = False
        self._version = None

        # Check availability on init
        self.check_availability()

    def check_availability(self) -> bool:
        """
        Check if Companion is available and responsive.

        Returns:
            True if Companion is running and accessible
        """
        try:
            response = requests.get(f"{self.base_url}/", timeout=2.0)
            self._available = response.status_code == 200
            return self._available
        except requests.exceptions.RequestException:
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        """Check if Companion is available"""
        return self._available

    def press_button(self, button: CompanionButton, use_legacy: bool = False) -> bool:
        """
        Trigger a button press in Companion.

        Args:
            button: Button location to press
            use_legacy: Use legacy API format (/press/bank) instead of new format

        Returns:
            True if button press was successful
        """
        try:
            if use_legacy:
                # Legacy format: /press/bank/{page}/{button}
                url = f"{self.base_url}/press/bank/{button.page}/{button.legacy_bank}"
            else:
                # New format: /api/location/{page}/{row}/{column}/press
                url = f"{self.base_url}/api/location/{button.to_location_str()}/press"

            response = requests.post(url, timeout=1.0)
            return response.status_code in (200, 204)
        except requests.exceptions.RequestException as e:
            print(f"Companion button press failed: {e}")
            return False

    def press_button_by_coords(self, page: int, row: int, column: int,
                              use_legacy: bool = False) -> bool:
        """
        Trigger a button press by page/row/column coordinates.

        Args:
            page: Page number (1-based)
            row: Row number (1-based)
            column: Column number (1-based)
            use_legacy: Use legacy API format

        Returns:
            True if button press was successful
        """
        button = CompanionButton(page=page, row=row, column=column)
        return self.press_button(button, use_legacy=use_legacy)

    def press_button_legacy(self, page: int, bank: int) -> bool:
        """
        Trigger a button press using legacy bank numbering.

        Args:
            page: Page number (1-based)
            bank: Bank number (1-based, sequential button index)

        Returns:
            True if button press was successful
        """
        try:
            url = f"{self.base_url}/press/bank/{page}/{bank}"
            response = requests.post(url, timeout=1.0)
            return response.status_code in (200, 204)
        except requests.exceptions.RequestException as e:
            print(f"Companion button press (legacy) failed: {e}")
            return False

    def get_button_style(self, button: CompanionButton) -> Optional[Dict[str, Any]]:
        """
        Get button style/state from Companion.

        Args:
            button: Button location

        Returns:
            Dict with button style info (text, color, bgcolor, etc.) or None
        """
        try:
            url = f"{self.base_url}/api/location/{button.to_location_str()}/style"
            response = requests.get(url, timeout=1.0)

            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException:
            return None

    def set_button_text(self, button: CompanionButton, text: str) -> bool:
        """
        Update button text in Companion.

        Note: This may require Companion v3.1+ and proper permissions.

        Args:
            button: Button location
            text: New button text

        Returns:
            True if update was successful
        """
        try:
            url = f"{self.base_url}/api/location/{button.to_location_str()}/style"
            payload = {"text": text}
            response = requests.post(url, json=payload, timeout=1.0)
            return response.status_code in (200, 204)
        except requests.exceptions.RequestException:
            return False

    def trigger_preset_recall(self, page: int, preset_num: int) -> bool:
        """
        Trigger a preset recall via Companion button.

        This assumes you have Companion buttons configured for preset recalls.
        Default mapping: Presets 1-10 on buttons 1-10 of specified page.

        Args:
            page: Companion page number
            preset_num: Preset number (1-based)

        Returns:
            True if trigger was successful
        """
        # Assuming preset buttons are in sequential order
        # This is a convention - adjust based on your Companion layout
        return self.press_button_legacy(page=page, bank=preset_num)

    def send_custom_request(self, endpoint: str, method: str = "GET",
                           data: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Send custom request to Companion API.

        Args:
            endpoint: API endpoint (e.g., "/api/custom/action")
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Optional JSON data for request

        Returns:
            Response object or None if failed
        """
        try:
            url = f"{self.base_url}{endpoint}"

            if method.upper() == "GET":
                response = requests.get(url, timeout=2.0)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=2.0)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=2.0)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=2.0)
            else:
                return None

            return response
        except requests.exceptions.RequestException:
            return None


class HybridCameraControl:
    """
    Hybrid camera control that uses both direct HTTP and Companion API.

    Control flow:
    1. Send command directly to camera (fast)
    2. Optionally trigger corresponding Companion button (for Stream Deck sync)
    3. Fall back to Companion if direct control fails
    """

    def __init__(self, camera_http_sender: Callable, companion_api: CompanionAPI,
                 mode: CompanionControlMode = CompanionControlMode.HYBRID,
                 companion_page: int = 1):
        """
        Initialize hybrid control.

        Args:
            camera_http_sender: Function to send HTTP commands to camera
            companion_api: CompanionAPI instance
            mode: Control mode (direct, companion, or hybrid)
            companion_page: Companion page number for this camera's controls
        """
        self.camera_http_sender = camera_http_sender
        self.companion_api = companion_api
        self.mode = mode
        self.companion_page = companion_page

        # Mapping of actions to Companion button locations
        # This should be configured to match your Companion layout
        self.action_button_map: Dict[str, CompanionButton] = {}

    def set_mode(self, mode: CompanionControlMode):
        """Set control mode"""
        self.mode = mode

    def map_action_to_button(self, action: str, row: int, column: int):
        """
        Map an action to a Companion button location.

        Args:
            action: Action name (e.g., "preset_1", "iris_auto", "wb_indoor")
            row: Button row
            column: Button column
        """
        self.action_button_map[action] = CompanionButton(
            page=self.companion_page,
            row=row,
            column=column
        )

    def execute_action(self, action: str, camera_command: str) -> Tuple[bool, str]:
        """
        Execute action with appropriate control mode.

        Args:
            action: Action name (e.g., "preset_1")
            camera_command: Direct HTTP command to send to camera

        Returns:
            Tuple of (success, method_used)
        """
        if self.mode == CompanionControlMode.DIRECT:
            # Direct only - fastest
            success = self.camera_http_sender(camera_command)
            return (success, "direct")

        elif self.mode == CompanionControlMode.COMPANION:
            # Companion only - for Stream Deck sync
            if action in self.action_button_map:
                success = self.companion_api.press_button(self.action_button_map[action])
                return (success, "companion")
            else:
                # No button mapped, fall back to direct
                success = self.camera_http_sender(camera_command)
                return (success, "direct_fallback")

        else:  # HYBRID mode (recommended)
            # Try direct first (fast)
            direct_success = self.camera_http_sender(camera_command)

            # Also trigger Companion button if mapped (for Stream Deck LED sync)
            if action in self.action_button_map and self.companion_api.is_available:
                self.companion_api.press_button(self.action_button_map[action])

            # If direct failed and Companion button exists, try Companion as fallback
            if not direct_success and action in self.action_button_map:
                companion_success = self.companion_api.press_button(self.action_button_map[action])
                return (companion_success, "companion_fallback")

            return (direct_success, "hybrid")

    def recall_preset(self, preset_num: int) -> Tuple[bool, str]:
        """
        Recall preset with hybrid control.

        Args:
            preset_num: Preset number (1-based)

        Returns:
            Tuple of (success, method_used)
        """
        action = f"preset_{preset_num}"
        camera_command = f"R{preset_num:02d}"  # Panasonic preset recall format

        return self.execute_action(action, camera_command)
