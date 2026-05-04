"""
================================================================================
Affiliate Pages Downloader Automation
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-03-14
Description :
    Automates the download of affiliate product pages using cross-platform
    keyboard and mouse automation. Reads URLs from `Inputs/urls.txt`, opens
    a blank separator tab, navigates to each URL in a new tab, performs
    image-first and coordinate-fallback actions, and builds a condensed
    grouped report of execution steps.

    Key features include:
        - Cross-platform automation with pyautogui
        - Image-first and coordinates fallback interaction
        - Execution report generation
        - Runtime logging and notification sound
        - Optional messagebox notification upon completion

Usage:
    1. Ensure Chrome window is focused and permissions are granted (Linux/macOS).
    2. Execute the script:
            $ python affiliate_pages_downloader.py
    3. Outputs a console report and optional messagebox notification.

Outputs:
    - Execution report printed to the console
    - Optional messagebox summarizing automation results
    - Logs saved under `./Logs/affiliate_pages_downloader.log`

TODOs:
    - Implement CLI argument for verbose logging
    - Extend image assets fallback for other browsers
    - Add retry logic for failed downloads
    - Parallelize tab processing
    - Refine execution timing and reporting

Dependencies:
    - Python >= 3.9
    - pyautogui
    - tkinter (optional for messagebox)
    - pathlib
    - time
    - argparse
    - sys

Assumptions & Notes:
    - Chrome must be focused during execution
    - Screen recording/accessibility permissions required on Linux/macOS
    - URLs input file: `Inputs/urls.txt`
    - Image assets stored in `.assets/Browser/`
"""


import argparse  # Parse command-line arguments.
import atexit  # Register post-execution callback functions.
import ctypes  # Import ctypes for Windows monitor enumeration.
import ctypes.wintypes  # Import ctypes.wintypes for RECT structure access.
import cv2  # Import OpenCV for color conversion.
import datetime  # Capture execution timestamps.
import json  # Handle JSON data for Chrome profile resolution.
import numpy as np  # Import NumPy for array conversion.
import os  # Execute operating-system commands.
import platform  # Identify active operating system.
import pyautogui  # Automate keyboard and mouse interactions.
import re  # Regular expressions for stripping ANSI escape sequences.
import shutil  # Move files between directories.
import subprocess  # Execute shell commands for clipboard access and other operations.
import sys  # Access process-level runtime controls.
import time  # Manage sleep and elapsed time operations.
import tkinter as tk  # Import tkinter module.
import traceback  # Import traceback module for detailed exception reporting.
from colorama import Style  # Reset ANSI style output.
from pathlib import Path  # Build and resolve filesystem paths.
from PIL import ImageGrab  # Import PIL ImageGrab for multi-monitor screenshot capture.
from pyscreeze import Box  # Import Box namedtuple for image location results.
from tkinter import messagebox  # Import tkinter messagebox utility.
from tqdm import tqdm  # Import tqdm progress bar iterator.
from typing import Any, Dict, List, Optional, Tuple  # Provide typing annotations for containers and dynamic objects.


PROJECT_ROOT = str(Path(__file__).resolve().parents[[p.name for p in Path(__file__).resolve().parents].index("E-Commerces-WebScraper")])  # Project root directory

if PROJECT_ROOT not in sys.path:  # Ensure project root is in sys.path
    sys.path.insert(0, PROJECT_ROOT)  # Insert at the beginning

from Logger import Logger  # For logging output to both terminal and file
from Amazon import AFFILIATE_URL_PATTERN  # Import Amazon affiliate URL regex pattern from project Amazon module
from urls_utils import load_urls_to_process, preprocess_urls, write_urls_to_file  # Centralized URL helpers


# Macros:
class BackgroundColors:  # Colors for the terminal
    CYAN = "\033[96m"  # Cyan
    GREEN = "\033[92m"  # Green
    YELLOW = "\033[93m"  # Yellow
    RED = "\033[91m"  # Red
    BOLD = "\033[1m"  # Bold
    UNDERLINE = "\033[4m"  # Underline
    CLEAR_TERMINAL = "\033[H\033[J"  # Clear the terminal


# Execution Constants:
VERBOSE = False  # Set to True to output verbose messages
RENEW_AMAZON_AFFILIATE_URL = True  # Set to True to enable Amazon affiliate URL renewal attempts (currently disabled for safety)
ONLY_RENEW_AMAZON_AFFILIATE_URLS = False  # Control mode to only renew Amazon affiliate URLs without downloading content
RENEWED_URL_MAP: Dict[str, str] = {}  # Store renewed Amazon URL pairs as original-to-renewed mapping.

ACTIVE_DOWNLOADS_DIRS = []  # Store the resolved active downloads directories path for reuse.

DOWNLOADS_DIR = {
    "windows": [os.path.join(os.path.expanduser("~"), "Downloads"), r"D:\Sem Backup\Download"],  # Define Windows downloads directory candidates.
    "linux": [os.path.join(os.path.expanduser("~"), "Downloads")],  # Define Linux downloads directory candidates.
    "darwin": [os.path.join(os.path.expanduser("~"), "Downloads")],  # Define macOS downloads directory candidates.
}  # Define monitored downloads directory candidates by operating system.

CHROME_USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data")  # Chrome User Data dir (Windows default)
CHROME_PROFILE_DISPLAY_NAME = "Achadinhos Brasil Amanda"  # Profile display name to use
CHROME_PROFILE_DIRECTORY: str | None = None  # Resolved profile folder name (e.g. "Profile 1")
pyautogui.FAILSAFE = True  # Enable fail-safe by moving cursor to the top-left corner.
pyautogui.PAUSE = 0.05  # Apply default pause between pyautogui actions.

# Resolution Independence Reference Dimensions:
REFERENCE_SCREEN_WIDTH = 1920  # Define reference screen width for coordinate scaling.
REFERENCE_SCREEN_HEIGHT = 1080  # Define reference screen height for coordinate scaling.

# Coordinate Fallback Values (for 1920x1080 reference resolution):
EXTENSION_X_REF = 1752  # Define extension click reference X coordinate for 1920x1080.
EXTENSION_Y_REF = 705  # Define extension click reference Y coordinate for 1920x1080.
DOWNLOAD_BUTTON_X_REF = 1590  # Define download button reference X coordinate for 1920x1080.
DOWNLOAD_BUTTON_Y_REF = 64  # Define download button reference Y coordinate for 1920x1080.
CLOSE_DOWNLOAD_TAB_X_REF = 1905  # Define close download tab reference X coordinate for 1920x1080.
CLOSE_DOWNLOAD_TAB_Y_REF = 148  # Define close download tab reference Y coordinate for 1920x1080.
CHROME_DOWNLOAD_SETTINGS_URL = "chrome://settings/downloads"  # Define Chrome downloads settings page URL.
DOWNLOAD_SETTINGS_RENDER_WAIT_SECONDS = 2.0  # Define wait time after loading Chrome downloads settings page.
DOWNLOAD_SETTINGS_TOGGLE_CLICK_WAIT_SECONDS = 0.4  # Define wait time after clicking a downloads settings toggle.
DOWNLOAD_SETTINGS_VERIFICATION_ATTEMPTS = 5  # Define the number of final-state verification attempts.
DOWNLOAD_SETTINGS_VERIFICATION_WAIT_SECONDS = 0.5  # Define wait time between final-state verification attempts.
DOWNLOAD_SETTINGS_STATE_CORRECT = "Correct"  # Define state label for the expected downloads settings configuration.
DOWNLOAD_SETTINGS_STATE_TOGGLE_1_ON = "Toggle 1 On"  # Define state label for the first downloads settings toggle enabled.
DOWNLOAD_SETTINGS_STATE_TOGGLE_2_ON = "Toggle 2 On"  # Define state label for the second downloads settings toggle enabled.
DOWNLOAD_SETTINGS_STATE_BOTH_TOGGLES_ON = "Both Toggles On"  # Define state label for both downloads settings toggles enabled.
DOWNLOAD_SETTINGS_STATE_UNKNOWN = "Unknown"  # Define state label for an unresolved downloads settings configuration.
MAX_DOWNLOAD_RETRY_ATTEMPTS = 2  # Define maximum number of download attempts per URL including the initial attempt.

TARGET_CHROME_TITLE = ""  # Store selected Chrome window title for reuse.
ACTIVE_CHROME_BOUNDS = {"left": 0, "top": 0, "width": 0, "height": 0}  # Store active Chrome window bounds for coordinate calculations.
DEDICATED_AUTOMATION_HWND: int = 0  # Store OS window handle of dedicated automation Chrome window for tab lifecycle isolation.
USE_MAIN_MONITOR: bool = False  # Control whether UI operations target the primary monitor instead of a secondary monitor.

# Logger Setup:
logger = Logger(f"./Logs/{Path(__file__).stem}.log", clean=True)  # Create a Logger instance
sys.stdout = logger  # Redirect stdout to the logger
sys.stderr = logger  # Redirect stderr to the logger

# Sound Constants:
SOUND_COMMANDS = {
    "Darwin": "afplay",
    "Linux": "aplay",
    "Windows": "start",
}  # The commands to play a sound for each operating system
SOUND_FILE = "./.assets/Sounds/NotificationSound.wav"  # The path to the sound file

# RUN_FUNCTIONS:
RUN_FUNCTIONS = {
    "Play Sound": True,  # Set to True to play a sound when the program finishes
}


# Functions Definitions:


def parse_arguments(repo_root: Path) -> argparse.Namespace:
    """
    Parse and return command-line arguments for the Affiliate Pages Downloader Automation.

    :param repo_root: Root directory of the repository.
    :return: Parsed argument namespace containing all CLI flags.
    """
    
    parser = argparse.ArgumentParser(description="Affiliate Pages Downloader Automation - Automates the downloading of affiliate pages, URL renewal, and content management.")  # Initialize argument parser with description.

    parser = argparse.ArgumentParser(description="Cross-platform affiliate pages downloader automation")  # Initialize argument parser.
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for debugging and insights")  # Register verbose flag argument.
    parser.add_argument("--process_only_unlinked_urls", action="store_true", help="Process only URLs that are not yet linked in the report in the input file")  # Register unlinked URLs processing flag.
    parser.add_argument("--tab-count", type=int, default=0, help="Number of URLs/tabs to process (0 = use all URLs from Inputs/urls.txt)")  # Register tab-count argument.
    parser.add_argument("--urls-file", type=Path, default=repo_root / "Inputs" / "urls.txt", help="Path to URLs input file")  # Register urls-file argument.
    parser.add_argument("--assets-dir", type=Path, default=repo_root / ".assets" / "Browser", help="Directory containing image assets")  # Register assets-dir argument.
    parser.add_argument("--headerless", type=lambda s: str(s).lower() in ("true", "1", "yes", "y"), default=True, help="Whether to suppress GUI messagebox (default: True)")  # Register headerless argument with boolean conversion
    parser.add_argument("--renew-amazon-affiliate-url", action="store_true", default=True, help="Enable Amazon affiliate URL renewal attempts (default: True)")  # Register renewal override argument
    parser.add_argument("--only-renew-amazon-urls", nargs="?", const="true", default=None, help="Enable mode that only renews Amazon affiliate URLs without downloading content")  # Register only-renew mode argument with optional truthy value.
    parser.add_argument("--main-monitor", action="store_true", default=False, help="Route all UI operations to the primary monitor (default: False uses secondary monitor when available)")  # Register main-monitor flag argument.

    args = parser.parse_args()  # Parse command-line arguments

    return args  # Return parsed argument namespace


def resolve_chrome_profile_directory(display_name: str) -> str | None:
    """
    Resolve Chrome profile directory folder (e.g. "Profile 1" or "Default")
    from the Chrome "Local State" file by matching the profile display name.

    Returns the directory name when found, otherwise None.
    """
    
    try:  # Attempt to read Chrome Local State and resolve profile
        local_state_path = Path(CHROME_USER_DATA_DIR) / "Local State"  # Construct Local State path
        if not local_state_path.exists():  # Verify Local State exists
            return None  # Return when Local State is missing

        raw = local_state_path.read_text(encoding="utf-8", errors="ignore")  # Read Local State file
        data = json.loads(raw)  # Parse Local State JSON
        info_cache = data.get("profile", {}).get("info_cache", {})  # Get profile info cache

        for profile_dir, info in info_cache.items():  # Iterate profile entries
            if info.get("name") == display_name:  # Match profile display name
                return profile_dir  # Return matching profile directory

    except Exception:  # Return None on any error during resolution
        return None  # Return None on failure

    return None  # Return None when no matching profile is found


def resolve_chrome_profile_with_fallback(display_name: str, fallback_folder_name: str = "Default") -> str | None:
    """
    Resolve profile directory or fallback to the main profile.

    :param display_name: Display name of the desired profile.
    :param fallback_folder_name: Folder name to use as fallback (default "Default").
    :return: Resolved profile folder name or fallback when resolution fails.
    """

    try:  # Attempt primary then fallback resolution
        profile = resolve_chrome_profile_directory(display_name)  # Attempt to resolve requested profile
        if profile is not None:  # Verify if requested profile was resolved
            return profile  # Return the resolved profile directory

        fallback = resolve_chrome_profile_directory(fallback_folder_name)  # Attempt to resolve fallback profile
        if fallback is not None:  # Verify if fallback profile was resolved
            return fallback  # Return the resolved fallback directory

        return fallback_folder_name  # Return folder name string as final fallback
    except Exception:  # Handle any exception during resolution
        return fallback_folder_name  # Return fallback folder name on error


def update_chrome_profile(display_name: str) -> None:
    """
    Update CHROME_PROFILE_DIRECTORY from the provided display name.

    :param display_name: Display name of the desired profile.
    :return: None.
    """

    global CHROME_PROFILE_DIRECTORY  # Reference global resolved profile directory variable.

    resolved_profile = resolve_chrome_profile_with_fallback(display_name)  # Resolve profile directory using configured display name with Default fallback.

    CHROME_PROFILE_DIRECTORY = resolved_profile  # Assign resolved profile directory to global configuration variable.


def verbose_output(true_string="", false_string=""):
    """
    Outputs a message if the VERBOSE constant is set to True.

    :param true_string: The string to be outputted if the VERBOSE constant is set to True.
    :param false_string: The string to be outputted if the VERBOSE constant is set to False.
    :return: None
    """

    if VERBOSE and true_string != "":  # If VERBOSE is True and a true_string was provided
        print(true_string)  # Output the true statement string
    elif false_string != "":  # If a false_string was provided
        print(false_string)  # Output the false statement string


def open_chrome_by_os() -> bool:
    """
    Opens Google Chrome using operating-system specific commands.

    :param: None.
    :return: True when the launch command is dispatched, otherwise False.
    """

    current_os = platform.system().lower()  # Retrieve normalized operating system name.

    try:  # Attempt Chrome launch using operating-system specific command.
        if current_os == "windows":  # Verify whether the current operating system is Windows.
            os.system("start \"\" chrome --new-window about:blank")  # Dispatch Windows command to open a new Chrome window.
        elif current_os == "darwin":  # Verify whether the current operating system is macOS.
            os.system("open -a 'Google Chrome'")  # Dispatch macOS command to open Chrome.
        elif current_os == "linux":  # Verify whether the current operating system is Linux.
            launch_code = os.system("google-chrome >/dev/null 2>&1 &")  # Dispatch Linux command to open Chrome in background.

            if launch_code != 0:  # Verify whether primary Linux Chrome command failed.
                os.system("chromium-browser >/dev/null 2>&1 &")  # Dispatch Linux Chromium fallback command in background.
        else:  # Handle unsupported operating systems.
            print(f"{BackgroundColors.YELLOW}[WARNING] Unsupported operating system for Chrome auto-launch: {current_os}{Style.RESET_ALL}")  # Log unsupported operating system warning.
            return False  # Return failure status for unsupported operating systems.

        time.sleep(2.0)  # Wait for Chrome process and window initialization.
        return True  # Return success status after launch command dispatch.
    except Exception:  # Handle Chrome launch failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to open Chrome automatically using operating-system command.{Style.RESET_ALL}")  # Log Chrome auto-launch failure warning.
        return False  # Return failure status when launch attempt fails.


def open_chrome_with_profile(display_name: str) -> bool:
    """
    Open Google Chrome using the requested profile when no windows are present.

    :param display_name: Display name of the Chrome profile to open.
    :return: True when the launch command is dispatched, otherwise False.
    """

    try:  # Attempt profile-aware Chrome launch using OS-specific commands
        profile_dir = resolve_chrome_profile_with_fallback(display_name)  # Resolve profile directory using display name with Default fallback.

        user_data_dir = str(Path(CHROME_USER_DATA_DIR).resolve())  # Resolve absolute user-data directory path for Chrome.

        current_os = platform.system().lower()  # Retrieve normalized operating system name.

        if current_os == "windows":  # Verify whether the current operating system is Windows.
            os.system(f'start "" chrome --new-window --user-data-dir="{user_data_dir}" --profile-directory="{profile_dir}" about:blank')  # Dispatch Windows start command to open a new Chrome window with profile flags.
        elif current_os == "darwin":  # Verify whether the current operating system is macOS.
            os.system(f'open -a "Google Chrome" --args --new-window --user-data-dir="{user_data_dir}" --profile-directory="{profile_dir}" about:blank')  # Dispatch macOS open command with Chrome args to open a new specific-profile window.
        elif current_os == "linux":  # Verify whether the current operating system is Linux.
            launch_code = os.system(f'google-chrome --new-window --user-data-dir="{user_data_dir}" --profile-directory="{profile_dir}" about:blank >/dev/null 2>&1 &')  # Dispatch Linux chrome command in background with new-window profile flags.

            if launch_code != 0:  # Verify whether primary Linux Chrome command failed.
                os.system(f'chromium-browser --new-window --user-data-dir="{user_data_dir}" --profile-directory="{profile_dir}" about:blank >/dev/null 2>&1 &')  # Dispatch Linux Chromium fallback command in background with new-window profile flags.
        else:  # Handle unsupported operating systems.
            print(f"{BackgroundColors.YELLOW}[WARNING] Unsupported operating system for Chrome auto-launch: {current_os}{Style.RESET_ALL}")  # Log unsupported operating system warning.
            return False  # Return failure status for unsupported operating systems.

        time.sleep(2.0)  # Wait for Chrome process and window initialization.
        return True  # Return success status after profile-aware launch command dispatch.
    except Exception:  # Handle Chrome launch failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to open Chrome automatically with profile: {display_name}{Style.RESET_ALL}")  # Log Chrome auto-launch failure warning.
        return False  # Return failure status when profile-aware launch attempt fails.


def activate_chrome_window() -> bool:
    """
    Activates a Chrome window to receive automation keystrokes.

    :return: True if a Chrome window is active, otherwise False.
    """

    global TARGET_CHROME_TITLE  # Reference global selected window title.

    chrome_windows = get_chrome_windows()  # Retrieve visible non-minimized Chrome windows.

    if len(chrome_windows) == 0:  # Verify at least one Chrome window exists.
        launch_result = open_chrome_with_profile(CHROME_PROFILE_DISPLAY_NAME)  # Attempt to open Chrome using profile-aware launch command.

        if not launch_result:  # Verify whether automatic Chrome launch failed.
            return False  # Return failure status when no Chrome window is available.

        chrome_windows = get_chrome_windows()  # Retrieve visible non-minimized Chrome windows after launch attempt.

        if len(chrome_windows) == 0:  # Verify at least one Chrome window exists after launch attempt.
            print(f"{BackgroundColors.RED}No Chrome windows were detected after automatic launch. Automation cannot continue.{Style.RESET_ALL}")  # Print Chrome not found error after launch retry.
            return False  # Return failure status when no Chrome window is available after launch retry.

    target_window = select_chrome_window(chrome_windows)  # Resolve deterministic Chrome target window.

    if target_window is None:  # Verify if a deterministic target window was selected.
        print(f"{BackgroundColors.RED}Failed to select a Chrome window. Automation cannot continue.{Style.RESET_ALL}")  # Print selection failure error.
        return False  # Return failure status when no target window can be selected.

    TARGET_CHROME_TITLE = str(getattr(target_window, "title", ""))  # Persist selected Chrome window title for next cycle.

    if not activate_window_with_fallback(target_window):  # Verify if Chrome activation succeeded.
        print(f"{BackgroundColors.RED}Failed to activate Chrome window. Keep Chrome focused manually and retry.{Style.RESET_ALL}")  # Print activation failure message.
        return False  # Return failure status after activation attempts.

    ensure_result = ensure_chrome_on_primary_monitor(target_window)  # Ensure active Chrome window is usable on the primary monitor.

    move_cursor_to_active_window_center()  # Move cursor to the center of the active Chrome window for safety and potential rendering updates.

    if not ensure_result:  # Verify if monitor-placement assurance failed.
        print(f"{BackgroundColors.YELLOW}[WARNING] Chrome window relocation fallback did not complete. Continuing with current active window.{Style.RESET_ALL}")  # Log relocation fallback warning without interrupting workflow.

    return True  # Return success status after activation and relocation flow.


def get_chrome_windows() -> List[Any]:
    """
    Retrieves visible and non-minimized Chrome windows.

    :param: None.
    :return: List of visible non-minimized Chrome windows.
    """

    try:  # Attempt cross-platform window enumeration.
        get_all_windows = getattr(pyautogui, "getAllWindows", None)  # Resolve optional window listing API.
        windows_raw = get_all_windows() if callable(get_all_windows) else []  # Retrieve all desktop windows when API is available.
        windows = windows_raw if isinstance(windows_raw, list) else []  # Normalize window collection to a list.
    except Exception:  # Handle unsupported window-management backend.
        print(f"{BackgroundColors.YELLOW}Window activation API is unavailable on this system. Keep Chrome focused manually.{Style.RESET_ALL}")  # Print manual-focus warning.
        return []  # Return empty list when desktop window enumeration is unavailable.

    chrome_windows: List[Any] = []  # Initialize filtered Chrome windows list.

    for window in windows:  # Iterate all desktop windows.
        title = str(getattr(window, "title", "")).strip()  # Retrieve and normalize window title.

        if title == "":  # Verify window title has content.
            continue  # Skip untitled windows.

        if "chrome" not in title.lower():  # Verify window title belongs to Chrome.
            continue  # Skip non-Chrome windows.

        is_minimized = bool(getattr(window, "isMinimized", False))  # Retrieve minimized state from window object.

        if is_minimized:  # Verify window is not minimized.
            continue  # Skip minimized Chrome windows.

        is_visible = bool(getattr(window, "visible", True))  # Retrieve visible state with True default when property is absent.

        if not is_visible:  # Verify window is visible.
            continue  # Skip hidden Chrome windows.

        chrome_windows.append(window)  # Append valid Chrome window to filtered list.

    return chrome_windows  # Return filtered Chrome windows.


def select_chrome_window(chrome_windows: List[Any]) -> Any:
    """
    Selects a deterministic Chrome window target.

    :param chrome_windows: List of visible non-minimized Chrome windows.
    :return: Selected Chrome window object or None.
    """

    global TARGET_CHROME_TITLE  # Reference persisted Chrome window title.

    if len(chrome_windows) == 0:  # Verify there is at least one candidate window.
        return None  # Return None when no candidates are available.

    if TARGET_CHROME_TITLE != "":  # Verify persisted title exists from previous successful selection.
        for window in chrome_windows:  # Iterate candidate windows to reuse persisted title.
            if str(getattr(window, "title", "")) == TARGET_CHROME_TITLE:  # Verify title matches persisted selection.
                return window  # Return persisted target window.

    try:  # Attempt retrieval of currently active desktop window.
        get_active_window = getattr(pyautogui, "getActiveWindow", None)  # Resolve optional active-window API.
        active_window = get_active_window() if callable(get_active_window) else None  # Retrieve currently active desktop window when API is available.
    except Exception:  # Handle active-window API failures.
        active_window = None  # Fallback to None when active-window retrieval fails.

    if active_window is not None:  # Verify an active window object was retrieved.
        active_title = str(getattr(active_window, "title", "")).lower()  # Retrieve and normalize active window title.

        if "chrome" in active_title and not bool(getattr(active_window, "isMinimized", False)):  # Verify active window is a valid non-minimized Chrome window.
            return active_window  # Return active Chrome window as most recently focused target.

    sorted_windows = sorted(  # Build deterministic ordering for remaining candidates.
        chrome_windows,  # Provide candidate Chrome windows list.
        key=lambda window: (str(getattr(window, "title", "")).lower(), int(getattr(window, "left", 0)), int(getattr(window, "top", 0))),  # Sort by title and position for deterministic fallback.
    )  # Finalize deterministic ordering for candidate windows.

    return sorted_windows[0] if len(sorted_windows) > 0 else None  # Return first deterministic candidate when available.


def click_box_center(box: Tuple[int, int, int, int], move_cursor: bool = True) -> None:
    """
    Clicks the center of a detected bounding box.

    :param box: Bounding box tuple (x, y, width, height).
    :param move_cursor: Flag indicating whether to move cursor before clicking.
    :return: None
    """
    
    x, y, w, h = box  # Unpack bounding box tuple.

    center_x = x + (w // 2)  # Compute center x coordinate of detected box.
    center_y = y + (h // 2)  # Compute center y coordinate of detected box.

    if move_cursor:  # Verify whether cursor movement before click is enabled.
        pyautogui.moveTo(center_x, center_y)  # Move cursor to detected center for traceability.
    
    pyautogui.click(center_x, center_y)  # Click center point of the box.


def activate_window_with_fallback(target_window: Any) -> bool:
    """
    Activates a window using primary and secondary strategies.

    :param target_window: Window object selected for activation.
    :return: True when activation succeeds, otherwise False.
    """

    global ACTIVE_CHROME_BOUNDS  # Reference global variable for caching active window bounds.

    if target_window is None:  # Verify window reference exists before activation attempts.
        return False  # Return failure status when target window is missing.

    try:  # Attempt primary activation strategy.
        target_window.activate()  # Activate selected Chrome window.
        time.sleep(0.2)  # Wait after activation.
        target_window.maximize()  # Maximize selected Chrome window.
        time.sleep(0.8)  # Wait after maximize.

        left = int(getattr(target_window, "left", 0))  # Retrieve window left coordinate.
        top = int(getattr(target_window, "top", 0))  # Retrieve window top coordinate.
        width = int(getattr(target_window, "width", 0))  # Retrieve window width value.
        height = int(getattr(target_window, "height", 0))  # Retrieve window height value.
        ACTIVE_CHROME_BOUNDS = {"left": left, "top": top, "width": width, "height": height}  # Cache active window bounds for coordinate calculations.

        return True  # Return success status after primary activation strategy.
    except Exception:  # Handle primary activation strategy failure.
        pass  # Continue to secondary activation strategy.

    try:  # Attempt secondary activation strategy.
        if bool(getattr(target_window, "isMinimized", False)):  # Verify if the target window is minimized.
            restore_function = getattr(target_window, "restore", None)  # Resolve restore method for minimized window recovery.

            if callable(restore_function):  # Verify restore method availability.
                restore_function()  # Restore minimized window before activation retry.
                time.sleep(0.2)  # Wait after restore operation.

        left = int(getattr(target_window, "left", 0))  # Retrieve window left coordinate.
        top = int(getattr(target_window, "top", 0))  # Retrieve window top coordinate.
        width = int(getattr(target_window, "width", 0))  # Retrieve window width value.
        height = int(getattr(target_window, "height", 0))  # Retrieve window height value.
        click_box_center(target_window)  # Focus window by clicking inside it.
        time.sleep(0.2)  # Wait after focus click.
        target_window.activate()  # Retry window activation after focus click.
        time.sleep(0.2)  # Wait after activation retry.
        target_window.maximize()  # Retry maximize operation for consistent coordinates.
        time.sleep(0.8)  # Wait after maximize retry.

        ACTIVE_CHROME_BOUNDS = {"left": left, "top": top, "width": width, "height": height}  # Cache active window bounds for coordinate calculations.

        return True  # Return success status after secondary activation strategy.
    except Exception:  # Handle secondary activation strategy failure.
        return False  # Return failure status when all activation strategies fail.


def monitor_enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData, monitor_rects: List[Tuple[int, int, int, int]]) -> bool:
    """
    Callback function for Windows monitor enumeration that collects monitor bounds.
    
    :param hMonitor: Handle to the monitor being enumerated.
    :param hdcMonitor: Handle to the monitor's device context (unused).
    :param lprcMonitor: Pointer to a RECT structure containing the monitor's bounds.
    :param dwData: User-defined data passed to EnumDisplayMonitors (unused).
    :param monitor_rects: List to collect monitor bounds as tuples of (left, top, right, bottom).
    :return: True to continue enumeration, False to stop.
    """
    
    rect = lprcMonitor.contents  # Dereference RECT structure from pointer.
    monitor_rects.append((int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)))  # Append collected monitor bounds to list.
    return True  # Return True to continue monitor enumeration.


def detect_secondary_monitor_bounds(primary_bounds: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """
    Detects bounds of any secondary monitor using platform-specific enumeration.

    :param primary_bounds: Primary monitor bounds as left, top, right, bottom fallback.
    :return: Secondary monitor bounds when available, otherwise primary bounds as fallback.
    """

    current_os = platform.system().lower()  # Retrieve normalized operating system name.

    try:  # Attempt platform-specific monitor enumeration for secondary detection.
        if current_os != "windows":  # Verify whether Windows-specific enumeration is applicable.
            return primary_bounds  # Return primary bounds when not on Windows.

        monitor_rects: List[Tuple[int, int, int, int]] = []  # Initialize monitor bounds collection.

        MonitorEnumProc = ctypes.WINFUNCTYPE(  # Define monitor enumeration callback signature.
            ctypes.c_bool,  # Return type: BOOL for continuation control.
            ctypes.c_void_p,  # HMONITOR handle argument.
            ctypes.c_void_p,  # HDC handle argument.
            ctypes.POINTER(ctypes.wintypes.RECT),  # LPRECT pointer to monitor rectangle.
            ctypes.c_ssize_t,  # LPARAM user data argument.
        )  # Finalize Windows MONITORENUMPROC callback type definition.

        callback_func = MonitorEnumProc(monitor_enum_callback)  # Create stable callback reference to prevent garbage collection.
        ctypes.windll.user32.EnumDisplayMonitors(None, None, callback_func, 0)  # Enumerate all connected display monitors.

        if len(monitor_rects) <= 1:  # Verify whether multiple monitors were detected.
            return primary_bounds  # Return primary bounds when only one monitor is present.

        prim_left, prim_top, prim_right, prim_bottom = primary_bounds  # Unpack primary monitor bounds for comparison.

        for rect in monitor_rects:  # Iterate enumerated monitor bounds to locate secondary.
            if rect != (prim_left, prim_top, prim_right, prim_bottom):  # Verify whether current monitor differs from primary.
                return rect  # Return first non-primary monitor bounds as secondary target.

    except Exception:  # Handle monitor enumeration failures gracefully.
        pass  # Continue to fallback when platform enumeration fails.

    return primary_bounds  # Return primary bounds as fallback when secondary detection is unavailable.


def get_desired_monitor_bounds() -> Tuple[int, int, int, int]:
    """
    Retrieves target monitor bounds based on the USE_MAIN_MONITOR setting.

    :param: None.
    :return: Tuple of target monitor bounds as left, top, right, bottom.
    """

    screen_size = pyautogui.size()  # Retrieve primary monitor size from pyautogui backend.
    primary_bounds = 0, 0, int(screen_size.width), int(screen_size.height)  # Build primary monitor bounds tuple.

    if USE_MAIN_MONITOR:  # Verify whether primary monitor is explicitly selected.
        return primary_bounds  # Return primary monitor bounds when main monitor flag is set.

    return detect_secondary_monitor_bounds(primary_bounds)  # Return secondary monitor bounds when available, otherwise primary bounds.


def is_window_outside_primary_monitor(target_window: Any, primary_bounds: Tuple[int, int, int, int]) -> bool:
    """
    Verifies whether a window center is outside primary monitor bounds.

    :param target_window: Window object to evaluate.
    :param primary_bounds: Primary monitor bounds as left, top, right, bottom.
    :return: True when the window center is outside primary bounds, otherwise False.
    """

    if target_window is None:  # Verify window reference exists for bounds evaluation.
        return False  # Return False when no window is available for evaluation.

    left = int(getattr(target_window, "left", 0))  # Retrieve window left coordinate.
    top = int(getattr(target_window, "top", 0))  # Retrieve window top coordinate.
    width = max(1, int(getattr(target_window, "width", 1)))  # Retrieve window width using safe minimum value.
    height = max(1, int(getattr(target_window, "height", 1)))  # Retrieve window height using safe minimum value.
    center_x = left + (width // 2)  # Compute window center X coordinate.
    center_y = top + (height // 2)  # Compute window center Y coordinate.
    primary_left, primary_top, primary_right, primary_bottom = primary_bounds  # Unpack primary monitor bounds.

    if center_x < primary_left or center_x >= primary_right:  # Verify horizontal center position against primary bounds.
        return True  # Return True when horizontal center is outside primary bounds.

    if center_y < primary_top or center_y >= primary_bottom:  # Verify vertical center position against primary bounds.
        return True  # Return True when vertical center is outside primary bounds.

    return False  # Return False when center is inside primary bounds.


def relocate_window_to_primary_monitor(target_window: Any) -> bool:
    """
    Relocates a window to the primary monitor when needed.

    :param target_window: Window object selected for relocation.
    :return: True when relocation is not required or succeeds, otherwise False.
    """

    if target_window is None:  # Verify window reference exists before relocation.
        return False  # Return failure status when target window is missing.

    try:  # Attempt primary monitor relocation logic.
        primary_left, primary_top, primary_right, primary_bottom = get_desired_monitor_bounds()  # Retrieve primary monitor bounds.

        if not is_window_outside_primary_monitor(target_window, (primary_left, primary_top, primary_right, primary_bottom)):  # Verify whether relocation is required.
            return True  # Return success when window is already on primary monitor.

        move_to_function = getattr(target_window, "moveTo", None)  # Resolve moveTo method for window relocation.

        if not callable(move_to_function):  # Verify moveTo method availability.
            print(f"{BackgroundColors.YELLOW}[WARNING] Window relocation API is unavailable for Chrome window.{Style.RESET_ALL}")  # Log relocation API warning.
            return False  # Return failure when relocation API is unavailable.

        width = max(1, int(getattr(target_window, "width", 1)))  # Retrieve current window width using safe minimum value.
        height = max(1, int(getattr(target_window, "height", 1)))  # Retrieve current window height using safe minimum value.
        primary_width = max(1, primary_right - primary_left)  # Compute primary monitor width.
        primary_height = max(1, primary_bottom - primary_top)  # Compute primary monitor height.
        target_left = primary_left if width >= primary_width else max(primary_left, min(int(getattr(target_window, "left", primary_left)), primary_right - width))  # Compute relocated left coordinate while preserving size when possible.
        target_top = primary_top if height >= primary_height else max(primary_top, min(int(getattr(target_window, "top", primary_top)), primary_bottom - height))  # Compute relocated top coordinate while preserving size when possible.
        move_to_function(target_left, target_top)  # Move window into primary monitor bounds.
        time.sleep(0.2)  # Wait after relocation operation.

        resize_to_function = getattr(target_window, "resizeTo", None)  # Resolve resizeTo method for oversized window fallback.

        if callable(resize_to_function) and (width > primary_width or height > primary_height):  # Verify resize is required and supported.
            resize_to_function(min(width, primary_width), min(height, primary_height))  # Resize only when window exceeds primary monitor dimensions.
            time.sleep(0.2)  # Wait after resize operation.

        target_window.activate()  # Re-activate window after relocation.
        time.sleep(0.2)  # Wait after re-activation.
        return True  # Return success when relocation flow completes.
    except Exception:  # Handle relocation failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to relocate Chrome window to the primary monitor.{Style.RESET_ALL}")  # Log relocation failure warning.
        return False  # Return failure status on relocation exception.


def detach_tab_to_new_window() -> bool:
    """
    Opens a new Chrome window to recover primary-monitor focus.

    :param: None.
    :return: True when a new Chrome window is activated on primary monitor, otherwise False.
    """

    previous_windows = get_chrome_windows()  # Capture current Chrome windows before creating a new window.
    previous_titles = {str(getattr(window, "title", "")) for window in previous_windows}  # Capture current Chrome window titles for delta detection.

    try:  # Attempt fallback new-window strategy.
        pyautogui.hotkey("ctrl", "n")  # Open a new Chrome window as fallback strategy.
        time.sleep(0.8)  # Wait for new Chrome window creation.
    except Exception:  # Handle shortcut execution failure.
        return False  # Return failure when fallback shortcut cannot be executed.

    refreshed_windows = get_chrome_windows()  # Refresh Chrome windows list after fallback shortcut.
    target_window = None  # Initialize fallback target window reference.

    for window in refreshed_windows:  # Iterate refreshed Chrome windows for new window detection.
        title = str(getattr(window, "title", ""))  # Retrieve current window title.

        if title not in previous_titles:  # Verify whether current window title was not present previously.
            target_window = window  # Select newly detected window candidate.
            break  # Stop iteration after selecting first new candidate.

    if target_window is None and len(refreshed_windows) > 0:  # Verify fallback target is still unresolved.
        target_window = select_chrome_window(refreshed_windows)  # Resolve deterministic fallback target from refreshed list.

    if target_window is None:  # Verify fallback target availability.
        return False  # Return failure when no fallback window is available.

    if not activate_window_with_fallback(target_window):  # Verify activation for fallback window.
        return False  # Return failure when fallback window activation fails.

    return relocate_window_to_primary_monitor(target_window)  # Return relocation status for fallback window.


def ensure_chrome_on_primary_monitor(target_window: Any) -> bool:
    """
    Ensures active Chrome window is usable on the primary monitor.

    :param target_window: Window object selected for activation flow.
    :return: True when the window is usable on primary monitor, otherwise False.
    """

    relocation_result = relocate_window_to_primary_monitor(target_window)  # Attempt relocation of active Chrome window to primary monitor.

    if relocation_result:  # Verify relocation was successful or not required.
        return True  # Return success when active window is already usable on primary monitor.

    print(f"{BackgroundColors.YELLOW}[DEBUG] Attempting fallback tab extraction strategy for Chrome window focus recovery.{Style.RESET_ALL}")  # Log fallback activation path.
    return detach_tab_to_new_window()  # Return fallback tab extraction strategy result.


def prepare_dedicated_chrome_window_for_automation() -> bool:
    """
    Prepares a dedicated Chrome window for automation tab lifecycle isolation.

    :param: None.
    :return: True when a dedicated automation window is ready, otherwise False.
    """

    global DEDICATED_AUTOMATION_HWND  # Reference global dedicated automation window handle.

    existing_windows = get_chrome_windows()  # Capture existing Chrome windows before opening the dedicated profile window.
    existing_hwnds = {int(getattr(window, "_hWnd", 0)) for window in existing_windows if int(getattr(window, "_hWnd", 0)) != 0}  # Capture existing Chrome window handles for delta detection.
    launch_attempts = 1 if len(existing_windows) > 0 else 2  # Define profile-window launch count to avoid changing an existing user window.
    launch_result = False  # Initialize aggregated launch result flag.

    for _ in range(launch_attempts):  # Iterate configured launch attempts for dedicated-window preparation.
        current_launch_result = open_chrome_with_profile(CHROME_PROFILE_DISPLAY_NAME)  # Open Chrome window with the configured profile.

        if current_launch_result:  # Verify whether current launch attempt was dispatched successfully.
            launch_result = True  # Persist successful launch status for post-launch selection flow.

    if launch_result:  # Verify whether profile-aware dedicated window launch succeeded.
        refreshed_windows = get_chrome_windows()  # Retrieve Chrome windows after dedicated profile launch.
        dedicated_window = None  # Initialize dedicated window reference for activation and handle capture.
        new_windows = []  # Initialize collection for newly opened Chrome windows.

        for window in refreshed_windows:  # Iterate refreshed Chrome windows to find the newly opened profile window.
            window_hwnd = int(getattr(window, "_hWnd", 0))  # Retrieve current Chrome window handle.

            if window_hwnd != 0 and window_hwnd not in existing_hwnds:  # Verify whether current window handle belongs to a newly opened window.
                new_windows.append(window)  # Append newly opened Chrome window candidate.

        if len(new_windows) > 0:  # Verify whether at least one newly opened Chrome window was found.
            dedicated_window = max(new_windows, key=lambda window: int(getattr(window, "_hWnd", 0)))  # Select the newest launched Chrome window candidate by OS handle.

        if dedicated_window is None:  # Verify whether dedicated window was not found by handle delta.
            get_active_window = getattr(pyautogui, "getActiveWindow", None)  # Resolve optional active-window API for fallback selection.
            active_window = get_active_window() if callable(get_active_window) else None  # Retrieve active desktop window as fallback dedicated candidate.
            active_title = str(getattr(active_window, "title", "")).lower() if active_window is not None else ""  # Retrieve and normalize active window title for Chrome validation.

            if active_window is not None and "chrome" in active_title:  # Verify whether active window is a Chrome window for fallback dedicated selection.
                dedicated_window = active_window  # Select active Chrome window as dedicated automation window.

        if dedicated_window is not None:  # Verify whether dedicated profile window candidate is available for activation.
            activation_result = activate_window_with_fallback(dedicated_window)  # Activate the dedicated profile window before storing its handle.

            if activation_result:  # Verify whether dedicated profile window activation succeeded.
                relocation_result = ensure_chrome_on_primary_monitor(dedicated_window)  # Ensure dedicated profile window is relocated to the primary monitor before automation.

                if not relocation_result:  # Verify whether relocation fallback failed for dedicated profile window.
                    print(f"{BackgroundColors.YELLOW}[WARNING] Dedicated profile window relocation did not complete. Continuing with current active window.{Style.RESET_ALL}")  # Log dedicated-window relocation warning without interrupting workflow.

                try:  # Attempt to capture dedicated profile window handle after activation.
                    DEDICATED_AUTOMATION_HWND = int(getattr(dedicated_window, "_hWnd", 0))  # Persist dedicated automation OS window handle.
                except Exception:  # Handle dedicated window handle capture exception.
                    DEDICATED_AUTOMATION_HWND = 0  # Reset dedicated window handle when capture fails.

                if DEDICATED_AUTOMATION_HWND != 0:  # Verify whether dedicated window handle was captured successfully.
                    return True  # Return success after dedicated profile window preparation.

    detach_result = detach_tab_to_new_window()  # Open and activate a dedicated Chrome window for automation as fallback path.

    if not detach_result:  # Verify whether dedicated Chrome window preparation failed.
        print(f"{BackgroundColors.RED}Failed to prepare dedicated Chrome window for automation. Aborting to preserve user tabs.{Style.RESET_ALL}")  # Log dedicated-window preparation failure.
        return False  # Return failure status when dedicated automation window is unavailable.

    try:  # Attempt to capture the dedicated automation window OS handle for reliable re-activation.
        get_active_window = getattr(pyautogui, "getActiveWindow", None)  # Resolve optional active-window API for handle capture.
        active_window = get_active_window() if callable(get_active_window) else None  # Retrieve active window reference after dedicated window creation.
        DEDICATED_AUTOMATION_HWND = int(getattr(active_window, "_hWnd", 0)) if active_window is not None else 0  # Extract and persist OS window handle from the newly created dedicated automation window.
    except Exception:  # Handle dedicated window handle capture failures.
        DEDICATED_AUTOMATION_HWND = 0  # Reset handle on capture failure to prevent stale automation references.

    return True  # Return success status when dedicated automation window is ready.


def close_dedicated_automation_window() -> bool:
    """
    Closes the dedicated automation Chrome window when present.

    :param: None.
    :return: True when closed or absent, False on failure.
    """

    global DEDICATED_AUTOMATION_HWND  # Reference stored dedicated automation window handle.

    if DEDICATED_AUTOMATION_HWND == 0:  # Verify whether a dedicated handle is stored.
        return True  # Nothing to close when handle is zero.

    window = find_window_by_hwnd(DEDICATED_AUTOMATION_HWND)  # Locate window by stored OS handle.

    if window is None:  # Verify window existence after handle lookup.
        DEDICATED_AUTOMATION_HWND = 0  # Reset stored handle when no matching window is found.
        return True  # Treat missing window as already closed.

    try:  # Attempt to activate and close the dedicated window gracefully.
        activate_window_with_fallback(window)  # Activate the dedicated automation window before closing.
        time.sleep(0.2)  # Wait after activation.
        current_os = platform.system().lower()  # Detect current operating system for proper close hotkey.

        if current_os == "darwin":  # Verify macOS for command-quit hotkey.
            pyautogui.hotkey("command", "q")  # Send Command+Q to quit Chrome on macOS.
        else:  # Use Control Shift+W for Windows/Linux to close the current window without affecting other windows.
            pyautogui.hotkey("ctrl", "shift", "w")  # Send Control+Shift+W to close the current Chrome window on Windows/Linux.

        time.sleep(0.6)  # Wait after close hotkey to allow window teardown.
        DEDICATED_AUTOMATION_HWND = 0  # Reset stored handle after successful close.
        return True  # Return success after closing the dedicated window.
    except Exception:  # Handle any exceptions during activation or close operations.
        return False  # Return failure when an exception prevented closing.


def find_window_by_hwnd(hwnd: int) -> Any:
    """
    Finds a Chrome window by its OS window handle.

    :param hwnd: OS window handle to search for among visible Chrome windows.
    :return: Matching Chrome window object or None when not found.
    """

    if hwnd == 0:  # Verify handle is non-zero before iterating Chrome windows.
        return None  # Return None when no valid handle is stored.

    chrome_windows = get_chrome_windows()  # Retrieve visible non-minimized Chrome windows.

    for window in chrome_windows:  # Iterate Chrome windows to locate the OS handle match.
        window_hwnd = int(getattr(window, "_hWnd", 0))  # Retrieve OS window handle from the current window object.

        if window_hwnd == hwnd:  # Verify whether current window matches the stored dedicated handle.
            return window  # Return matched window object immediately.

    return None  # Return None when no matching window is found.


def activate_automation_window() -> bool:
    """
    Activates the dedicated automation Chrome window using the stored OS window handle.

    :param: None.
    :return: True when the dedicated automation window is activated, otherwise False.
    """

    global DEDICATED_AUTOMATION_HWND  # Reference stored dedicated automation window handle.

    if DEDICATED_AUTOMATION_HWND != 0:  # Verify that a dedicated automation window handle was previously stored.
        window = find_window_by_hwnd(DEDICATED_AUTOMATION_HWND)  # Locate dedicated automation window by OS handle.

        if window is not None:  # Verify whether the dedicated automation window is still present.
            return activate_window_with_fallback(window)  # Activate dedicated automation window using existing fallback strategy.

    return activate_chrome_window()  # Fall back to standard Chrome activation when dedicated handle is unavailable.


def resolve_downloads_directories() -> List[str]:
    """
    Resolves the active downloads directory for the current operating system.

    :param: None.
    :return: Active downloads directory paths as list of strings, or fallback path when no candidates are available.
    """

    current_os = platform.system().lower()  # Retrieve normalized operating system name.
    candidates = DOWNLOADS_DIR.get(current_os, [])  # Retrieve downloads directory candidates for the detected operating system.

    if len(candidates) == 0:  # Verify if no downloads directory candidates were configured for the detected operating system.
        fallback_path = os.path.join(os.path.expanduser("~"), "Downloads")  # Build the default downloads fallback path.
        print(f"{BackgroundColors.YELLOW}[WARNING] No downloads directory candidates configured for detected OS, using fallback path: {fallback_path}{Style.RESET_ALL}")  # Log missing operating system configuration warning.
        return [fallback_path]  # Return the default downloads fallback path in a list.

    existing: List[str] = []  # Initialize list for existing candidate paths.

    for candidate in candidates:  # Iterate downloads directory candidates in configured priority order.
        if os.path.isdir(candidate):  # Verify if the current downloads directory candidate exists.
            existing.append(candidate)  # Append existing candidate to the list.

    if len(existing) == 0:  # Verify if no existing candidates were found after evaluation.
        print(f"{BackgroundColors.YELLOW}[WARNING] No existing downloads directory found for detected OS, using configured fallback.{Style.RESET_ALL}")  # Log missing downloads directory warning.
        return [candidates[0]]  # Return the first configured downloads directory candidate as fallback.

    return existing  # Return the list of existing downloads directory candidates.


def prepare_active_downloads_directory() -> List[str]:
    """
    Prepares the active downloads directories by resolving candidates and caching the result for reuse.

    :param: None.
    :return: Active downloads directory paths as list of strings.
    """

    global ACTIVE_DOWNLOADS_DIRS  # Declare global variable for active downloads directory.

    candidates = resolve_downloads_directories()  # Resolve downloads directory candidates for the current operating system.

    ACTIVE_DOWNLOADS_DIRS = [str(Path(candidate).resolve()) for candidate in candidates]  # Resolve and cache active downloads directory paths for reuse.
    return ACTIVE_DOWNLOADS_DIRS  # Return cached active downloads directories for immediate usage.


def resolve_urls_tab_count(tab_count: int, urls: List[str]) -> int:
    """
    Normalizes tab count based on available URL list.

    :param tab_count: Requested tab count.
    :param urls: URL list used for fallback sizing.
    :return: Resolved tab count.
    """

    if tab_count is None or tab_count <= 0:  # Verify tab count validity
        tab_count = len(urls)  # Use full URL list length when invalid tab count

    return tab_count  # Return normalized tab count


def resolve_url_files(urls_file: Path) -> Tuple[Path, Path]:
    """
    Resolves primary and backup URL file paths.

    :param urls_file: Base URLs file path.
    :return: Tuple containing resolved primary and backup file paths.
    """

    primary_urls_file = urls_file.resolve()  # Resolve primary file path
    backup_urls_file = primary_urls_file.with_name(primary_urls_file.stem + "-backup" + primary_urls_file.suffix)  # Resolve backup file path

    return primary_urls_file, backup_urls_file  # Return resolved file paths


def extract_and_validate_urls(primary_file: Path, backup_file: Path, affiliate_pattern: str) -> List[str]:
    """
    Extracts and validates Amazon URLs from primary and backup sources with deduplication.

    :param primary_file: Primary URLs file.
    :param backup_file: Backup URLs file.
    :param affiliate_pattern: Pattern used for extraction.
    :return: Deduplicated URL list.
    """

    primary_is_empty = is_file_empty(str(primary_file))  # Verify primary file emptiness
    backup_is_empty = is_file_empty(str(backup_file))  # Verify backup file emptiness

    if primary_is_empty:  # Verify primary file empty state
        print(f"{BackgroundColors.YELLOW}[WARNING] {primary_file.name} is empty{Style.RESET_ALL}")  # Log primary empty warning

    if backup_is_empty:  # Verify backup file empty state
        print(f"{BackgroundColors.YELLOW}[WARNING] {backup_file.name} is empty{Style.RESET_ALL}")  # Log backup empty warning

    primary_valid_urls = [] if primary_is_empty else extract_amazon_urls_from_file(str(primary_file), affiliate_pattern)  # Extract primary URLs
    backup_valid_urls = [] if backup_is_empty else extract_amazon_urls_from_file(str(backup_file), affiliate_pattern)  # Extract backup URLs

    if not primary_is_empty and len(primary_valid_urls) == 0:  # Verify invalid primary content
        print(f"{BackgroundColors.YELLOW}[WARNING] {primary_file.name} contains no valid Amazon URLs{Style.RESET_ALL}")  # Log warning

    if not backup_is_empty and len(backup_valid_urls) == 0:  # Verify invalid backup content
        print(f"{BackgroundColors.YELLOW}[WARNING] {backup_file.name} contains no valid Amazon URLs{Style.RESET_ALL}")  # Log warning

    unique_urls: List[str] = []  # Initialize deduplicated URL list
    seen_urls: set[str] = set()  # Initialize deduplication set

    for candidate_url in primary_valid_urls + backup_valid_urls:  # Iterate merged URLs
        if candidate_url in seen_urls:  # Verify duplication
            continue  # Skip duplicate

        seen_urls.add(candidate_url)  # Register URL
        unique_urls.append(candidate_url)  # Append unique URL

    return sorted(unique_urls, key=lambda x: x.lower())  # Return sorted URLs


def resolve_outputs_fallback(urls: List[str], affiliate_pattern: str) -> Tuple[List[str], bool, Dict[str, List[str]]]:
    """
    Resolves Outputs fallback scan when no valid URLs exist in primary sources.

    :param urls: Current URL list.
    :param affiliate_pattern: Pattern used for scanning.
    :return: Updated URLs, fallback mode flag, and fallback map.
    """

    fallback_outputs_mode = False  # Initialize fallback mode flag
    fallback_outputs_url_map: Dict[str, List[str]] = {}  # Initialize fallback map

    if len(urls) == 0:  # Verify empty merged result
        fallback_outputs_mode = True  # Enable fallback mode

        outputs_dir = resolve_outputs_directory()  # Resolve outputs directory
        fallback_outputs_url_map = scan_outputs_for_amazon_urls(str(outputs_dir), affiliate_pattern)  # Scan outputs

        urls = sorted(fallback_outputs_url_map.keys())  # Build URL list from fallback map

        if len(urls) == 0:  # Verify fallback failure
            print(f"{BackgroundColors.YELLOW}[WARNING] No valid Amazon URLs found in Outputs fallback scan.{Style.RESET_ALL}")  # Log failure

    return urls, fallback_outputs_mode, fallback_outputs_url_map  # Return fallback result


def setup_only_renew_amazon_urls(tab_count: int, urls: List[str], urls_file: Path, affiliate_pattern: str) -> Tuple[List[str], bool, Dict[str, List[str]], int]:
    """
    Builds final URL list for only-renew mode with validation, deduplication, and fallback scanning.

    :param tab_count: Requested number of URLs.
    :param urls: Initial URL list.
    :param urls_file: Path to URLs file.
    :param affiliate_pattern: Amazon URL pattern.
    :return: Final URLs, fallback flag, fallback map, updated tab count.
    """

    tab_count = resolve_urls_tab_count(tab_count, urls)  # Normalize tab count

    primary_urls_file, backup_urls_file = resolve_url_files(urls_file)  # Resolve file paths

    urls = extract_and_validate_urls(primary_urls_file, backup_urls_file, affiliate_pattern)  # Extract and validate URLs

    urls, fallback_outputs_mode, fallback_outputs_url_map = resolve_outputs_fallback(urls, affiliate_pattern)  # Resolve fallback scan

    tab_count = len(urls)  # Update tab count
    
    verbose_output(f"{BackgroundColors.GREEN}[INFO] Total URLs found for Amazon Affiliate Links Renewal: {BackgroundColors.CYAN}{len(urls)}{Style.RESET_ALL}")  # Log final URLs list for renewal

    return urls, fallback_outputs_mode, fallback_outputs_url_map, tab_count  # Return final state


def open_chrome_download_settings_page(open_in_new_tab: bool = True) -> bool:
    """
    Opens the Chrome downloads settings page, optionally in a new tab.

    :param open_in_new_tab: Whether to open a fresh tab before navigating.
    :return: True when the settings page is opened, otherwise False.
    """

    try:  # Attempt to open or reuse the current tab for the Chrome downloads settings page.
        if open_in_new_tab:  # Verify whether a new tab should be created for the settings page.
            pyautogui.hotkey("ctrl", "t")  # Open a new Chrome tab for downloads settings when requested.
            time.sleep(0.2)  # Wait after opening the settings tab.

        pyautogui.hotkey("ctrl", "l")  # Focus the address bar in the current tab.
        time.sleep(0.08)  # Wait after focusing the address bar.
        pyautogui.hotkey("ctrl", "a")  # Select any existing address-bar text.
        time.sleep(0.05)  # Wait after selecting the address-bar text.
        pyautogui.press("backspace")  # Clear the selected address-bar text.
        time.sleep(0.05)  # Wait after clearing the address-bar text.
        pyautogui.typewrite(CHROME_DOWNLOAD_SETTINGS_URL, interval=0.0)  # Type the Chrome downloads settings URL into the address bar.
        time.sleep(0.1)  # Wait after typing the settings URL.
        pyautogui.press("enter")  # Navigate to the Chrome downloads settings page.
        time.sleep(DOWNLOAD_SETTINGS_RENDER_WAIT_SECONDS)  # Wait for the Chrome downloads settings page to render.
        return True  # Return success after opening or navigating to the downloads settings page.
    except Exception:  # Handle settings navigation failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to open Chrome downloads settings page.{Style.RESET_ALL}")  # Log downloads settings page opening failure.
        return False  # Return failure when the downloads settings page cannot be opened.


def get_chrome_download_settings_region() -> Tuple[int, int, int, int] | None:
    """
    Resolves the Chrome downloads settings capture region.

    :param: None.
    :return: Tuple with left, top, width, and height or None when unavailable.
    """

    window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds for region capture.
    left = int(window_bounds.get("left", 0))  # Resolve left coordinate for region capture, preserving negative secondary-monitor offsets.
    top = int(window_bounds.get("top", 0))  # Resolve top coordinate for region capture, preserving negative secondary-monitor offsets.
    width = max(1, int(window_bounds.get("width", 0)))  # Resolve safe width for region capture.
    height = max(1, int(window_bounds.get("height", 0)))  # Resolve safe height for region capture.

    if width <= 0 or height <= 0:  # Verify whether the resolved region dimensions are invalid.
        return None  # Return None when the Chrome settings capture region is unavailable.

    return left, top, width, height  # Return the Chrome settings capture region tuple.


def diagnose_screenshot_capability() -> Tuple[bool, str]:
    """
    Diagnoses whether pyautogui screenshot capability is working.

    :return: Tuple of (is_working: bool, diagnostic_message: str)
    """

    try:  # Attempt to take a screenshot to diagnose screenshot capability.
        screenshot = pyautogui.screenshot()  # Attempt to capture screenshot from screen.
        if screenshot is None:  # Verify whether screenshot was successfully captured.
            return False, "Screenshot returned None"  # Return failure with diagnostic message.
        size = screenshot.size  # Retrieve screenshot image size dimensions.
        return True, f"Screenshot working - Size: {size}"  # Return success with diagnostic message.
    except Exception as e:  # Handle screenshot diagnostic exceptions.
        error_details = traceback.format_exc()  # Capture full exception traceback for diagnostic purposes.
        return False, f"Screenshot failed: {str(e)} | Traceback: {error_details}"  # Return failure with diagnostic details.


def get_virtual_desktop_bounds() -> Tuple[int, int, int, int]:
    """
    Retrieves the bounding rectangle covering all connected monitors as a virtual desktop.

    :param: None.
    :return: Tuple of left, top, right, bottom spanning the full virtual desktop across all monitors.
    """

    try:  # Attempt Windows monitor enumeration to resolve full virtual desktop bounds.
        monitor_rects: List[Tuple[int, int, int, int]] = []  # Initialize monitor bounds collection.

        MonitorEnumProc = ctypes.WINFUNCTYPE(  # Define monitor enumeration callback signature.
            ctypes.c_bool,  # Return type: BOOL for continuation control.
            ctypes.c_void_p,  # HMONITOR handle argument.
            ctypes.c_void_p,  # HDC handle argument.
            ctypes.POINTER(ctypes.wintypes.RECT),  # LPRECT pointer to monitor rectangle.
            ctypes.c_ssize_t,  # LPARAM user data argument.
        )  # Finalize Windows MONITORENUMPROC callback type definition.

        callback_func = MonitorEnumProc(monitor_enum_callback)  # Create stable callback reference to prevent garbage collection.
        ctypes.windll.user32.EnumDisplayMonitors(None, None, callback_func, 0)  # Enumerate all connected display monitors.

        if monitor_rects:  # Verify whether any monitor bounds were collected.
            vd_left = min(r[0] for r in monitor_rects)  # Compute virtual desktop left boundary from all monitor origins.
            vd_top = min(r[1] for r in monitor_rects)  # Compute virtual desktop top boundary from all monitor origins.
            vd_right = max(r[2] for r in monitor_rects)  # Compute virtual desktop right boundary from all monitor extents.
            vd_bottom = max(r[3] for r in monitor_rects)  # Compute virtual desktop bottom boundary from all monitor extents.
            return vd_left, vd_top, vd_right, vd_bottom  # Return full virtual desktop bounding rectangle.
    except Exception:  # Handle monitor enumeration failures gracefully.
        pass  # Continue to fallback when enumeration fails.

    screen_size = pyautogui.size()  # Retrieve primary monitor size as fallback.
    return 0, 0, int(screen_size.width), int(screen_size.height)  # Return primary monitor bounds as virtual desktop fallback.


def locate_image_in_region(image_path: Path, region: Tuple[int, int, int, int] | None, confidence: float = 0.9) -> Any:
    """
    Locates an image on screen inside an optional region.

    :param image_path: Path to the image file.
    :param region: Optional screen region tuple used during image search.
    :param confidence: Matching confidence threshold for image recognition.
    :return: Box location when found, otherwise None.
    """

    if not image_path.exists():  # Verify image file existence before image search.
        print(f"{BackgroundColors.RED}[DEBUG] Image file not found: {image_path}{Style.RESET_ALL}")  # Log missing image file for diagnostic purposes.
        return None  # Return None when image file does not exist.

    try:  # Attempt image location on screen using multi-monitor capture.
        template = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)  # Load template image in grayscale for matching.

        if template is None:  # Verify template loading success.
            return None  # Return None when template loading fails.

        vd_left, vd_top, vd_right, vd_bottom = get_virtual_desktop_bounds()  # Retrieve full virtual desktop bounds for coordinate conversion.

        if region is not None:  # Verify whether a capture region was provided for the image search.
            reg_left, reg_top, reg_width, reg_height = region  # Unpack region components for bounded capture.
            screenshot = ImageGrab.grab(bbox=(reg_left, reg_top, reg_left + reg_width, reg_top + reg_height), all_screens=True)  # Capture specified region across all monitors.
            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)  # Convert region screenshot to grayscale for matching.
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)  # Perform normalized cross-correlation template matching.
            _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Extract best match location and confidence score.

            if max_val < confidence:  # Verify match confidence meets threshold.
                return None  # Return None when match confidence is insufficient.

            x_img, y_img = max_loc  # Unpack image-space match coordinates.
            h_t, w_t = template.shape[:2]  # Extract template height and width for bounding box.
            return Box(left=reg_left + x_img, top=reg_top + y_img, width=w_t, height=h_t)  # Return virtual desktop coordinates as Box for region match.

        screenshot = ImageGrab.grab(bbox=(vd_left, vd_top, vd_right, vd_bottom), all_screens=True)  # Capture full virtual desktop across all monitors.
        screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)  # Convert full screenshot to grayscale for matching.
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)  # Perform normalized cross-correlation template matching.
        _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Extract best match location and confidence score.

        if max_val < confidence:  # Verify match confidence meets threshold.
            return None  # Return None when match confidence is insufficient.

        x_img, y_img = max_loc  # Unpack image-space match coordinates.
        h_t, w_t = template.shape[:2]  # Extract template height and width for bounding box.
        return Box(left=vd_left + x_img, top=vd_top + y_img, width=w_t, height=h_t)  # Return virtual desktop coordinates as Box for full-screen match.
    except Exception:  # Handle image search exceptions.
        return None  # Return None when image search fails.


def locate_image_variants(image_paths: List[Path]) -> Any:
    """
    Attempts to locate an image from multiple candidate variant paths.

    :param image_paths: List of image file paths to test in sequence.
    :return: Bounding box when any variant matches, otherwise None.
    """

    for image_path in image_paths:  # Iterate through image variant candidates in priority order.
        if not image_path.exists():  # Verify whether the image file exists before attempting detection.
            print(f"{BackgroundColors.RED}Image file not found: {BackgroundColors.GREEN}{image_path}{Style.RESET_ALL}")  # Log missing image file for diagnostic purposes.
            continue  # Skip to next image variant when current file does not exist.

        box = locate_image(image_path)  # Attempt to locate the current image variant in the capture region.

        if box is not None:  # Verify whether the current image variant was successfully detected.
            return box  # Return matched bounding box immediately upon first successful match.

    return None  # Return None when no image variants match.


def detect_chrome_download_settings_state(correct_imgs: List[Path], wrong_toggle_1_imgs: List[Path], wrong_toggle_2_imgs: List[Path], wrong_both_imgs: List[Path]) -> Tuple[str, Any]:
    """
    Detects the current Chrome downloads settings toggle state using dual-theme image variants.

    :param correct_imgs: List of image paths representing the correct settings state (both color variants).
    :param wrong_toggle_1_imgs: List of image paths representing Toggle 1 enabled (both color variants).
    :param wrong_toggle_2_imgs: List of image paths representing Toggle 2 enabled (both color variants).
    :param wrong_both_imgs: List of image paths representing both toggles enabled (both color variants).
    :return: Tuple containing the detected state label and matched bounding box.
    """

    image_candidates = [  # Define ordered image candidate groups for state detection.
        (DOWNLOAD_SETTINGS_STATE_CORRECT, correct_imgs),  # Define the correct settings-state variants.
        (DOWNLOAD_SETTINGS_STATE_TOGGLE_1_ON, wrong_toggle_1_imgs),  # Define the Toggle 1 enabled variants.
        (DOWNLOAD_SETTINGS_STATE_TOGGLE_2_ON, wrong_toggle_2_imgs),  # Define the Toggle 2 enabled variants.
        (DOWNLOAD_SETTINGS_STATE_BOTH_TOGGLES_ON, wrong_both_imgs),  # Define the both-toggles-enabled variants.
    ]  # Finalize ordered image candidate groups for state detection.

    for state_name, image_paths in image_candidates:  # Iterate downloads settings state candidates in priority order.
        box = locate_image_variants(image_paths)  # Attempt to locate any color variant of the current state image.

        if box is not None:  # Verify whether the current state was successfully detected from any color variant.
            return state_name, box  # Return the detected downloads settings state and bounding box.

    print(f"{BackgroundColors.YELLOW}[WARNING] Unable to detect Chrome downloads settings toggle state.{Style.RESET_ALL}")  # Log unresolved downloads settings state warning.
    return DOWNLOAD_SETTINGS_STATE_UNKNOWN, None  # Return unresolved downloads settings state when no image variants match.


def resolve_download_settings_toggle_click_position(box: Any, toggle_number: int) -> Tuple[int, int]:
    """
    Resolves the click position for a downloads settings toggle.

    :param box: Matched bounding box for the downloads settings state image.
    :param toggle_number: Toggle index where 1 is the middle toggle and 2 is the bottom toggle.
    :return: Tuple containing the click X and Y coordinates.
    """

    left = int(getattr(box, "left", 0))  # Retrieve the matched bounding-box left coordinate.
    top = int(getattr(box, "top", 0))  # Retrieve the matched bounding-box top coordinate.
    width = max(1, int(getattr(box, "width", 1)))  # Retrieve the matched bounding-box width using a safe minimum.
    height = max(1, int(getattr(box, "height", 1)))  # Retrieve the matched bounding-box height using a safe minimum.
    click_x = left + int(width / 2)  # Compute the horizontal center of the matched bounding box.

    if toggle_number == 1:  # Verify whether the first downloads settings toggle position was requested.
        click_y = top + int(height * 0.5)  # Compute the first toggle vertical position from the matched bounding box.
    else:  # Resolve the second downloads settings toggle position as fallback.
        click_y = top + int(height * 5 / 6)  # Compute the second toggle vertical position from the matched bounding box.

    return click_x, click_y  # Return the resolved toggle click coordinates.


def disable_chrome_download_toggle_1(box: Any) -> None:
    """
    Disables the first Chrome downloads settings toggle.

    :param box: Matched bounding box for the downloads settings state image.
    :return: None.
    """

    click_x, click_y = resolve_download_settings_toggle_click_position(box, 1)  # Resolve the click position for the first downloads settings toggle.
    pyautogui.click(click_x, click_y)  # Click the first downloads settings toggle.
    time.sleep(DOWNLOAD_SETTINGS_TOGGLE_CLICK_WAIT_SECONDS)  # Wait after disabling the first downloads settings toggle.


def disable_chrome_download_toggle_2(box: Any) -> None:
    """
    Disables the second Chrome downloads settings toggle.

    :param box: Matched bounding box for the downloads settings state image.
    :return: None.
    """

    click_x, click_y = resolve_download_settings_toggle_click_position(box, 2)  # Resolve the click position for the second downloads settings toggle.
    pyautogui.click(click_x, click_y)  # Click the second downloads settings toggle.
    time.sleep(DOWNLOAD_SETTINGS_TOGGLE_CLICK_WAIT_SECONDS)  # Wait after disabling the second downloads settings toggle.


def disable_both_chrome_download_toggles(box: Any) -> None:
    """
    Disables both Chrome downloads settings toggles.

    :param box: Matched bounding box for the downloads settings state image.
    :return: None.
    """

    disable_chrome_download_toggle_1(box)  # Disable the first downloads settings toggle.
    disable_chrome_download_toggle_2(box)  # Disable the second downloads settings toggle.


def correct_chrome_download_settings_state(correct_imgs: List[Path], wrong_toggle_1_imgs: List[Path], wrong_toggle_2_imgs: List[Path], wrong_both_imgs: List[Path]) -> bool:
    """
    Corrects the Chrome downloads settings state using iterative re-detection.

    :param correct_imgs: List of image paths representing the correct settings state.
    :param wrong_toggle_1_imgs: List of image paths representing Toggle 1 enabled.
    :param wrong_toggle_2_imgs: List of image paths representing Toggle 2 enabled.
    :param wrong_both_imgs: List of image paths representing both toggles enabled.
    :return: True when settings reach the correct state, otherwise False.
    """

    max_correction_cycles = 4  # Limit correction loops to avoid infinite retries.

    for _ in range(max_correction_cycles):  # Iterate correction cycles with fresh state detection after each click.
        detected_state, matched_box = detect_chrome_download_settings_state(correct_imgs, wrong_toggle_1_imgs, wrong_toggle_2_imgs, wrong_both_imgs)  # Detect current settings state.

        if detected_state == DOWNLOAD_SETTINGS_STATE_CORRECT:  # Verify whether settings are already in the expected state.
            return True  # Return success when no additional correction is required.

        if detected_state == DOWNLOAD_SETTINGS_STATE_UNKNOWN or matched_box is None:  # Verify whether state detection failed.
            return False  # Return failure when state cannot be resolved for correction.

        if detected_state == DOWNLOAD_SETTINGS_STATE_TOGGLE_1_ON:  # Verify whether only the first toggle is enabled.
            disable_chrome_download_toggle_1(matched_box)  # Disable the first toggle using a fresh matched box.
            continue  # Continue loop for re-detection.

        if detected_state == DOWNLOAD_SETTINGS_STATE_TOGGLE_2_ON:  # Verify whether only the second toggle is enabled.
            disable_chrome_download_toggle_2(matched_box)  # Disable the second toggle using a fresh matched box.
            continue  # Continue loop for re-detection.

        if detected_state == DOWNLOAD_SETTINGS_STATE_BOTH_TOGGLES_ON:  # Verify whether both toggles are enabled.
            disable_chrome_download_toggle_1(matched_box)  # Disable one toggle first and re-detect before second click.
            continue  # Continue loop so next cycle handles the remaining enabled toggle with a fresh box.

    return False  # Return failure when correction cycles are exhausted without reaching correct state.


def move_cursor_to_active_window_center() -> None:
    """
    Moves the cursor to the center of the active Chrome window.

    :param: None.
    :return: None.
    """

    window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds for pointer repositioning.
    center_x = int(window_bounds["left"] + (window_bounds["width"] / 2))  # Compute the active Chrome window horizontal center.
    center_y = int(window_bounds["top"] + (window_bounds["height"] / 2))  # Compute the active Chrome window vertical center.
    pyautogui.moveTo(center_x, center_y)  # Move the cursor to the center of the active Chrome window.
    time.sleep(DOWNLOAD_SETTINGS_TOGGLE_CLICK_WAIT_SECONDS)  # Wait after moving the cursor away from the toggles.


def verify_chrome_download_settings_correct_state(correct_imgs: List[Path]) -> bool:
    """
    Verifies the final Chrome downloads settings state using dual-theme image variants.

    :param correct_imgs: List of image paths representing the correct settings state (both color variants).
    :return: True when the correct settings state is detected, otherwise False.
    """

    move_cursor_to_active_window_center()  # Move the cursor away from the downloads settings block before verification.

    for _ in range(DOWNLOAD_SETTINGS_VERIFICATION_ATTEMPTS):  # Iterate the configured number of final-state verification attempts.
        if locate_image_variants(correct_imgs) is not None:  # Verify whether any correct downloads settings image variant is now detected.
            return True  # Return success when the correct downloads settings state is detected.

        time.sleep(DOWNLOAD_SETTINGS_VERIFICATION_WAIT_SECONDS)  # Wait before retrying final-state verification.

    print(f"{BackgroundColors.YELLOW}[WARNING] Chrome downloads settings remain in an unexpected state after correction attempt.{Style.RESET_ALL}")  # Log final-state verification failure.
    return False  # Return failure when the correct downloads settings state is not detected.


def close_chrome_download_settings_tab() -> bool:
    """
    Closes the Chrome downloads settings tab and restores focus.

    :param: None.
    :return: True when focus returns to Chrome, otherwise False.
    """

    try:  # Attempt to close the Chrome downloads settings tab.
        close_current_tab()  # Close the active Chrome downloads settings tab.
    except Exception:  # Handle downloads settings tab close failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close Chrome downloads settings tab cleanly.{Style.RESET_ALL}")  # Log downloads settings tab close failure.
        return False  # Return failure when the downloads settings tab cannot be closed.

    return activate_automation_window()  # Restore dedicated automation window focus after closing the downloads settings tab.


def verify_and_correct_chrome_download_settings(assets_dir: Path, open_in_new_tab: bool = True) -> bool:
    """
    Verifies and corrects Chrome downloads settings before automation starts.

    :param assets_dir: Path to the browser assets directory.
    :param open_in_new_tab: Whether to open the settings page in a new tab.
    :return: True when Chrome downloads settings are ready, otherwise False.
    """

    correct_imgs = [assets_dir / "AskUserDownload - Black - Confirmation - Correct.png", assets_dir / "AskUserDownload - White - Confirmation - Correct.png"]  # Define image paths for the correct downloads settings state (both color variants).
    wrong_toggle_1_imgs = [assets_dir / "AskUserDownloadConfirmation - Black - Wrong - Toggle 1 On.png", assets_dir / "AskUserDownloadConfirmation - White - Wrong - Toggle 1 On.png"]  # Define image paths for Toggle 1 enabled (both color variants).
    wrong_toggle_2_imgs = [assets_dir / "AskUserDownloadConfirmation - Black - Wrong - Toggle 2 On.png", assets_dir / "AskUserDownloadConfirmation - White - Wrong - Toggle 2 On.png"]  # Define image paths for Toggle 2 enabled (both color variants).
    wrong_both_imgs = [assets_dir / "AskUserDownloadConfirmation - Black - Wrong - Both Toggles On.png", assets_dir / "AskUserDownloadConfirmation - White - Wrong - Both Toggles On.png"]  # Define image paths for both toggles enabled (both color variants).

    if not open_chrome_download_settings_page(open_in_new_tab=open_in_new_tab):  # Verify whether the Chrome downloads settings page was opened successfully.
        return False  # Return failure when the Chrome downloads settings page cannot be opened.

    correction_result = correct_chrome_download_settings_state(correct_imgs, wrong_toggle_1_imgs, wrong_toggle_2_imgs, wrong_both_imgs)  # Correct settings state with iterative re-detection between clicks.

    if not correction_result:  # Verify whether automatic settings correction failed.
        close_result = close_chrome_download_settings_tab()  # Close the downloads settings tab before aborting.

        if not close_result:  # Verify whether Chrome focus restoration succeeded after aborting.
            print(f"{BackgroundColors.YELLOW}[WARNING] Chrome focus restoration failed after downloads settings detection error.{Style.RESET_ALL}")  # Log Chrome focus restoration failure after aborting.

        return False  # Return failure when the downloads settings state cannot be resolved.

    verified = verify_chrome_download_settings_correct_state(correct_imgs)  # Verify whether the downloads settings are now in the correct state using all color variants.
    close_result = close_chrome_download_settings_tab()  # Close the downloads settings tab and restore Chrome focus.

    if not close_result:  # Verify whether Chrome focus restoration succeeded after settings handling.
        print(f"{BackgroundColors.YELLOW}[WARNING] Chrome focus restoration failed after downloads settings handling.{Style.RESET_ALL}")  # Log Chrome focus restoration failure after settings handling.
        return False  # Return failure when Chrome focus cannot be restored.

    return verified  # Return final downloads settings verification result.


def setup_method_maps() -> Tuple[Dict[str, List[int]], Dict[str, List[int]], Dict[str, List[int]], Dict[str, List[int]]]:
    """
    Initializes and returns grouped automation method maps.

    :return: Tuple containing extension, download, completion, and close method maps.
    """

    ext_methods: Dict[str, List[int]] = {}  # Initialize extension method map
    download_methods: Dict[str, List[int]] = {}  # Initialize download method map
    completion_methods: Dict[str, List[int]] = {}  # Initialize completion method map
    close_methods: Dict[str, List[int]] = {}  # Initialize close tab method map

    return ext_methods, download_methods, completion_methods, close_methods  # Return all method maps


def notify_manual_chrome_download_settings_intervention(url: str) -> None:
    """
    Requests manual Chrome downloads settings correction after first-URL download failure.

    :param url: URL that failed to produce the expected compressed download.
    :return: None.
    """

    print(f"{BackgroundColors.YELLOW}[WARNING] No compressed download was detected for the first URL after Chrome downloads settings verification failed earlier: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}")  # Log the first-URL compressed download failure after prior settings verification failure.
    print(f"{BackgroundColors.YELLOW}[WARNING] Disable \"Ask where to save each file before downloading\" in Chrome downloads settings before continuing.{Style.RESET_ALL}")  # Instruct the user to disable the Chrome prompt-for-save setting.
    print(f"{BackgroundColors.YELLOW}[WARNING] Open this URL in Chrome now: {BackgroundColors.CYAN}{CHROME_DOWNLOAD_SETTINGS_URL}{Style.RESET_ALL}")  # Instruct the user to open the Chrome downloads settings URL.
    print(f"{BackgroundColors.YELLOW}[WARNING] Stopping the remaining URL processing to avoid invalid automation results.{Style.RESET_ALL}")  # Inform that the remaining URLs will not be processed.

    if activate_automation_window():  # Verify whether the automation Chrome window can be activated before opening the settings URL.
        if not open_chrome_download_settings_page():  # Verify whether the Chrome downloads settings page could be opened automatically.
            print(f"{BackgroundColors.YELLOW}[WARNING] Failed to open Chrome downloads settings automatically. Open it manually using the URL above.{Style.RESET_ALL}")  # Instruct the user to open the settings URL manually when automatic navigation fails.


def handle_initial_chrome_download_failures(chrome_download_settings_ready: bool, index: int, detected_filename: str, initial_consecutive_download_failures: int, url: str, processed_count: int, url_to_download: Dict[str, str]) -> Tuple[int, Tuple[int, Dict[str, str], bool] | None]:
    """
    Handle initial Chrome download failures and request manual intervention when needed.

    :param chrome_download_settings_ready: Whether Chrome downloads settings were previously verified.
    :param index: Current URL processing index (1-based).
    :param detected_filename: Detected downloaded filename for current URL.
    :param initial_consecutive_download_failures: Current consecutive initial download failures count.
    :param url: URL associated with current processing cycle.
    :param processed_count: Number of URLs processed so far.
    :param url_to_download: Mapping from URL to detected downloaded filename.
    :return: Tuple of updated failures count and optional abort tuple when manual intervention is requested.
    """

    if not chrome_download_settings_ready and index <= 3:  # Verify whether downloads settings unresolved and index within the first three
        if detected_filename == "":  # Verify whether current URL produced no detected compressed download
            initial_consecutive_download_failures += 1  # Increment consecutive initial download-failure counter
        else:  # Handle a detected compressed download within the first three processed URLs
            initial_consecutive_download_failures = 0  # Reset the consecutive initial download-failure counter

        if index == 3 and initial_consecutive_download_failures == 3:  # Verify whether the first three processed URLs failed consecutively
            notify_manual_chrome_download_settings_intervention(url)  # Request manual Chrome downloads settings correction and attempt to open the settings page
            return initial_consecutive_download_failures, (processed_count, url_to_download, False)  # Return abort tuple to stop processing remaining URLs

    return initial_consecutive_download_failures, None  # Return updated failures count and no abort when continuing


def detect_split_zip_fragment_start(filename: str) -> Tuple[bool, str]:
    """
    Detect whether a downloaded filename is the first fragment of a split ZIP archive (.zNN format).

    Split ZIP archives use sequential parts like:
    - file.z01
    - file.z02
    - ...
    - file.zip (final container)

    This function identifies whether the given file is part of such a fragmented sequence and extracts
    the base name used to track the full archive chain.

    :param filename: Detected downloaded filename to evaluate.
    :return: Tuple of (is_split_fragment, base_name_without_extension).
    """

    lower = filename.lower()  # Normalize filename for extension comparison.
    is_fragment = bool(re.search(r"\.z\d{2}$", lower))  # Verify whether the filename ends with a .zNN pattern indicating a fragmented ZIP first-part.
    base_name = Path(filename).stem  # Extract the base name without the .zNN extension for downstream polling of the expected final ZIP file.

    if not is_fragment:  # Verify whether filename ends with .zNN fragmented archive suffix.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] No ZIP fragment detected in filename: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}")  # Log absence of fragmentation when filename does not match .zNN pattern.
        return False, ""  # Return not-fragmented when filename does not match .zNN pattern.

    base_name = Path(filename).stem  # Extract base name without the .zNN extension.
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Fragment detected: {BackgroundColors.CYAN}{filename}{BackgroundColors.GREEN} — tracking full ZIP chain.{Style.RESET_ALL}")  # Log fragmented archive detection.

    return True, base_name  # Return fragmented flag and base name for downstream polling.


def wait_for_zip_fragmented_chain_completion(downloads_dir: str, base_name: str) -> bool:
    """
    Poll downloads directory every 1 second until the full ZIP chain is completed.

    The completion condition requires:
    - Presence of the final .zip file
    - At least one fragmented part (.z01, .z02, etc.)

    :param downloads_dir: Resolved path to the downloads directory to poll.
    :param base_name: Base filename without extension to construct the expected ZIP family.
    :return: True when the full ZIP chain is detected, otherwise False.
    """

    dir_path = Path(downloads_dir)  # Resolve downloads directory path.
    final_zip = dir_path / f"{base_name}.zip"  # Build expected final ZIP path.

    elapsed_seconds = 0  # Initialize elapsed seconds counter for periodic INFO logging.
    notify_interval = 10  # Define interval in seconds between wait-status messages.

    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Waiting for full ZIP chain: {BackgroundColors.CYAN}{base_name}.z[0-9][0-9]{BackgroundColors.GREEN} + {BackgroundColors.CYAN}.zip{BackgroundColors.GREEN} in {downloads_dir}{Style.RESET_ALL}")  # Log initial wait start message.

    while True:  # Poll indefinitely until ZIP chain is complete.
        fragments = list(dir_path.glob(f"{base_name}.z[0-9][0-9]"))  # Collect all fragment parts.

        if final_zip.exists() and len(fragments) > 0:  # Verify whether full ZIP chain is complete.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Full ZIP chain detected ({BackgroundColors.CYAN}{len(fragments)}{BackgroundColors.GREEN} parts + {BackgroundColors.CYAN}.zip{BackgroundColors.GREEN}).{Style.RESET_ALL}")  # Log ZIP chain completion.
            return True  # Return success when full chain is detected.

        time.sleep(1)  # Wait 1 second before re-polling.
        elapsed_seconds += 1  # Increment elapsed seconds tracker.

        if elapsed_seconds % notify_interval == 0:  # Verify whether notify interval has elapsed.
            print(f"{BackgroundColors.GREEN}[DEBUG] Waiting ZIP chain {base_name} — {BackgroundColors.CYAN}{elapsed_seconds}s{BackgroundColors.GREEN} elapsed.{Style.RESET_ALL}")  # Print periodic wait notification.


def initialize_git_submodules(submodule_dir: Path) -> Path | None:
    """
    Initialize git submodules when directory is missing or empty.

    :param submodule_dir: Path to the target submodule directory.
    :return: The submodule directory path if initialization succeeds, otherwise None.
    """

    if not submodule_dir.exists() or not any(submodule_dir.iterdir()):  # Verify whether submodule directory is present and non-empty.
        print(f"{BackgroundColors.GREEN}[DEBUG] Submodule directory missing or empty — initializing via git submodule update.{Style.RESET_ALL}")  # Log submodule initialization attempt.
        init_result = subprocess.run(["git", "submodule", "update", "--init", "--recursive"], capture_output=True, text=True, cwd=PROJECT_ROOT)  # Run git submodule init from project root.

        if init_result.returncode != 0:  # Verify whether submodule initialization succeeded.
            print(f"{BackgroundColors.YELLOW}[WARNING] git submodule update failed: {init_result.stderr.strip()}{Style.RESET_ALL}")  # Log submodule initialization failure.
            return None  # Return None when submodule cannot be initialized.

    return submodule_dir  # Return validated submodule directory path.


def resolve_submodule_path() -> Path:
    """
    Resolve the Multi-Fragmented-ZipFile-Extractor submodule path.

    :param: None.
    :return: Resolved submodule Path.
    """

    submodule_dir = Path(PROJECT_ROOT) / "Multi-Fragmented-ZipFile-Extractor"  # Build submodule root path from project root.

    initialize_git_submodules(submodule_dir)  # Ensure submodule is initialized.

    return submodule_dir  # Return resolved submodule directory.


def resolve_java_jar_path(submodule_dir: Path) -> Path | None:
    """
    Resolve the JAR path inside Multi-Fragmented-ZipFile-Extractor/target/.

    :param submodule_dir: Path to the submodule directory.
    :return: Resolved JAR Path when found, otherwise None.
    """

    target_dir = submodule_dir / "target"  # Build Maven target directory path.

    if not target_dir.exists():  # Verify whether the Maven target directory exists.
        return None  # Return None when target directory is absent.

    jar_candidates = [
        p for p in target_dir.glob("*.jar")
        if not p.name.startswith("original-")
    ]  # Discover all non-original JAR files inside target directory.

    if len(jar_candidates) == 0:  # Verify whether any JAR candidates were found.
        return None  # Return None when no JAR exists in target directory.

    return max(jar_candidates, key=lambda p: p.stat().st_mtime)  # Return most recently modified JAR candidate.


def resolve_existing_jar(submodule_dir: Path) -> Path | None:
    """
    Resolve an existing JAR file from the submodule target directory.

    :param submodule_dir: Path to the submodule directory.
    :return: Resolved JAR Path if available, otherwise None.
    """

    jar_path = resolve_java_jar_path(submodule_dir)  # Attempt to resolve JAR from target directory.

    if jar_path is not None:  # Verify whether JAR exists locally.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Java jar resolved (cached): {BackgroundColors.CYAN}{jar_path}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log cached JAR resolution.
        return jar_path  # Return resolved JAR path.

    return None  # Return None when no JAR is available.


def run_executable(executable_names: list[str], args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """
    Resolves and executes a system binary in a cross-platform safe way.

    :param executable_names: List of possible executable names (e.g. ["java"], ["mvn", "mvn.cmd", "mvn.bat"]).
    :param args: Arguments to pass to the executable.
    :param cwd: Working directory for execution.
    :return: Completed subprocess result.
    """

    resolved_exe = None  # Initialize resolved executable path.

    for name in executable_names:  # Iterate through possible executable variants.
        resolved_exe = shutil.which(name)  # Attempt to resolve executable in PATH.

        if resolved_exe is not None:  # Verify if executable was found.
            break  # Stop at first valid match.

    if resolved_exe is None:  # Verify whether any executable was resolved.
        raise FileNotFoundError(f"None of the executables were found: {executable_names}")  # Fail fast with context.

    return subprocess.run([resolved_exe, *args], capture_output=True, text=True, cwd=cwd)  # Execute safely.


def verify_java_available() -> bool:
    """
    Verify Java availability on the system.

    :param: None.
    :return: True when Java is available, otherwise False.
    """

    java_result = run_executable(["java"], ["--version"])  # Verify Java availability cross-platform.

    if java_result.returncode != 0:  # Verify whether Java is present on the system.
        print(f"{BackgroundColors.YELLOW}[WARNING] Java not found. Cannot build Multi-Fragmented-ZipFile-Extractor JAR. See: https://github.com/BrenoFariasdaSilva/Multi-Fragmented-ZipFile-Extractor#installation. Falling back to local JAR if available.{Style.RESET_ALL}")  # Log Java missing warning.
        return False  # Return False when Java is unavailable.

    return True  # Return True when Java is available.


def verify_maven_available() -> bool:
    """
    Verify Maven availability on the system.

    :param: None.
    :return: True when Maven is available, otherwise False.
    """

    mvn_result = run_executable(["mvn", "mvn.cmd", "mvn.bat"], ["--version"])  # Verify Maven availability cross-platform.

    if mvn_result.returncode != 0:  # Verify whether Maven is present on the system.
        print(f"{BackgroundColors.YELLOW}[WARNING] Maven not found. Cannot build Multi-Fragmented-ZipFile-Extractor JAR. See: https://github.com/BrenoFariasdaSilva/Multi-Fragmented-ZipFile-Extractor#installation. Falling back to local JAR if available.{Style.RESET_ALL}")  # Log Maven missing warning.
        return False  # Return False when Maven is unavailable.

    return True  # Return True when Maven is available.


def build_maven_project(submodule_dir: Path) -> subprocess.CompletedProcess:
    """
    Execute Maven clean package build.

    :param submodule_dir: Path to the submodule directory.
    :return: Maven build process result.
    """

    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Maven build executed — running {BackgroundColors.CYAN}mvn clean package{BackgroundColors.GREEN} in submodule.{Style.RESET_ALL}")  # Log Maven build execution.

    build_result = run_executable(
        ["mvn", "mvn.cmd", "mvn.bat"],  # Resolve Maven cross-platform.
        ["clean", "package"],  # Maven build arguments.
        cwd=str(submodule_dir)  # Execute inside submodule directory.
    )  # Run Maven clean package safely.

    return build_result  # Return build result.


def handle_build_failure(submodule_dir: Path, build_result: subprocess.CompletedProcess) -> Path | None:
    """
    Handle Maven build failure and attempt fallback JAR resolution.

    :param submodule_dir: Path to the submodule directory.
    :param build_result: Maven build process result.
    :return: Resolved JAR Path if available, otherwise None.
    """

    print(f"{BackgroundColors.YELLOW}[WARNING] mvn clean package failed: {build_result.stderr.strip()}{Style.RESET_ALL}")  # Log Maven build failure.
    print(f"{BackgroundColors.YELLOW}[WARNING] See: https://github.com/BrenoFariasdaSilva/Multi-Fragmented-ZipFile-Extractor#installation{Style.RESET_ALL}")  # Log installation reference.

    jar_path = resolve_java_jar_path(submodule_dir)  # Attempt fallback to existing JAR after failure.

    if jar_path is not None:  # Verify whether fallback JAR exists.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Java jar resolved (fallback after failure): {BackgroundColors.CYAN}{jar_path}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log fallback resolution.
        return jar_path  # Return fallback JAR.

    return None  # Return None when no JAR exists.


def resolve_or_build_java_jar(first_run: bool = True) -> Path | None:
    """
    Build or resolve the Multi-Fragmented-ZipFile-Extractor JAR.

    :param first_run: When True, forces build attempt; otherwise uses cached resolution only.
    :return: Resolved JAR Path if available, otherwise None.
    """

    submodule_dir = resolve_submodule_path()  # Resolve submodule directory.

    if not first_run:  # Verify whether build is skipped on non-first run.
        return resolve_existing_jar(submodule_dir)  # Return cached JAR if available.

    if not verify_java_available() or not verify_maven_available():  # Verify Java and Maven availability before attempting build.
        return resolve_existing_jar(submodule_dir)  # Attempt fallback JAR when Java or Maven is unavailable.

    build_result = build_maven_project(submodule_dir)  # Execute Maven build.

    if build_result.returncode != 0:  # Verify whether Maven build succeeded.
        return handle_build_failure(submodule_dir, build_result)  # Handle build failure and fallback.

    jar_path = resolve_java_jar_path(submodule_dir)  # Resolve JAR after successful build.

    if jar_path is None:  # Verify whether JAR was produced.
        print(f"{BackgroundColors.YELLOW}[WARNING] JAR not found in target/ after successful Maven build.{Style.RESET_ALL}")  # Log missing JAR after build.
        return None  # Return None when JAR is missing.

    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Java jar resolved: {BackgroundColors.CYAN}{jar_path}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log resolved JAR path.
    return jar_path  # Return resolved JAR path.


def run_zip_merge_java(jar_path: Path, zip_files: List[Path], output_zip: Path) -> bool:
    """
    Run the Java merge pipeline to combine fragmented ZIP parts into a single archive.

    :param jar_path: Absolute path to the Multi-Fragmented-ZipFile-Extractor JAR.
    :param zip_files: List of absolute paths to the .zip fragment companion files.
    :param output_zip: Absolute path for the merged output ZIP file.
    :return: True when merge succeeds, otherwise False.
    """

    jar_path_str = jar_path.resolve().as_posix()  # Normalize JAR path to POSIX format for Java compatibility.
    output_zip_str = output_zip.resolve().as_posix()  # Normalize output ZIP path to POSIX format for Java compatibility.

    zip_files_str = [
        p.resolve().as_posix()
        for p in zip_files
        if re.search(r"\.z\d{2}$", str(p).lower())
    ]  # Collect ZIP fragments (.z01, .z02, etc.) and normalize paths.

    def _extract_fragment_index(path: str) -> int:
        match = re.search(r"\.z(\d{2})$", path.lower())  # Extract fragment index safely.
        return int(match.group(1)) if match else 0  # Return numeric index or fallback.

    zip_files_str = sorted(
        zip_files_str,
        key=_extract_fragment_index
    )  # Sort fragments in correct numeric order for Java merge.

    zip_files_str += [
        p.resolve().as_posix()
        for p in zip_files
        if str(p).lower().endswith(".zip") and not re.search(r"\.z\d{2}\.zip$", str(p).lower())
    ]  # Append final ZIP file(s) after all fragments.

    command = ["java", "-jar", jar_path_str]  # Initialize Java base command with JAR execution.

    if VERBOSE:  # Verify whether verbose mode is enabled for debugging output.
        command.append("--log=DEBUG")  # Append verbose logging argument in correct CLI position.

    command.append(output_zip_str)  # Append output ZIP path as after optional logging argument but before the list of input ZIP fragments.
    command.extend(zip_files_str)  # Append all ZIP fragment inputs to command.

    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Executing Java merge fragment zip file command: {BackgroundColors.CYAN}{' '.join(command)}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log the exact Java command being executed
    
    try:  # Attempt Java execution.
        result = subprocess.run(command, capture_output=True, text=True)  # Execute Java process.
    except Exception as exc:  # Handle subprocess failure.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to execute Java merge command: {exc}{Style.RESET_ALL}")  # Log execution failure.
        return False  # Return failure.

    raw_output = result.stdout.strip() if result.stdout else ""  # Normalize stdout output.
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Raw Java output: {BackgroundColors.CYAN}{raw_output}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log raw Java output for debugging.

    try:  # Attempt to extract JSON from mixed output.
        json_matches = re.findall(r"\{.*\}", raw_output, re.DOTALL)  # Extract JSON objects from the raw output using regex, allowing for any surrounding text.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] JSON matches found in Java output: {BackgroundColors.CYAN}{json_matches}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log JSON matches found in the Java output for debugging.

        if not json_matches:  # Verify whether any JSON was found in the output.
            print(f"{BackgroundColors.YELLOW}[WARNING] No JSON found in Java output: {raw_output}{Style.RESET_ALL}")
            return False  # Return failure when no JSON is found to parse.

        json_match = json_matches[-1]  # Use the last JSON match found, assuming it's the most relevant status output from the Java process.

        parsed = json.loads(json_match)  # Parse extracted JSON.
        status = str(parsed.get("status", "")).lower()  # Extract status field.

        if status == "success":  # Verify success status.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Merge success: {BackgroundColors.CYAN}{parsed.get('output', '')}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log success.

            if not verify_filepath_exists(output_zip):  # Verify whether the expected merged ZIP file now exists after Java merge.
                print(f"{BackgroundColors.RED}[WARNING] Java merge reported success but output ZIP not found: {output_zip}{Style.RESET_ALL}")  # Log missing output ZIP warning.
                return False  # Return failure when output ZIP is not found after reported success.
            return True  # Return success.

        print(f"{BackgroundColors.RED}[WARNING] Java merge returned non-success status: {BackgroundColors.CYAN}{parsed}{Style.RESET_ALL}")  # Log failure status.
        print(f"{BackgroundColors.RED}[WARNING] Full Java output for context: {BackgroundColors.CYAN}{raw_output}{Style.RESET_ALL}")  # Log full raw output for additional context on failure.
        print(f"{BackgroundColors.RED}[WARNING] Executed command: {BackgroundColors.CYAN}{' '.join(command)}{Style.RESET_ALL}")  # Log executed command for context.
        return False  # Return failure for non-success status.
    except Exception:  # Handle parsing failure.
        print(f"{BackgroundColors.RED}[WARNING] Java merge output could not be parsed as JSON: {BackgroundColors.CYAN}{raw_output}{Style.RESET_ALL}")  # Log raw output.
        return False  # Return failure.


def finalize_fragments_cleanup(downloads_dir: str, base_name: str) -> str:
    """
    Delete fragmented artifacts and rename merged ZIP to canonical filename.

    :param downloads_dir: Resolved path to the downloads directory containing the artifacts.
    :param base_name: Base filename without extension shared by all fragmented parts.
    :return: Canonical ZIP filename after successful cleanup, or empty string on failure.
    """

    dir_path = Path(downloads_dir)  # Build Path instance for downloads directory.
    original_zip_path = dir_path / f"{base_name}.zip"  # Build absolute path to the original .zip companion.
    merged_zip_path = dir_path / f"{base_name}_merged.zip"  # Build absolute path to the Java-produced merged ZIP.
    canonical_zip_path = dir_path / f"{base_name}.zip"  # Build canonical final ZIP path (same as original after cleanup).

    if not merged_zip_path.exists():  # Verify whether merged ZIP was produced by Java pipeline.
        print(f"{BackgroundColors.YELLOW}[WARNING] Merged ZIP not found after Java pipeline: {merged_zip_path}{Style.RESET_ALL}")  # Log missing merged ZIP warning.
        return ""  # Return empty string when merged ZIP is absent.

    try:  # Attempt deletion of fragmented artifacts before renaming.
        for part in dir_path.glob(f"{base_name}.z[0-9][0-9]"):  # Iterate over ALL fragmented ZIP parts (.z01, .z02, .z03, etc.).
            if part.exists():  # Verify fragment still exists on disk.
                os.remove(part)  # Delete fragmented ZIP part.
                verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Fragmented file deleted: {BackgroundColors.CYAN}{part.name}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log deletion of each fragment.

        if original_zip_path.exists():  # Verify whether original .zip companion still exists.
            os.remove(original_zip_path)  # Delete original .zip file.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Original ZIP deleted: {BackgroundColors.CYAN}{original_zip_path.name}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log deletion.

        os.rename(merged_zip_path, canonical_zip_path)  # Rename merged ZIP to canonical filename.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Final rename complete: {BackgroundColors.CYAN}{merged_zip_path.name} → {canonical_zip_path.name}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log rename.

        return canonical_zip_path.name  # Return final filename.
    except Exception as exc:  # Handle filesystem operation failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed during fragment cleanup or rename: {exc}{Style.RESET_ALL}")  # Log cleanup failure warning.
        return ""  # Return empty string when cleanup fails.


def handle_fragmented_file_processing(detected_download_dir: str, detected_filename: str, frag_base_name: str, url: str, first_fragmented_file_detected: bool) -> str:
    """
    Handles the detection and merging of fragmented ZIP files when applicable.

    :param detected_download_dir: Directory where the fragmented files were detected.
    :param detected_filename: Initially detected filename from the downloads directory, used for logging and potential association with the URL if merging fails or is not needed.
    :param frag_base_name: Base name of the fragmented files without the .z01/.zip extensions.
    :param url: URL associated with the current processing cycle, used for logging context.
    :param first_fragmented_file_detected: Boolean flag indicating if this is the first detection of a fragmented file.
    :return: The new detected filename after handling fragmentation in case of success. In case of failure during merging, return empty string to indicate that the URL should not be associated with any file due to potential corruption, or return the original detected filename if no fragmentation handling was needed.
    """

    zip_arrived = wait_for_zip_fragmented_chain_completion(detected_download_dir, frag_base_name)  # Poll until the companion .zip file exists alongside the .z01 fragment.

    if zip_arrived:  # Verify whether the companion ZIP arrived before proceeding with merge.
        jar_path = resolve_or_build_java_jar(first_fragmented_file_detected)  # Resolve or build the Java merge JAR from submodule.

        if jar_path is not None:  # Verify whether the JAR was resolved or built successfully.
            zip_dir = Path(detected_download_dir)  # Resolve downloads directory path.
            zip_parts = sorted(zip_dir.glob(f"{frag_base_name}.z[0-9][0-9]"))  # Collect all fragmented parts (.z01, .z02, etc.)
            zip_parts.append(zip_dir / f"{frag_base_name}.zip")  # Add final ZIP file to complete the chain.
            merged_zip_path = zip_dir / f"{frag_base_name}_merged.zip"  # Build absolute output path for merged ZIP file.
            merge_ok = run_zip_merge_java(jar_path, zip_parts, merged_zip_path)  # Execute Java merge pipeline with ZIP chain reference.

            if merge_ok:  # Verify whether Java merge pipeline completed successfully.
                canonical_filename = finalize_fragments_cleanup(detected_download_dir, frag_base_name)  # Delete fragments, rename merged ZIP to canonical basename.

                if canonical_filename != "":  # Verify whether cleanup and rename completed successfully.
                    detected_filename = canonical_filename  # Replace detected filename with canonical single ZIP artifact.
                else:  # Cleanup failed — do not associate any file to avoid corrupted downstream mapping.
                    print(f"{BackgroundColors.YELLOW}[WARNING] Fragment cleanup failed for URL: {url} — skipping URL association.{Style.RESET_ALL}")  # Log cleanup failure and skip association.
                    detected_filename = ""  # Clear detected filename to prevent invalid URL association.
            else:  # Java merge failed — do not delete anything, skip association safely.
                print(f"{BackgroundColors.YELLOW}[WARNING] Java merge failed for URL: {url} — skipping URL association to preserve artifacts.{Style.RESET_ALL}")  # Log merge failure and skip association.
                detected_filename = ""  # Clear detected filename to prevent invalid URL association.
        else:  # JAR unavailable — cannot merge, skip association safely.
            print(f"{BackgroundColors.YELLOW}[WARNING] Java JAR unavailable for fragmented ZIP merge of URL: {url} — skipping URL association.{Style.RESET_ALL}")  # Log JAR unavailable warning.
            detected_filename = ""  # Clear detected filename to prevent invalid URL association.
    else:  # ZIP did not arrive — should not happen given infinite wait, but guard anyway.
        print(f"{BackgroundColors.YELLOW}[WARNING] Companion ZIP did not appear for fragmented archive of URL: {url} — skipping URL association.{Style.RESET_ALL}")  # Log missing companion ZIP warning.
        pass  # No fragmentation handling was needed; keep original detected filename.

    return detected_filename  # Return the potentially updated detected filename after handling fragmentation.


def is_file_empty(filepath: str) -> bool:
    """
    Verifies whether a file is empty.

    :param filepath: Path string to the file that must be evaluated.
    :return: True when file is missing, unreadable, or empty, otherwise False.
    """

    path_obj = Path(filepath)  # Build Path instance from the provided filepath string.

    if not path_obj.exists():  # Verify whether the target file exists before size evaluation.
        print(f"{BackgroundColors.YELLOW}[WARNING] File not found: {BackgroundColors.CYAN}{path_obj}{Style.RESET_ALL}")  # Print missing-file warning for validation visibility.
        return True  # Return True when the file is missing to keep fallback flow safe.

    try:  # Attempt to evaluate file size metadata safely.
        return int(path_obj.stat().st_size) == 0  # Return True when file byte size is zero.
    except Exception as e:  # Handle file metadata access failures safely.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to read file size for {BackgroundColors.CYAN}{path_obj}{Style.RESET_ALL}: {e}")  # Print unreadable-file warning for validation visibility.
        return True  # Return True when file metadata cannot be read.


def extract_amazon_urls_from_file(filepath: str, pattern: str) -> list:
    """
    Extracts valid Amazon affiliate URLs from a text file.

    :param filepath: Path string to the file to scan for URLs.
    :param pattern: Regex pattern string or compiled object used for extraction.
    :return: List of unique valid Amazon affiliate URLs found in the file.
    """

    extracted_urls: list = []  # Initialize extracted URL list preserving source order.
    path_obj = Path(filepath)  # Build Path instance from provided filepath string.

    if not path_obj.exists():  # Verify whether target file exists before content read.
        return extracted_urls  # Return empty list when target file is missing.

    try:  # Attempt to read file content safely using tolerant decoding.
        raw_text = path_obj.read_text(encoding="utf-8", errors="ignore")  # Read full file text using utf-8 with ignored decode errors.
    except Exception as e:  # Handle file read failures without interrupting flow.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to read file for URL extraction: {BackgroundColors.CYAN}{path_obj}{Style.RESET_ALL} - {e}")  # Print unreadable-file warning for extraction visibility.
        return extracted_urls  # Return empty list when file content cannot be read.

    compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else pattern  # Resolve extraction pattern as compiled regex for iteration.

    try:  # Attempt regex iteration across file content for URL extraction.
        for match in compiled_pattern.finditer(raw_text):  # Iterate regex matches across file content.
            candidate_url = normalize_affiliate_url(match.group(0))  # Normalize matched URL text before strict validation.

            if not validate_amazon_affiliate_url(candidate_url):  # Verify whether matched URL satisfies strict Amazon affiliate constraints.
                continue  # Continue iteration when matched URL is invalid.

            if candidate_url in extracted_urls:  # Verify whether matched URL is already collected for de-duplication.
                continue  # Continue iteration when URL is already present.

            extracted_urls.append(candidate_url)  # Append valid unique Amazon affiliate URL to extraction list.
    except Exception as e:  # Handle regex processing failures safely.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed during URL extraction for file: {BackgroundColors.CYAN}{path_obj}{Style.RESET_ALL} - {e}")  # Print regex processing warning for extraction visibility.

    return extracted_urls  # Return extracted URL list after scan completion.


def scan_outputs_for_amazon_urls(base_path: str, pattern: str) -> dict:
    """
    Scans Outputs recursively and maps valid Amazon URLs to source files.

    :param base_path: Base directory path string used for recursive traversal.
    :param pattern: Regex pattern string or compiled object used for extraction.
    :return: Dictionary mapping URL strings to lists of file paths where they appear.
    """

    url_map: dict = {}  # Initialize URL-to-filepaths mapping dictionary.
    outputs_path = Path(base_path)  # Build Outputs base Path instance from provided string.

    if not outputs_path.exists():  # Verify whether Outputs directory exists before recursive traversal.
        print(f"{BackgroundColors.YELLOW}[WARNING] Outputs directory not found for fallback scan: {BackgroundColors.CYAN}{outputs_path}{Style.RESET_ALL}")  # Print missing Outputs warning for fallback visibility.
        return url_map  # Return empty mapping when Outputs directory is unavailable.

    if not outputs_path.is_dir():  # Verify whether provided Outputs path points to a directory.
        print(f"{BackgroundColors.YELLOW}[WARNING] Outputs fallback path is not a directory: {BackgroundColors.CYAN}{outputs_path}{Style.RESET_ALL}")  # Print invalid Outputs path warning for fallback visibility.
        return url_map  # Return empty mapping when Outputs path is invalid.

    history_json_path = (outputs_path / "history.json").resolve()  # Resolve excluded Outputs history.json absolute path.

    for filepath in outputs_path.rglob("*"):  # Traverse Outputs filesystem entries recursively.
        if not filepath.is_file():  # Verify whether current traversal entry is a regular file.
            continue  # Continue traversal when entry is not a regular file.

        resolved_file = filepath.resolve()  # Resolve current file path for canonical comparison and storage.

        if resolved_file == history_json_path:  # Verify whether current file is excluded Outputs history.json.
            continue  # Continue traversal while skipping excluded history file.

        extracted_urls = extract_amazon_urls_from_file(str(resolved_file), pattern)  # Extract valid Amazon URLs from current Outputs file.

        if len(extracted_urls) == 0:  # Verify whether current Outputs file produced any valid URL entries.
            continue  # Continue traversal when no valid URL entries were extracted.

        normalized_filepath = str(resolved_file)  # Normalize resolved file path to string for map storage.

        for extracted_url in extracted_urls:  # Iterate extracted URLs to build grouped URL mapping.
            if extracted_url not in url_map:  # Verify whether URL key already exists in mapping dictionary.
                url_map[extracted_url] = []  # Initialize filepath list for first URL occurrence.

            if normalized_filepath in url_map[extracted_url]:  # Verify whether filepath is already listed for current URL key.
                continue  # Continue iteration when filepath is already mapped.

            url_map[extracted_url].append(normalized_filepath)  # Append unique filepath to current URL mapping list.

    return url_map  # Return completed URL-to-filepaths mapping dictionary.


def setup_image_paths(assets_dir: Path) -> Tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    """
    Creates and returns all required image asset paths.

    :param assets_dir: Directory containing image assets.
    :return: Tuple containing all resolved image paths in predefined order.
    """

    extension_img = assets_dir / "Extension.png"  # Define extension image path
    download_img = assets_dir / "DownloadButton.png"  # Define download button image path
    enable_permission_img = assets_dir / "Extension Enable Permission.png"  # Define extension permission image path
    confirmation_img = assets_dir / "ConfirmationFileDownloaded.png"  # Define download confirmation image path
    failed_file_download_img = assets_dir / "FileDownloadFailed.png"  # Define failed download image path
    close_download_tab_img = assets_dir / "CloseDownloadTab.png"  # Define close tab image path
    mercado_livre_img = assets_dir / "MercadoLivre-GoToProduct.png"  # Define MercadoLivre navigation image path
    share_button_img = assets_dir / "ShareAffiliateURL-Amazon.png"  # Define Amazon share button image path
    save_button_img = assets_dir / "SaveFileButton.png"  # Define MercadoLivre save button image path

    return (
        extension_img,  # Return extension image path
        download_img,  # Return download button image path
        enable_permission_img,  # Return permission image path
        confirmation_img,  # Return confirmation image path
        failed_file_download_img,  # Return failed download image path
        close_download_tab_img,  # Return close tab image path
        mercado_livre_img,  # Return MercadoLivre image path
        share_button_img,  # Return share button image path
        save_button_img,  # Return save button image path
    )  # Return complete tuple of image paths


def snapshot_download_directory(downloads_dir: Path) -> Dict[str, float]:
    """
    Captures file snapshot metadata from the downloads directory.

    :param downloads_dir: Path to the monitored downloads directory.
    :return: Dictionary mapping filename to modified timestamp.
    """

    snapshot: Dict[str, float] = {}  # Initialize snapshot dictionary.

    if not downloads_dir.exists():  # Verify if monitored downloads directory exists.
        print(f"{BackgroundColors.YELLOW}[WARNING] Downloads directory not found: {downloads_dir}{Style.RESET_ALL}")  # Log missing downloads directory warning.
        return snapshot  # Return empty snapshot when directory does not exist.

    try:  # Attempt to iterate over monitored downloads directory.
        for file_path in downloads_dir.iterdir():  # Iterate over entries from monitored downloads directory.
            if not file_path.is_file():  # Verify if current entry is a file.
                continue  # Skip non-file entries.

            try:  # Attempt to retrieve file modified timestamp.
                snapshot[file_path.name] = file_path.stat().st_mtime  # Store filename and modified timestamp in snapshot dictionary.
            except Exception:  # Handle timestamp retrieval failures.
                continue  # Skip file entries with inaccessible metadata.
    except Exception:  # Handle downloads directory listing failures.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to read downloads directory snapshot: {downloads_dir}{Style.RESET_ALL}")  # Log downloads snapshot failure warning.

    return snapshot  # Return captured downloads directory snapshot.


def snapshot_download_directories(downloads_dirs: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Captures snapshots for all monitored downloads directories.

    :param downloads_dirs: List of monitored downloads directory paths.
    :return: Dictionary mapping directory path to its file snapshot.
    """

    snapshots: Dict[str, Dict[str, float]] = {}  # Initialize directory-to-snapshot mapping dictionary.

    for downloads_dir in downloads_dirs:  # Iterate monitored downloads directory paths.
        resolved_dir = str(Path(downloads_dir).resolve())  # Resolve and normalize downloads directory path.
        snapshots[resolved_dir] = snapshot_download_directory(Path(resolved_dir))  # Capture and store snapshot for current downloads directory.

    return snapshots  # Return collected snapshots for all monitored directories.


def resolve_first_download_directory(downloads_dirs: List[str], before_snapshots: Dict[str, Dict[str, float]], after_snapshots: Dict[str, Dict[str, float]]) -> str | None:
    """
    Resolves which monitored directory received the first new download.

    :param downloads_dirs: List of monitored downloads directory paths.
    :param before_snapshots: Directory snapshots captured before processing the URL.
    :param after_snapshots: Directory snapshots captured after processing the URL.
    :return: Resolved directory path when detected, otherwise None.
    """

    for downloads_dir in downloads_dirs:  # Iterate monitored downloads directory paths in priority order.
        resolved_dir = str(Path(downloads_dir).resolve())  # Resolve and normalize current monitored directory path.
        before_snapshot = before_snapshots.get(resolved_dir, {})  # Retrieve pre-processing snapshot for current directory.
        after_snapshot = after_snapshots.get(resolved_dir, {})  # Retrieve post-processing snapshot for current directory.
        new_filenames = [filename for filename in after_snapshot if filename not in before_snapshot]  # Build new filenames list for current monitored directory.

        if len(new_filenames) > 0:  # Verify whether current monitored directory received at least one new file.
            return resolved_dir  # Return first resolved directory that received a new file.

    return None  # Return None when no monitored directory received a new file.


def update_active_download_directory(directory: str) -> None:
    """
    Updates cached active downloads directories with a single resolved directory.

    :param directory: Resolved downloads directory path.
    :return: None.
    """

    global ACTIVE_DOWNLOADS_DIRS  # Declare global variable for active downloads directory cache.

    resolved_dir = str(Path(directory).resolve())  # Resolve and normalize detected downloads directory path.
    ACTIVE_DOWNLOADS_DIRS = [resolved_dir]  # Persist single resolved downloads directory in global cache.


def is_compressed_file(filename: str) -> bool:
    """
    Returns True when filename appears to be a compressed archive.

    :param filename: Filename to evaluate.
    :return: True when filename extension matches common archive types.
    """

    lower = filename.lower()  # Normalize filename for suffix comparison.
    compressed_suffixes = (".zip", ".rar", ".7z", ".tar.gz", ".tgz", ".tar", ".gz")  # Define common compressed archive suffixes.

    if any(lower.endswith(suf) for suf in compressed_suffixes):  # Verify whether filename ends with any of the common compressed archive suffixes.
        return True  # Return True when filename ends with any common compressed archive suffix.

    if re.search(r"\.z\d{2}$", lower):  # Match .z followed by exactly two digits at the end of the filename.
        return True  # Return True when filename matches the .zNN compressed archive pattern.

    return False  # Return False when filename does not match any known compressed archive patterns.


def find_filename_by_marketplace(filenames: List[str], keywords: List[str]) -> str | None:
    """
    Select a filename that contains any of the marketplace keywords.

    :param filenames: List of filenames to evaluate.
    :param keywords: List of marketplace keywords to search for.
    :return: Filename matching keywords or None when no match is found.
    """

    for name in filenames:  # Iterate candidate filenames for keyword matching.
        lower_name = name.lower()  # Normalize candidate filename to lowercase for comparison.
        for kw in keywords:  # Iterate keywords to test presence in filename.
            if kw in lower_name:  # Verify whether the keyword appears as substring in filename.
                return name  # Return the first matching filename immediately when found.

    return None  # Return None when no marketplace keyword match is found.


def select_preferred_filename(filenames: List[str], filename_mtimes: Dict[str, float], keywords: List[str]) -> str | None:
    """
    Select a preferred filename among candidates, preferring unnumbered variants.

    :param filenames: List of filenames to evaluate.
    :param filename_mtimes: Mapping of filename to its modified timestamp.
    :param keywords: List of marketplace keywords to prioritize.
    :return: Preferred filename or None when no candidates are available.
    """

    if len(filenames) == 0:  # Verify whether candidate filenames list is empty.
        return None  # Return None when there are no candidate filenames.

    normalized_keywords = [kw.lower() for kw in keywords]  # Normalize keywords for case-insensitive matching.

    matched = [name for name in filenames if any(kw in name.lower() for kw in normalized_keywords)]  # Filter filenames that contain any marketplace keyword.

    if len(matched) == 0:  # Verify whether no filenames matched marketplace keywords.
        matched = filenames  # Fallback to all filenames when no marketplace-specific match was found.

    pattern = re.compile(r" \(\d+\)(?=\.[^./\\]+$)")  # Compile pattern that matches trailing numbered copies like " (1)" before extension.

    unnumbered = [name for name in matched if not pattern.search(name)]  # Filter matched names that do not contain numbered-copy suffixes.

    if len(unnumbered) > 0:  # Verify whether there are unnumbered candidate filenames.
        chosen = max(unnumbered, key=lambda fn: filename_mtimes.get(fn, 0.0))  # Select most recently modified unnumbered filename.
        return chosen  # Return the chosen unnumbered filename.

    chosen = max(matched, key=lambda fn: filename_mtimes.get(fn, 0.0))  # Select most recently modified filename when all are numbered.
    return chosen  # Return chosen filename as fallback when only numbered variants exist.


def detect_new_download_from_directories(before_snapshots: Dict[str, Dict[str, float]], after_snapshots: Dict[str, Dict[str, float]], downloads_dirs: List[str], url: str) -> Tuple[str, str]:
    """
    Detects a new downloaded file across one or multiple monitored directories.

    :param before_snapshots: Directory snapshots captured before URL processing.
    :param after_snapshots: Directory snapshots captured after URL processing.
    :param downloads_dirs: List of monitored downloads directory paths.
    :param url: URL associated with current processing cycle.
    :return: Tuple containing detected directory and detected filename.
    """

    detected_entries: List[Tuple[str, str, float]] = []  # Initialize detected entries list as tuples of directory, filename, and modified timestamp.
    single_compressed_entries: List[Tuple[str, str, float]] = []  # Initialize list for directories with exactly one compressed addition.

    for downloads_dir in downloads_dirs:  # Iterate monitored downloads directory paths.
        resolved_dir = str(Path(downloads_dir).resolve())  # Resolve and normalize current monitored directory path.
        before_snapshot = before_snapshots.get(resolved_dir, {})  # Retrieve pre-processing snapshot for current directory.
        after_snapshot = after_snapshots.get(resolved_dir, {})  # Retrieve post-processing snapshot for current directory.
        new_filenames = [filename for filename in after_snapshot if filename not in before_snapshot]  # Build list of new filenames for current monitored directory.

        if len(new_filenames) == 0:  # Verify whether current monitored directory has new files.
            continue  # Continue iteration when current directory has no new files.

        compressed_new = [fn for fn in new_filenames if is_compressed_file(fn)]  # Filter new filenames to compressed archive candidates.

        if len(compressed_new) == 1:  # Verify whether current monitored directory received exactly one compressed archive.
            comp_name = max(compressed_new, key=lambda fn: after_snapshot.get(fn, 0.0))  # Select the compressed filename by timestamp when single.
            comp_mtime = after_snapshot.get(comp_name, 0.0)  # Retrieve compressed filename modified timestamp.
            single_compressed_entries.append((resolved_dir, comp_name, comp_mtime))  # Append single compressed detection entry.
            continue  # Continue iteration after recording single compressed detection.

        selected_filename = max(new_filenames, key=lambda filename: after_snapshot.get(filename, 0.0))  # Select most recently modified new filename for current monitored directory.
        detected_entries.append((resolved_dir, selected_filename, after_snapshot.get(selected_filename, 0.0)))  # Append detected directory, filename, and modified timestamp entry.

    if len(single_compressed_entries) > 0:  # Verify whether any directory reported exactly one compressed addition.
        if len(single_compressed_entries) > 1:  # Verify multiple candidate directories with single compressed additions.
            print(f"{BackgroundColors.YELLOW}[WARNING] Multiple compressed downloads detected. Using most recent compressed file.{Style.RESET_ALL}")  # Log multiple compressed detection warning.

        sel_dir, sel_file, _ = max(single_compressed_entries, key=lambda item: item[2])  # Select most recent compressed file across single-compressed directories.
        return sel_dir, sel_file  # Return resolved directory and filename for the single compressed addition.

    compressed_entries: List[Tuple[str, str, float]] = [entry for entry in detected_entries if is_compressed_file(entry[1])]  # Build list of detected entries that are compressed archives.

    if len(compressed_entries) > 1:  # Verify whether multiple compressed files were detected across directories.
        keywords = ["aliexpress", "amazon", "mercadolivre", "shein", "shopee"]  # Marketplace keywords to prioritize when multiple compressed files exist.
        filenames = [entry[1] for entry in compressed_entries]  # Extract filenames from compressed entries for keyword scanning.
        filename_mtimes = {entry[1]: entry[2] for entry in compressed_entries}  # Build mapping of filename to modified timestamp from detected compressed entries.
        matched = select_preferred_filename(filenames, filename_mtimes, keywords)  # Attempt to select preferred filename using duplicate-aware selection.

        if matched is not None:  # Verify whether a preferred filename was selected among compressed entries.
            for d, f, _ in compressed_entries:  # Iterate compressed entries to locate the directory for the selected filename.
                if f == matched:  # Verify whether current entry filename matches the selected filename.
                    return d, f  # Return resolved directory and filename for the selected marketplace file.

    if len(detected_entries) == 0:  # Verify whether any monitored directory received new files when no single compressed detection occurred.
        print(f"{BackgroundColors.YELLOW}[WARNING] No new download detected for URL: {url}{Style.RESET_ALL}")  # Log missing download warning for current URL.
        return "", ""  # Return empty detection tuple when no new download is found.

    if len(detected_entries) > 1:  # Verify whether multiple directories or files were detected in the same cycle.
        print(f"{BackgroundColors.YELLOW}[WARNING] Multiple downloads detected across monitored directories. Using most recent file.{Style.RESET_ALL}")  # Log multiple downloads warning across directories.

    selected_dir, selected_filename, _ = max(detected_entries, key=lambda item: item[2])  # Select most recently modified file across all monitored directories.
    return selected_dir, selected_filename  # Return detected directory and filename.


def filter_and_delete_detected_filenames(detected_filename: str, delete_temp_files: bool = True) -> str:
    """
    Filters detected filenames to remove temporary or invalid entries.

    :param detected_filename: Detected filename to be filtered.
    :param delete_temp_files: Flag indicating whether to attempt deletion of detected temporary files.
    :return: Filtered filename or empty string if invalid.
    """
    
    if detected_filename.endswith(".tmp"):  # If the detected file is a temporary file.
        print(f"{BackgroundColors.YELLOW}[WARNING] Detected filename appears to be a temporary file and will be ignored: {BackgroundColors.CYAN}{detected_filename}{Style.RESET_ALL}")  # Log warning about temporary file detection.
        try:
            if delete_temp_files:  # Check if deletion of temporary files is enabled before attempting to delete.
                os.remove(detected_filename)  # Attempt to delete the temporary file to prevent future false detections.
                verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Temporary file deleted: {BackgroundColors.CYAN}{detected_filename}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log successful deletion of temporary file.
        except Exception as e:  # Handle potential failures during file deletion.
            print(f"{BackgroundColors.YELLOW}[WARNING] Failed to delete temporary file: {BackgroundColors.CYAN}{detected_filename}{Style.RESET_ALL} - {e}")  # Log failure to delete temporary file for visibility.
        return ""  # Return empty string for temporary files.

    return detected_filename  # Return original filename if valid.


def detect_new_download_file(before_snapshot: Dict[str, float], after_snapshot: Dict[str, float], url: str) -> str:
    """
    Detects new downloaded filename by comparing two snapshots.

    :param before_snapshot: Snapshot captured before URL processing.
    :param after_snapshot: Snapshot captured after URL processing.
    :param url: URL associated with current processing cycle.
    :return: Detected downloaded filename or empty string.
    """

    new_filenames = [filename for filename in after_snapshot if filename not in before_snapshot]  # Build list of files present only in post-download snapshot.

    if len(new_filenames) == 0:  # Verify if no new files were detected.
        print(f"{BackgroundColors.YELLOW}[WARNING] No new download detected for URL: {url}{Style.RESET_ALL}")  # Log missing download warning for current URL.
        return ""  # Return empty filename when no new file is detected.

    if len(new_filenames) > 1:  # Verify if multiple new files were detected.
        print(f"{BackgroundColors.YELLOW}[WARNING] Multiple downloads detected across monitored directories. Using most recent file.{Style.RESET_ALL}")  # Log multiple downloads warning across directories.

    selected_filename = max(new_filenames, key=lambda filename: after_snapshot.get(filename, 0.0))  # Select most recently modified filename from detected files.
    return selected_filename  # Return selected downloaded filename.


def handle_fragmented_download(detected_download_dir: str, detected_filenames: str, url: str, first_fragmented_file_detected: bool) -> Tuple[str, bool, bool]:
    """
    Handles fragmented ZIP detection and processing.

    :param detected_download_dir: Detected download directory.
    :param detected_filenames: Detected filename.
    :param url: URL associated with the download.
    :param first_fragmented_file_detected: Flag indicating first fragmented detection.
    :return: Tuple containing effective filename, updated fragmented flag, and continue flag.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Handling fragmented download for URL: {url} with detected file: {BackgroundColors.CYAN}{detected_filenames}{BackgroundColors.GREEN} in directory: {BackgroundColors.CYAN}{detected_download_dir}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log entry into fragmented download handling with details.

    effective_filename = detected_filenames  # Initialize effective filename with detected filename.
    should_continue = False  # Initialize continue flag.

    if detected_filenames != "" and detected_download_dir != "":  # Verify whether a download was detected before fragmentation evaluation.
        is_fragmented, frag_base_name = detect_split_zip_fragment_start(detected_filenames)  # Evaluate whether detected file is a fragmented ZIP first-part.

        if is_fragmented:  # Verify whether fragmented ZIP handling is required for this download.
            is_first_fragment = not first_fragmented_file_detected  # Determine whether this is the first fragmented file detection.
            first_fragmented_file_detected = True  # Mark that at least one fragmented file has been detected.
            final_filename = handle_fragmented_file_processing(detected_download_dir, detected_filenames, frag_base_name, url, is_first_fragment)  # Execute fragmented ZIP handling pipeline for the detected file.

            if final_filename == "":  # Verify whether fragmented ZIP processing succeeded by verifying for a non-empty final filename.
                print(f"{BackgroundColors.YELLOW}[WARNING] Fragmented ZIP processing failed for URL: {url}. Detected file: {detected_filenames}{Style.RESET_ALL}")  # Log fragmented ZIP processing failure with URL and detected filename details.
                should_continue = True  # Mark loop to continue without processing mapping.
            else:  # Verify whether fragmented processing returned a valid filename.
                effective_filename = final_filename  # Update effective filename to processed fragmented result.

    return effective_filename, first_fragmented_file_detected, should_continue  # Return processed filename, updated flag, and continue signal.


def associate_url_with_download(url_to_download: Dict[str, str], url: str, downloaded_filename: str) -> None:
    """
    Associates the processed URL with detected downloaded filename.

    :param url_to_download: Dictionary mapping URL to downloaded filename.
    :param url: Processed URL string.
    :param downloaded_filename: Detected downloaded filename.
    :return: None.
    """

    if downloaded_filename == "":  # Verify if downloaded filename is empty.
        return  # Return without mapping when no file was detected.

    url_to_download[url] = downloaded_filename  # Persist URL to downloaded filename association.


def normalize_and_deduplicate_url_entries(lines: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """
    Normalizes and deduplicates URL entries, preserving order and prioritizing valid filename mappings.

    :param lines: Raw lines from URLs file.
    :return: Tuple containing (url_to_filename_map, ordered_urls).
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Normalizing and deduplicating {BackgroundColors.CYAN}{len(lines)}{BackgroundColors.GREEN} raw URL entries from file.{Style.RESET_ALL}")  # Log entry into normalization with raw entry count.

    url_to_filename_map: Dict[str, str] = {}  # Initialize mapping of URL -> filename (empty string when not assigned).
    ordered_urls: List[str] = []  # Initialize ordered list to preserve first-seen URL ordering.

    for raw_line in lines:  # Iterate each raw line from file.
        tokens = raw_line.strip().split()  # Normalize and split line into tokens.

        if not tokens:  # Verify whether line is empty after stripping.
            continue  # Skip empty lines.

        parsed_url = tokens[0]  # Extract URL token (first token).
        parsed_filename = tokens[1] if len(tokens) > 1 else ""  # Extract filename token when present.

        if parsed_url not in url_to_filename_map:  # Verify whether URL is being seen for the first time.
            url_to_filename_map[parsed_url] = parsed_filename  # Persist initial mapping.
            ordered_urls.append(parsed_url)  # Preserve insertion order.
        else:  # Handle duplicate URL entries.
            if url_to_filename_map[parsed_url] == "" and parsed_filename != "":  # Prefer non-empty filename over empty mapping.
                url_to_filename_map[parsed_url] = parsed_filename  # Upgrade mapping with valid filename.

    return url_to_filename_map, ordered_urls  # Return normalized structures.


def apply_url_filename_update(url_to_filename_map: Dict[str, str], ordered_urls: List[str], target_url: str, detected_filename: str) -> None:
    """
    Applies a filename update to the normalized mapping.

    :param url_to_filename_map: Mapping of URL -> filename.
    :param ordered_urls: Ordered list of URLs.
    :param target_url: URL to update.
    :param detected_filename: Filename to associate.
    :return: None
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Applying filename update for URL: {BackgroundColors.CYAN}{target_url}{BackgroundColors.GREEN} with detected filename: {BackgroundColors.CYAN}{detected_filename}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log entry into URL-filename update with details.

    if target_url == "":  # Verify whether target URL is valid.
        return  # Skip invalid updates.

    if detected_filename != "":  # Verify whether detected filename is valid.
        url_to_filename_map[target_url] = detected_filename  # Force overwrite with latest detected filename.
    else:  # Handle case where filename is empty.
        if target_url not in url_to_filename_map:  # Verify whether URL is not already present.
            url_to_filename_map[target_url] = ""  # Insert URL with empty mapping.
            ordered_urls.append(target_url)  # Preserve ordering for new URL.


def rebuild_url_file_lines(url_to_filename_map: Dict[str, str], ordered_urls: List[str]) -> List[str]:
    """
    Reconstructs normalized file lines from mapping.

    :param url_to_filename_map: Mapping of URL -> filename.
    :param ordered_urls: Ordered list of URLs.
    :return: List of normalized lines.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Rebuilding normalized lines for {BackgroundColors.CYAN}{len(ordered_urls)}{BackgroundColors.GREEN} URLs based on updated mapping.{Style.RESET_ALL}")  # Log entry into line rebuilding with URL count.

    normalized_lines: List[str] = []  # Initialize output lines container.

    for ordered_url in ordered_urls:  # Iterate URLs preserving original order.
        mapped_filename = url_to_filename_map.get(ordered_url, "")  # Retrieve mapped filename.

        if mapped_filename != "":  # Verify whether filename exists.
            normalized_lines.append(f"{ordered_url} {mapped_filename}")  # Append URL with filename.
        else:
            normalized_lines.append(ordered_url)  # Append URL only.

    return normalized_lines  # Return reconstructed lines.


def update_url_filename_in_file(urls_file: Path, url: str, filename: str) -> bool:
    """
    Update the detected filename for a URL entry in a single file,
    while normalizing and deduplicating all entries.

    :param urls_file: Path to the URLs file to update.
    :param url: URL string to locate.
    :param filename: Detected downloaded filename.
    :return: True when successful, otherwise False.
    """

    if not urls_file.exists():  # Verify whether the target file exists.
        return False  # Return failure when file is absent.

    try:  # Attempt full normalization + update flow.
        raw_text = urls_file.read_text(encoding="utf-8", errors="ignore")  # Read file content.
        lines = raw_text.splitlines()  # Split into lines.

        url_to_filename_map, ordered_urls = normalize_and_deduplicate_url_entries(lines)  # Normalize + deduplicate dataset.

        apply_url_filename_update(url_to_filename_map, ordered_urls, url, filename)  # Apply update logic.

        normalized_lines = rebuild_url_file_lines(url_to_filename_map, ordered_urls)  # Rebuild normalized output.

        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Normalized URLs file with {BackgroundColors.CYAN}{len(normalized_lines)}{BackgroundColors.GREEN} unique entries.{Style.RESET_ALL}")  # Log normalization result.

        write_atomic_temp_file(urls_file, normalized_lines)  # Persist atomically.

        return True  # Return success.

    except Exception as e:  # Handle IO errors.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to normalize/update {BackgroundColors.CYAN}{urls_file}{Style.RESET_ALL}: {e}")  # Log failure.
        return False  # Return failure.


def update_url_filename_in_files(urls_file: Path, url: str, filename: str) -> None:
    """
    Update the detected filename for a URL entry in both the main and backup files.

    :param urls_file: Path to the main URLs input file.
    :param url: URL string to locate in both files.
    :param filename: Detected downloaded filename to associate with the URL.
    :return: None.
    """

    if filename == "":  # Verify whether the detected filename is empty before attempting any file updates.
        return  # Return early when no valid filename is available to associate.

    update_url_filename_in_file(urls_file, url, filename)  # Update detected filename in the main URLs input file.

    backup_file = resolve_backup_file_path(urls_file)  # Resolve the backup file path from the main URLs file path.

    if backup_file.exists():  # Verify whether the backup file exists before attempting update.
        update_url_filename_in_file(backup_file, url, filename)  # Update detected filename in the backup URLs input file.


def move_downloaded_file_for_url(downloads_dirs: List[str], destination_dir: Path, url: str, effective_filename: str, url_to_download: Dict[str, str]) -> str:
    """
    Moves a downloaded file associated with a URL into the URLs directory and returns final path.

    :param downloads_dirs: Paths to monitored downloads directories.
    :param destination_dir: Destination directory (urls_file.resolve().parent).
    :param url: URL associated with the downloaded file.
    :param effective_filename: Detected filename of the downloaded file.
    :param url_to_download: Mapping of URL to filename.
    :return: Final moved file path as string.
    """

    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Attempting to move downloaded file for URL: {BackgroundColors.CYAN}{url}{BackgroundColors.GREEN} with effective filename: {BackgroundColors.CYAN}{effective_filename}{BackgroundColors.GREEN} from {BackgroundColors.CYAN}{downloads_dirs}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{destination_dir}{Style.RESET_ALL}{Style.RESET_ALL}")  # Log entry into file move operation with details.

    if effective_filename == "":  # Verify if effective filename is empty before attempting move.
        return ""  # Return empty string when no file to move.

    normalized_downloads_dirs = [str(Path(downloads_dir).resolve()) for downloads_dir in downloads_dirs]  # Resolve and normalize monitored downloads directory paths.

    source_path = None  # Initialize source file path variable.

    for downloads_dir in normalized_downloads_dirs:  # Iterate over monitored downloads directories.
        candidate = Path(downloads_dir) / effective_filename  # Build candidate file path in current downloads directory.

        if candidate.exists():  # Verify if candidate file exists in current directory.
            source_path = candidate  # Assign candidate as source path if found.
            break  # Break loop after finding the file.

    if source_path is None:  # Verify if source file was not found in any monitored directory.
        return ""  # Return empty string when file is missing.

    destination_path = destination_dir / effective_filename  # Build initial destination file path in URLs directory.

    if destination_path.exists():  # Verify if destination file already exists to resolve collision.
        base = destination_path.stem  # Extract base name from destination file.
        suffix = destination_path.suffix  # Extract suffix from destination file.
        counter = 1  # Initialize collision counter.

        while True:  # Loop to resolve filename collision deterministically.
            new_name = f"{base} ({counter}){suffix}"  # Build new filename with deterministic suffix.
            candidate_path = destination_dir / new_name  # Build candidate destination path.

            if not candidate_path.exists():  # Verify if candidate path does not exist.
                destination_path = candidate_path  # Assign candidate as destination path.
                break  # Break loop after resolving collision.

            counter += 1  # Increment collision counter.

    try:  # Attempt to move file to destination path.
        source_path.rename(destination_path)  # Move source file to destination path.

    except Exception:  # Handle file move failures.
        return str(source_path)  # Return original source path as fallback if move fails.

    return destination_path.name  # Return final moved file name.


def update_urls_file(urls_file: Path, url_to_download: Dict[str, str]) -> None:
    """
    Rewrites URLs file using URL and downloaded filename associations.

    :param urls_file: Path to the URLs input file.
    :param url_to_download: Dictionary mapping URL to downloaded filename.
    :return: None.
    """

    if not urls_file.exists():  # Verify if URLs file exists before rewrite.
        print(f"{BackgroundColors.YELLOW}[WARNING] URLs file not found for update: {urls_file}{Style.RESET_ALL}")  # Log missing URLs file warning.
        return  # Return when URLs file does not exist.

    original_lines = urls_file.read_text(encoding="utf-8", errors="ignore").splitlines()  # Read current URLs file content as lines.
    updated_lines: List[str] = []  # Initialize updated URLs lines collection.

    for raw_line in original_lines:  # Iterate over original URLs file lines.
        line = raw_line.strip()  # Normalize line by removing outer whitespace.

        if line == "":  # Verify if normalized line is empty.
            updated_lines.append(raw_line)  # Preserve blank line entry in rewritten output.
            continue  # Continue processing next line.

        url = line.split()[0].strip()  # Extract URL token from current line.

        if url in url_to_download:  # Verify if URL has detected downloaded filename.
            updated_lines.append(f"{url} {url_to_download[url]}")  # Append URL and downloaded filename mapping entry.
            continue  # Continue processing next line after mapped update.

        updated_lines.append(line)  # Preserve original URL line when no mapping is available.

    urls_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")  # Rewrite URLs file with updated mapping lines.


def resolve_backup_file_path(urls_file: Path) -> Path:
    """
    Resolve the backup file path corresponding to the given URLs file.

    :param urls_file: Path to the main URLs input file.
    :return: Path to the corresponding backup file with '-backup' suffix.
    """

    return urls_file.with_name(urls_file.stem + "-backup" + urls_file.suffix)  # Build backup path by inserting '-backup' before the file extension.


def apply_renewed_url_to_files(original_url: str, renewed_url: str, urls_file: Path) -> None:
    """
    Apply a renewed Amazon affiliate URL replacement to both the main and backup input files.

    :param original_url: Original URL to locate and replace in both files.
    :param renewed_url: Renewed affiliate URL to substitute in place of the original.
    :param urls_file: Path to the main URLs input file.
    :return: None.
    """

    update_urls_txt_with_new_amazon_url(original_url, renewed_url, urls_file)  # Replace original URL with renewed URL in the main URLs input file.

    backup_file = resolve_backup_file_path(urls_file)  # Resolve the backup file path from the main URLs file path.

    if backup_file.exists():  # Verify whether the backup file exists before attempting update.
        update_urls_txt_with_new_amazon_url(original_url, renewed_url, backup_file)  # Replace original URL with renewed URL in the backup URLs input file.


def process_urls_with_download_tracking(urls: List[str], urls_file: Path, tab_count: int, downloads_dirs: List[str], extension_img: Path, download_img: Path, enable_permission_img: Path, confirmation_img: Path, failed_file_download_img: Path, close_download_tab_img: Path, mercado_livre_img: Path, share_button_img: Path, save_button_img: Path, ext_methods: Dict[str, List[int]], download_methods: Dict[str, List[int]], completion_methods: Dict[str, List[int]], close_methods: Dict[str, List[int]], chrome_download_settings_ready: bool, renew_amazon_affiliate: bool = False, only_renew_amazon_urls: bool = False) -> Tuple[int, Dict[str, str], bool]:
    """
    Processes URLs while tracking downloaded files by directory snapshots.

    :param urls: URL list to process.
    :param urls_file: Path to the file containing the URLs.
    :param tab_count: Number of URLs to process.
    :param downloads_dirs: Paths to monitored downloads directories.
    :param extension_img: Path to extension action image.
    :param download_img: Path to download button image.
    :param enable_permission_img: Path to optional extension enable-permission image.
    :param confirmation_img: Path to download confirmation image.
    :param failed_file_download_img: Path to failed file download image indicating download failure.
    :param close_download_tab_img: Path to close extension tab image.
    :param mercado_livre_img: Path to MercadoLivre go-to-product image.
    :param share_button_img: Path to ShareAffiliateURL button image for Amazon URL renewal.
    :param save_button_img: Path to save button image for MercadoLivre.
    :param ext_methods: Grouped extension click methods dictionary.
    :param download_methods: Grouped download click methods dictionary.
    :param completion_methods: Grouped completion detection methods dictionary.
    :param close_methods: Grouped close extension tab methods dictionary.
    :param chrome_download_settings_ready: Whether Chrome downloads settings were verified successfully before URL processing.
    :param only_renew_amazon_urls: Whether to execute only Amazon URL renewal flow without downloads.
    :return: Processed count, URL mapping dictionary, and success status.
    """

    url_to_download: Dict[str, str] = {}  # Initialize URL to downloaded filename mapping dictionary.
    processed_count = 0  # Initialize processed URL counter.
    initial_consecutive_download_failures = 0  # Initialize consecutive download-failure counter for the first processed URLs when Chrome downloads settings are unresolved.
    downloads_dirs[:] = [str(Path(downloads_dir).resolve()) for downloads_dir in downloads_dirs]  # Resolve and normalize monitored downloads directory paths.
    opened_tabs = 0  # Track number of tabs opened by this processing loop to avoid closing the base tab.

    if tab_count > 0:  # Verify if there are URLs to process.
        if not activate_automation_window():  # Verify if automation window activation succeeds before opening separator tab.
            return processed_count, url_to_download, False  # Return failure state when activation fails.

    bar_format = (
        f"{BackgroundColors.GREEN}{{desc}}: {Style.RESET_ALL}"  # Format the description and a green colon for clarity
        f"{BackgroundColors.CYAN}{{bar}}{Style.RESET_ALL} "  # Render the progress bar itself in cyan for visibility
        f"{BackgroundColors.GREEN}{{n_fmt}}/{{total_fmt}} [{{elapsed}}<{{remaining}}, {{rate_fmt}}/it]{Style.RESET_ALL}"
    )  # Combine ANSI-colored segments into a single tqdm bar format string

    first_fragmented_file_detected = False  # Flag to track whether the first fragmented file detection has occurred for initial failure handling.

    for index, url in enumerate(tqdm(urls, total=len(urls), desc="Processing URLs", bar_format=bar_format), start=1):  # Initialize tqdm with custom colored bar_format and enumerate indexing
        retry_attempt = 1  # Initialize retry counter for current URL execution.
        success = False  # Initialize success flag for current URL processing.
        fragmented_skip = False  # Initialize fragmented skip flag for for-loop continuation after while-loop exit.

        if not activate_automation_window():  # Verify if automation window activation succeeds before URL navigation.
            return processed_count, url_to_download, False  # Return failure state when activation fails.

        opened_tabs = open_url_in_new_tab(url, opened_tabs)  # Open URL in new tab and update opened tabs counter.

        current_tab = index  # Store current tab index.
        original_url = url  # Preserve original URL before potential Amazon affiliate renewal modification.

        if re.search(AFFILIATE_URL_PATTERN, url):  # Verify whether current URL matches Amazon affiliate pattern.
            url, renewal_success, renewed_url = handle_amazon_affiliate_url(current_tab, url, share_button_img, Path(urls_file), renew_amazon_affiliate)  # Execute extracted Amazon affiliate handling logic.

            if renewal_success and renewed_url != original_url:  # Verify whether renewal succeeded and URL actually changed before applying file updates.
                apply_renewed_url_to_files(original_url, renewed_url, urls_file)  # Apply renewed URL to both main and backup input files.

        # @TODO: FIx this, as this depends on renewal_sucess. If the renewal fails, it must try again 
        if only_renew_amazon_urls:  # Verify whether only-renew mode is active for Amazon URLs.
            opened_tabs = handle_only_renew_amazon_urls(opened_tabs)  # Execute extracted only-renew tab handling logic.
            processed_count += 1  # Increment processed counter.
            break  # Continue loop without executing download-specific workflow.
        
        while retry_attempt <= MAX_DOWNLOAD_RETRY_ATTEMPTS:  # Execute download attempt up to maximum retry limit.
            pre_download_snapshots = snapshot_download_directories(downloads_dirs)  # Capture downloads directory snapshots before URL processing.
            
            click_go_to_product_button(mercado_livre_img)  # Execute MercadoLivre button action when available.
            
            extension_method = click_image_or_coords(extension_img, EXTENSION_X_REF, EXTENSION_Y_REF)  # Execute extension click action with scaled fallback coordinates.
                
            px, py = compute_extension_cursor_position()  # Compute cursor position based on current browser/window size.
            pyautogui.moveTo(px, py, duration=0.12)  # Move cursor to computed extension position to prepare for scrolling.
            time.sleep(0.05)  # Wait briefly after moving cursor to allow UI to stabilize before scrolling.
            scroll_extension_tab_to_start_button()  # Scroll at cursor position to reveal the Start download button on low-resolution screens.
            
            enable_permission_method = click_enable_permission(enable_permission_img)  # Attempt to click optional extension enable permission button using passed asset variable.
            
            scroll_extension_tab_to_start_button()  # Scroll again after potential permission click to ensure the Start download button is visible regardless of permission prompt presence or screen size.
            
            verbose_output(f"{BackgroundColors.GREEN}Enable permission action: {BackgroundColors.CYAN}{enable_permission_method}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Log enable-permission action when verbose.

            download_method = click_download_button(download_img)  # Execute download click action.
            confirmation_alt_img = confirmation_img.with_name(f"{confirmation_img.stem}-Alternative{confirmation_img.suffix}")  # Build alternative confirmation image path using deterministic naming pattern.
            confirmation_method = watch_for_save_dialog_and_confirmation(save_button_img, confirmation_img, confirmation_alt_img, failed_file_download_img)  # Watch and handle optional save dialog while waiting.

            download_failed = confirmation_method == "Timeout" or confirmation_method == "Download Failed"  # Set download failure flag based on confirmation timeout or failed download result.
            
            if not download_failed:  # Execute post-download detection when confirmation succeeded.
                # @TODO: Dispatch this to a new function and thread/core in order for the code to jump to the next url and handle the download detection and mapping asynchronously while the current thread continues processing the next URLs and handling their downloads in parallel, which would significantly improve the overall processing time when dealing with a large number of URLs and downloads.
                
                wait_for_download_file_stabilization(downloads_dirs)  # Wait for file to finish writing and remove temporary extensions.
                post_download_snapshots = snapshot_download_directories(downloads_dirs)  # Capture downloads directory snapshots after download completion.
                
                if len(downloads_dirs) > 1:  # Verify whether monitored downloads directories are unresolved.
                    resolved_download_dir = resolve_first_download_directory(downloads_dirs, pre_download_snapshots, post_download_snapshots)  # Resolve monitored downloads directory using first detected file.
                    
                    if resolved_download_dir is not None:  # Verify whether monitored downloads directory resolution succeeded.
                        update_active_download_directory(resolved_download_dir)  # Persist resolved monitored downloads directory in global cache.
                        downloads_dirs[:] = ACTIVE_DOWNLOADS_DIRS  # Update local monitored downloads directories list with resolved cache.
                        
                detected_download_dir, detected_filenames = detect_new_download_from_directories(pre_download_snapshots, post_download_snapshots, downloads_dirs, url)  # Detect downloaded filename and source directory associated with current URL.
                
                detected_filenames = filter_and_delete_detected_filenames(detected_filenames)  # Filter detected filenames to remove temporary or invalid entries.
                
                if detected_download_dir != "" and len(downloads_dirs) > 1:  # Verify whether detected directory exists while local list remains unresolved.
                    update_active_download_directory(detected_download_dir)  # Persist detected monitored downloads directory in global cache.
                    downloads_dirs[:] = ACTIVE_DOWNLOADS_DIRS  # Update local monitored downloads directories list with detected cache.
                
                initial_consecutive_download_failures, abort_result = handle_initial_chrome_download_failures(chrome_download_settings_ready, index, detected_filenames, initial_consecutive_download_failures, url, processed_count, url_to_download)  # Verify initial downloads and possibly request manual intervention.
                
                if abort_result is not None:  # Verify whether handler requested abort after manual intervention request.
                    return abort_result  # Return handler-provided abort tuple to stop processing remaining URLs.
                
                if detected_filenames == "":  # Verify whether file detection failed after confirmation succeeded.
                    download_failed = True  # Mark download as failed when no file was detected after confirmation.
                else:  # Execute success path when file was detected after confirmation.
                    effective_filename = detected_filenames  # Default: Non-fragmented file case.
                    
                    effective_filename, first_fragmented_file_detected, should_continue = handle_fragmented_download(detected_download_dir, detected_filenames, url, first_fragmented_file_detected)  # Execute fragmented ZIP handling logic.
                    
                    if should_continue:  # Verify whether fragmented processing requested loop continuation.
                        verbose_output(f"{BackgroundColors.YELLOW}[WARNING] Skipping URL mapping update due to fragmented ZIP processing failure for URL: {url}{Style.RESET_ALL}")  # Log mapping skip due to fragmented processing failure with URL details when verbose.
                        fragmented_skip = True  # Mark fragmented skip flag for outer for-loop continuation without processed_count increment.
                        break  # Exit while loop without closing tabs, preserving original fragmented skip behavior.
                    
                    associate_url_with_download(url_to_download, url, effective_filename)  # Persist URL to downloaded filename mapping when detection succeeds.
                    update_url_filename_in_files(urls_file, url, effective_filename)  # Update detected filename for the current URL in both main and backup input files.
                    effective_filename = move_downloaded_file_for_url(downloads_dirs, urls_file.resolve().parent, url, effective_filename, url_to_download)  # Move downloaded file for current URL and update mapping with new location.
                    success = True  # Mark download as successful for processed_count increment after while loop.
                    
            close_method = close_extension_download_tab(close_download_tab_img)  # Execute close extension tab action.
            if not download_failed:  # Execute post-download tab closure only when download was not marked as failed to allow for retry attempts without reopening the URL.
                handle_post_download_methods(ext_methods, download_methods, completion_methods, close_methods, extension_method, download_method, confirmation_method, close_method, current_tab)  # Execute extracted method tracking logic.
            opened_tabs = safely_close_product_tab(opened_tabs)  # Execute safe tab closure logic and update opened tabs counter.

            if download_failed:  # Execute retry or exhaustion handling when download failed.
                retry_attempt += 1  # Increment retry counter before evaluating retry eligibility.

                if retry_attempt <= MAX_DOWNLOAD_RETRY_ATTEMPTS:  # Verify whether retry is still within allowed attempts.
                    print(f"{BackgroundColors.YELLOW}[WARNING] Download failed for URL: {BackgroundColors.CYAN}{url}{BackgroundColors.YELLOW}. Retrying attempt {BackgroundColors.CYAN}{retry_attempt}{BackgroundColors.YELLOW}/{BackgroundColors.CYAN}{MAX_DOWNLOAD_RETRY_ATTEMPTS}{BackgroundColors.YELLOW}.{Style.RESET_ALL}")  # Log retry warning with current attempt count.
                    context_ready = reset_browser_context_for_retry(close_download_tab_img)  # Reset browser context by closing window and reopening automation environment.
                    opened_tabs = 0  # Reset opened tabs counter after browser window closure during retry.

                    if context_ready:  # Verify browser context readiness before reopening URL for retry.
                        opened_tabs = open_url_in_new_tab(url, opened_tabs)  # Reopen URL in new tab for retry attempt.
                    continue  # Continue while loop for retry attempt execution.
                print(f"{BackgroundColors.YELLOW}[WARNING] Download failed for URL: {BackgroundColors.CYAN}{url}{BackgroundColors.YELLOW} after {BackgroundColors.CYAN}{MAX_DOWNLOAD_RETRY_ATTEMPTS}{BackgroundColors.YELLOW} attempts. Moving to next URL.{Style.RESET_ALL}")  # Log final failure after exhausting all retry attempts.
                break  # Exit while loop after exhausting all retry attempts.
            break  # Exit while loop on successful download completion.

        if fragmented_skip:  # Verify whether fragmented skip was requested during download attempt.
            continue  # Continue for loop without processed_count increment for fragmented ZIP skip.

        if not success:  # Verify whether download ultimately failed after all retry attempts.
            continue  # Continue for loop without processed_count increment for failed URLs.

        processed_count += 1  # Increment processed counter for successfully completed URLs.

    url_to_download = dict(sorted(url_to_download.items(), key=lambda item: item[0].lower()))  # Sort URL mapping dictionary by keys alphabetically in a case-insensitive manner

    return processed_count, url_to_download, True  # Return processed counter, URL mapping, and success status.


def locate_image(image_path: Path) -> Any:
    """
    Locates an image on screen.

    :param image_path: Path to the image file.
    :return: Box location when found, otherwise None.
    """

    if not image_path.exists():  # Verify image file existence.
        return None  # Return None when image file does not exist.

    try:  # Attempt image location on screen using multi-monitor capture.
        template = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)  # Load template image in grayscale for matching.

        if template is None:  # Verify template loading success.
            return None  # Return None when template loading fails.

        vd_left, vd_top, vd_right, vd_bottom = get_virtual_desktop_bounds()  # Retrieve full virtual desktop bounds for coordinate conversion.
        screenshot = ImageGrab.grab(bbox=(vd_left, vd_top, vd_right, vd_bottom), all_screens=True)  # Capture full virtual desktop across all monitors.
        screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)  # Convert screenshot to grayscale for template matching.
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)  # Perform normalized cross-correlation template matching.
        _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Extract best match location and confidence score.

        if max_val < 0.9:  # Verify match confidence meets threshold.
            return None  # Return None when match confidence is insufficient.

        x_img, y_img = max_loc  # Unpack image-space match coordinates.
        h_t, w_t = template.shape[:2]  # Extract template height and width for bounding box.
        return Box(left=vd_left + x_img, top=vd_top + y_img, width=w_t, height=h_t)  # Return virtual desktop coordinates as Box for matched result.
    except Exception:  # Handle image search exception.
        return None  # Return None when image search fails.


def load_template(image_path: Path) -> Any:
    """
    Loads the template image in grayscale.

    :param image_path: Path to the image file.
    :return: Loaded grayscale template or None.
    """

    template = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)  # Load image in grayscale.

    if template is None:  # Verify template loading success.
        return None  # Return None when loading fails.

    return template  # Return loaded template.


def capture_screen_grayscale() -> Any:
    """
    Captures the current screen and converts it to grayscale.

    :return: Grayscale screenshot as numpy array.
    """

    try:  # Attempt all-monitor screenshot capture for full virtual desktop coverage.
        vd_left, vd_top, vd_right, vd_bottom = get_virtual_desktop_bounds()  # Retrieve full virtual desktop bounds for all-screen capture.
        screen = ImageGrab.grab(bbox=(vd_left, vd_top, vd_right, vd_bottom), all_screens=True)  # Capture full virtual desktop across all monitors.
    except Exception:  # Fall back to primary monitor capture on failure.
        screen = pyautogui.screenshot()  # Capture primary monitor screen as fallback.

    return cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)  # Convert to grayscale and return.


def get_scale_factors() -> list[float]:
    """
    Provides predefined scale factors for multi-resolution matching.

    :return: List of scale factors.
    """

    return [0.5, 0.75, 1.0, 1.25, 1.5]  # Return supported scaling values.


def match_template_multi_scale(screen: Any, template: Any, scales: list[float], verbose=False) -> Any:
    """
    Performs multi-scale template matching.

    :param screen: Grayscale screenshot.
    :param template: Grayscale template image.
    :param scales: Scale factors to test.
    :param verbose: Flag to enable verbose output.
    :return: Best match result or None.
    """

    best_match = None  # Initialize best match container.
    best_val = -1  # Initialize best score.

    for scale in scales:  # Iterate scale factors.
        resized = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)  # Resize template.

        if resized.shape[0] > screen.shape[0] or resized.shape[1] > screen.shape[1]:  # Verify size compatibility.
            continue  # Skip invalid scale.

        result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)  # Perform matching.
        _, max_val, _, max_loc = cv2.minMaxLoc(result)  # Extract best result.

        if max_val > best_val:  # Verify improvement.
            if verbose:
                verbose_output(f"{BackgroundColors.GREEN}[DEBUG] New best match found at scale {BackgroundColors.CYAN}{scale}{BackgroundColors.GREEN} with confidence {BackgroundColors.CYAN}{max_val:.4f}{Style.RESET_ALL}")  # Log new best match details when verbose.
            best_val = max_val  # Update score.
            best_match = (max_loc, resized.shape[::-1])  # Store match.

    return best_match, best_val  # Return match and confidence.


def validate_match(best_match: Any, best_val: float, threshold: float = 0.9) -> Any:
    """
    Validates match quality against threshold.

    :param best_match: Match result tuple.
    :param best_val: Confidence score.
    :param threshold: Minimum allowed confidence.
    :return: Validated match or None.
    """

    if best_match is None:  # Verify match existence.
        return None  # Return None when no match found.

    if best_val < threshold:  # Verify confidence threshold.
        return None  # Reject weak matches.

    return best_match  # Return valid match.


def enhanced_locate_image(image_path: Path, threshold: float = 0.90) -> Any:
    """
    Locates an image on screen using multi-scale template matching.

    :param image_path: Path to the image file.
    :param threshold: Minimum allowed confidence for match validation.
    :return: Box location when found, otherwise None.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Attempting to locate image with enhanced method: {BackgroundColors.CYAN}{image_path}{Style.RESET_ALL}")  # Log entry into enhanced image location with target path details when verbose.

    if not image_path.exists():  # Verify image file existence.
        return None  # Return None when image file does not exist.

    try:  # Attempt image location on screen.
        template = load_template(image_path)  # Load grayscale template.
        if template is None:  # Verify template load success.
            return None  # Return None when template loading fails.

        screen = capture_screen_grayscale()  # Capture grayscale screen.
        scales = get_scale_factors()  # Retrieve scale factors.

        best_match, best_val = match_template_multi_scale(screen, template, scales, verbose=False)  # Perform multi-scale matching.
        validated_match = validate_match(best_match, best_val, threshold=threshold)  # Validate match confidence.

        if validated_match is None:  # Verify match validity.
            return None  # Return None when invalid match.

        (x, y), (w, h) = validated_match  # Unpack match result.

        vd_left, vd_top, _, _ = get_virtual_desktop_bounds()  # Retrieve virtual desktop origin for coordinate conversion.
        return Box(left=vd_left + x, top=vd_top + y, width=w, height=h)  # Return virtual desktop coordinates as Box for matched result.
    except Exception:  # Handle image search exception.
        return None  # Return None when image search fails.


def get_screen_dimensions() -> Tuple[int, int]:
    """
    Retrieves target monitor dimensions based on the USE_MAIN_MONITOR setting.

    :param: None.
    :return: Tuple of target monitor width and height in pixels.
    """

    left, top, right, bottom = get_desired_monitor_bounds()  # Retrieve target monitor bounds from monitor selection logic.
    return max(1, right - left), max(1, bottom - top)  # Return target monitor width and height derived from bounds.


def scale_coordinate_to_screen(reference_x: float, reference_y: float) -> Tuple[int, int]:
    """
    Scales reference coordinates to current screen dimensions.

    :param reference_x: X coordinate from reference resolution (1920x1080).
    :param reference_y: Y coordinate from reference resolution (1920x1080).
    :return: Tuple of scaled X and Y coordinates for current screen.
    """

    current_width, current_height = get_screen_dimensions()  # Retrieve current screen dimensions.
    scale_x = current_width / REFERENCE_SCREEN_WIDTH  # Compute horizontal scaling factor.
    scale_y = current_height / REFERENCE_SCREEN_HEIGHT  # Compute vertical scaling factor.
    scaled_x = int(reference_x * scale_x)  # Apply horizontal scaling to reference X coordinate.
    scaled_y = int(reference_y * scale_y)  # Apply vertical scaling to reference Y coordinate.
    return scaled_x, scaled_y  # Return tuple of scaled coordinates.


def get_active_window_bounds() -> Dict[str, int]:
    """
    Retrieves active Chrome window bounds for relative positioning.

    :param: None.
    :return: Dictionary with left, top, width, height of active Chrome window or zeros if unavailable.
    """

    try:  # Attempt to retrieve active window bounds from global tracking variable.
        if ACTIVE_CHROME_BOUNDS["width"] > 0 and ACTIVE_CHROME_BOUNDS["height"] > 0:  # Verify active window bounds were previously cached.
            return ACTIVE_CHROME_BOUNDS.copy()  # Return cached active window bounds.
    except Exception:  # Handle global variable access failures.
        pass  # Continue to screen dimensions fallback.

    screen_width, screen_height = get_screen_dimensions()  # Retrieve current screen dimensions.
    return {"left": 0, "top": 0, "width": screen_width, "height": screen_height}  # Return full screen as fallback bounds.


def get_scaled_fallback_coords(reference_x: float, reference_y: float) -> Tuple[int, int]:
    """
    Computes scaled fallback coordinates relative to active Chrome window.

    :param reference_x: X coordinate from reference resolution (1920x1080).
    :param reference_y: Y coordinate from reference resolution (1920x1080).
    :return: Tuple of adjusted coordinates relative to Chrome window position.
    """

    scaled_x, scaled_y = scale_coordinate_to_screen(reference_x, reference_y)  # Scale coordinates to current screen dimensions.
    window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds.
    adjusted_x = window_bounds["left"] + scaled_x  # Adjust X coordinate relative to window left edge.
    adjusted_y = window_bounds["top"] + scaled_y  # Adjust Y coordinate relative to window top edge.
    return adjusted_x, adjusted_y  # Return tuple of window-adjusted coordinates.


def click_image_or_coords(image_path: Path, reference_x: float, reference_y: float) -> str:
    """
    Clicks image center or scaled fallback coordinates.

    :param image_path: Path to the primary image target.
    :param reference_x: Fallback X coordinate from reference resolution (1920x1080).
    :param reference_y: Fallback Y coordinate from reference resolution (1920x1080).
    :return: Method name used for the click.
    """

    box = locate_image(image_path)  # Locate image on screen.

    if box is not None:  # Verify image was found.
        pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
        return "ImageSearch"  # Return image search method label.

    scaled_x, scaled_y = get_scaled_fallback_coords(reference_x, reference_y)  # Compute scaled fallback coordinates relative to active window.
    pyautogui.click(scaled_x, scaled_y)  # Click scaled fallback coordinates.
    return "Coordinates"  # Return coordinates method label.


def compute_extension_cursor_position() -> Tuple[int, int]:
    """
    Compute cursor position for extension tab scrolling.

    :param: None.
    :return: Tuple of X and Y coordinates to position the cursor for extension tab scrolling.
    """

    window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds for absolute coordinate computation.
    window_left = window_bounds["left"]  # Extract active window left offset for absolute X positioning.
    window_top = window_bounds["top"]  # Extract active window top offset for absolute Y positioning.
    window_width = max(1, window_bounds["width"])  # Extract active window width for relative position computation.
    window_height = max(1, window_bounds["height"])  # Extract active window height for vertical center computation.

    ninth_segment_start = int(window_width * 0.8)  # Compute start of the ninth decile of the window width.

    ninth_segment_end = int(window_width * 0.9)  # Compute end of the ninth decile of the window width.

    target_x = window_left + int((ninth_segment_start + ninth_segment_end) / 2)  # Compute absolute center X inside the ninth decile offset by window position.

    target_y = window_top + int(window_height / 2)  # Compute absolute vertical center Y offset by window position.

    return target_x, target_y  # Return computed cursor coordinates for extension interactions.


def scroll_extension_tab_to_start_button(scroll_amount: int = -500) -> None:
    """
    Scrolls extension tab at computed cursor to reveal the Start download button.

    :param scroll_amount: Number of scroll units (negative to scroll down).
    :return: None.
    """

    pyautogui.scroll(scroll_amount)  # Scroll vertically from current cursor position to reveal hidden controls.

    time.sleep(0.2)  # Wait briefly after scrolling to allow elements to become visible.


def open_url_in_new_tab(url: str, opened_tabs: int) -> int:
    """
    Open URL in a new browser tab and navigate to it.

    :param url: URL to open in the browser.
    :param opened_tabs: Current count of opened tabs.
    :return: Updated opened tabs count.
    """

    pyautogui.hotkey("ctrl", "t")  # Open new browser tab.
    opened_tabs += 1  # Increment opened tabs counter after opening a new tab.

    time.sleep(0.2)  # Wait after opening tab.
    pyautogui.hotkey("ctrl", "l")  # Focus browser address bar.

    time.sleep(0.08)  # Wait after focusing address bar.
    pyautogui.hotkey("ctrl", "a")  # Select any previous address-bar text.

    time.sleep(0.05)  # Wait after selecting address text.
    pyautogui.press("backspace")  # Clear selected address text.

    time.sleep(0.05)  # Wait after clearing address text.
    pyautogui.typewrite(url, interval=0.0)  # Type URL into address bar.

    time.sleep(0.1)  # Wait after typing URL.
    pyautogui.press("enter")  # Navigate to URL.

    time.sleep(3)  # Wait for page loading.

    return opened_tabs  # Return updated opened tabs count.


def scroll_window_to_top_center() -> None:
    """
    Scrolls the active window to the top center.

    :return: None.
    """

    try:  # Guard against unexpected errors during UI automation
        window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds for absolute center computation.
        center_x = window_bounds["left"] + window_bounds["width"] // 2  # Compute absolute horizontal center of active window.
        center_y = window_bounds["top"] + window_bounds["height"] // 2  # Compute absolute vertical center of active window.
        pyautogui.moveTo(center_x, center_y, duration=0.12)  # Move cursor to center of active window to prepare for input.
        time.sleep(0.05)  # Wait briefly after moving cursor for UI stability.
        time.sleep(0.05)  # Wait briefly after click to allow window focus to settle.
        pyautogui.keyDown("home")  # Press and hold Home key to move content to top.
        time.sleep(3)  # Hold Home key for three seconds to ensure top alignment.
        pyautogui.keyUp("home")  # Release Home key after hold duration.
        time.sleep(0.2)  # Wait after input to allow UI elements to stabilize.
    except Exception:  # Handle unexpected exceptions to avoid breaking main flow
        pass  # Ignore exceptions to preserve execution flow when Home key press fails


def handle_amazon_affiliate_url(current_tab: int, url: str, share_button_img: Path, urls_file: Path, renew_amazon_affiliate: bool) -> Tuple[str, bool, str]:
    """
    Handle Amazon affiliate URL renewal flow.

    :param current_tab: Current browser tab index.
    :param url: Original URL being processed.
    :param share_button_img: Path to ShareAffiliateURL button image.
    :param urls_file: Path to urls.txt file.
    :param renew_amazon_affiliate: Flag indicating whether renewal is enabled.
    :return: Tuple containing possibly updated URL, success flag, and renewed URL.
    """

    scroll_window_to_top_center()  # Scroll active window to top center to reveal the share button image.

    renewal_success = False  # Initialize renewal success flag.
    old_url = url  # Preserve original URL for comparison after renewal attempt.
    renewed_url = url  # Initialize renewed URL with original URL.

    if renew_amazon_affiliate or RENEW_AMAZON_AFFILIATE_URL:  # Verify whether renewal is enabled via arg or global flag before attempting renewal.
        renewal_success, renewed_url = renew_amazon_affiliate_url(url, share_button_img, Path(urls_file))  # Attempt Amazon affiliate URL renewal and capture tuple result.
        if renewal_success and renewed_url != url:  # Verify whether renewal succeeded and URL changed before updating current URL.
            url = renewed_url  # Update current URL with renewed affiliate URL.

    if VERBOSE:  # Verify whether verbose logging is enabled for renewal status reporting.
        if renewal_success:  # Verify whether renewal succeeded before logging success message.
            print(f"{BackgroundColors.GREEN}Amazon URL renewed successfully for tab {BackgroundColors.CYAN}{current_tab}{BackgroundColors.GREEN} from {BackgroundColors.CYAN}{old_url}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{renewed_url}{Style.RESET_ALL}")  # Log successful renewal with details and green background.
        else:  # Otherwise renewal failed, log failure message.
            print(f"{BackgroundColors.RED}Amazon URL renewal failed for tab {BackgroundColors.CYAN}{current_tab}{BackgroundColors.RED} from {BackgroundColors.CYAN}{old_url}{BackgroundColors.RED} to {BackgroundColors.CYAN}{renewed_url}{Style.RESET_ALL}")  # Log failed renewal with details and red background.

    return url, renewal_success, renewed_url  # Return updated URL, success flag, and renewed URL.


def handle_only_renew_amazon_urls(opened_tabs: int) -> int:
    """
    Handle only-renew Amazon URLs mode tab closure logic.

    :param opened_tabs: Current number of opened tabs.
    :return: Updated opened_tabs count after closure attempt.
    """

    try:  # Attempt safe tab closure and focus restoration in only-renew mode.
        if opened_tabs > 0:  # Verify that a tab opened by this loop exists before closing.
            close_current_tab()  # Close the current product tab that was opened earlier.
            opened_tabs -= 1  # Decrement opened tabs counter after successful closure.
            time.sleep(0.2)  # Wait briefly to stabilize focus after closing the tab.
        else:  # When no opened tabs tracked, skip closure to avoid closing base tab.
            print(f"{BackgroundColors.YELLOW}[DEBUG] No opened tab to close; skipping to preserve main tab{Style.RESET_ALL}")  # Log skipping closure.
    except Exception as e:  # Handle unexpected exceptions during closure.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close browser tab: {e}{Style.RESET_ALL}")  # Log warning on failure.

    return opened_tabs  # Return updated opened tabs count.


def click_download_button(download_img: Path) -> str:
    """
    Clicks the download button with retry fallback and scaled coordinates.

    :param download_img: Path to the download button image.
    :return: Method name used for the click.
    """

    start = time.time()  # Store start timestamp for retry window.
    
    scroll_extension_tab_to_start_button()  # Ensure the download button is visible by scrolling the extension tab before attempting to locate the download button image.
    
    while time.time() - start < 3.0:  # Repeat until timeout window expires.
        box = locate_image(download_img)  # Locate download image on screen.

        if box is not None:  # Verify image was found.
            pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
            return "ImageSearch"  # Return image search method label.

        time.sleep(0.2)  # Wait before retrying image search.

    scaled_x, scaled_y = get_scaled_fallback_coords(DOWNLOAD_BUTTON_X_REF, DOWNLOAD_BUTTON_Y_REF)  # Compute scaled download button fallback coordinates.
    pyautogui.click(scaled_x, scaled_y)  # Click scaled download button coordinates.
    return "Coordinates"  # Return coordinates method label.


def click_enable_permission(enable_img: Path) -> str:
    """
    Clicks the extension enable permission button when present.

    :param enable_img: Path to the extension enable-permission image.
    :return: Method name used for the click.
    """

    start = time.time()  # Store start timestamp for optional retry window.

    while time.time() - start <= 1.2:  # Repeat until timeout window expires.
        box = locate_image(enable_img)  # Locate enable-permission image on screen.

        if box is not None:  # Verify image was found before clicking.
            click_box_center(box)  # Click center of detected enable-permission button box.
            return "ImageSearch"  # Return image search method label when clicked.

        time.sleep(0.1)  # Wait before retrying image search when not found.

    return "NotFound"  # Return NotFound when no enable-permission image was detected.


def prevent_screen_lock(last_move_ts: float, interval_seconds: float = 50.0) -> float:
    """
    Moves the cursor by a single pixel every defined interval to prevent screen lock.

    :param last_move_ts: Timestamp of the last cursor movement.
    :param interval_seconds: Minimum seconds between cursor movements.
    :return: Updated timestamp of last cursor movement.
    """

    current_time = time.time()  # Capture current timestamp for interval comparison.

    if (current_time - last_move_ts) >= interval_seconds:  # Verify whether interval threshold was reached.
        try:  # Attempt cursor movement.
            x, y = pyautogui.position()  # Get current cursor position.
            pyautogui.moveTo(x + 1, y)  # Move cursor by +1 pixel on X axis.
            pyautogui.moveTo(x, y)  # Move cursor back to original position to avoid displacement.

            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Prevented screen lock via cursor jitter.{Style.RESET_ALL}")  # Log cursor movement action.

        except Exception as e:  # Handle unexpected failures from pyautogui.
            verbose_output(f"{BackgroundColors.YELLOW}[WARNING] Failed to move cursor for screen lock prevention: {e}{Style.RESET_ALL}")  # Log failure.

        return current_time  # Update last movement timestamp.

    return last_move_ts  # Return unchanged timestamp when interval not reached.


def watch_for_save_dialog_and_confirmation(save_button_img: Path, confirmation_img: Path, confirmation_alt_img: Path, failed_file_download_img: Path) -> str:
    """
    Watches for the optional Chrome "Save As" dialog and clicks the save button if it appears,
    while also monitoring for the confirmation image to stop early.

    :param save_button_img: Path to the save button image.
    :param confirmation_img: Path to the confirmation image.
    :param confirmation_alt_img: Path to the alternative confirmation image.
    :param failed_file_download_img: Path to the failed file download image.
    :return: Detection status string.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Watching for save dialog and confirmation...{Style.RESET_ALL}")  # Log start of save dialog and confirmation monitoring.

    start_time = time.time()  # Record start time to enforce same timeout behavior as confirmation polling.
    last_cursor_move_ts = start_time  # Initialize last cursor movement timestamp for screen lock prevention.
    max_wait_time = 60 * 10  # Match wait_for_download_confirmation total wait time (60 iterations * 5 seconds).

    while (time.time() - start_time) < max_wait_time:  # Loop until timeout window is reached.
        scroll_extension_tab_to_start_button()  # Scroll again after potential permission click to ensure the Start download button is visible regardless of permission prompt presence or screen size.
        last_cursor_move_ts = prevent_screen_lock(last_cursor_move_ts)  # Periodically move cursor to prevent screen lock.

        box = enhanced_locate_image(save_button_img)  # Attempt to locate the optional save button image on screen.
        pyautogui.press("enter")  # Confirm save action via Enter key when required.
        
        if box is not None:  # Verify image was found.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Save button detected; clicking to confirm download.{Style.RESET_ALL}")  # Log save button detection and click action.
            click_box_center(box)  # Click center of detected save button box.
            time.sleep(0.1)  # Wait briefly to allow UI to process click before sending key event.
            pyautogui.press("enter")  # Confirm save action via Enter key when required.
        
        if enhanced_locate_image(confirmation_img) is not None or enhanced_locate_image(confirmation_alt_img) is not None:  # Verify for confirmation images to allow early exit from waiting when detected.
            time.sleep(1)  # Wait briefly after confirmation detection to allow any UI changes to settle before proceeding.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Confirmation detected during save dialog watch; exiting early.{Style.RESET_ALL}")  # Log early exit due to confirmation detection.
            box = enhanced_locate_image(save_button_img)  # Attempt to locate the optional save button image on screen.
            if box is not None:  # Verify image was found.
                verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Save button detected; clicking to confirm download.{Style.RESET_ALL}")  # Log save button detection and click action.
                click_box_center(box)  # Click center of detected save button box.
                time.sleep(0.1)  # Wait briefly to allow UI to process click before sending key event.
                pyautogui.press("enter")  # Confirm save action via Enter key when required.
            return "Image Detected"  # Return confirmation detection method.
        
        if enhanced_locate_image(failed_file_download_img) is not None:  # Verify for failed file download image to allow early exit with failure status when detected.
            print(f"{BackgroundColors.RED}[DEBUG] Detected failed file download image during save dialog watch; exiting early with failure status.{Style.RESET_ALL}")  # Log early exit due to download failure detection.
            return "Download Failed"  # Return download failure status.

        time.sleep(1)  # Wait 1 second before next verification cycle.

    verbose_output(f"{BackgroundColors.YELLOW}[DEBUG] Save dialog and confirmation watch timed out after {max_wait_time} seconds.{Style.RESET_ALL}")  # Log timeout of save dialog and confirmation monitoring.
    return "Timeout"  # Return timeout status after wait window expires.


def wait_for_download_file_stabilization(downloads_dirs: List[str], timeout: float = 10.0, interval: float = 0.5, recent_window: float = 10.0) -> None:
    """
    Waits until no recently modified or temporary download files are present in monitored directories.

    :param downloads_dirs: Paths to monitored downloads directories.
    :param timeout: Maximum time to wait for stabilization.
    :param interval: Delay between verification cycles.
    :param recent_window: Time window in seconds to consider files as recently modified.
    :return: None
    """
    
    verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Waiting for download file stabilization in monitored directories...{Style.RESET_ALL}")  # Log start of download file stabilization monitoring.

    start_time = time.time()  # Record start time for timeout enforcement.
    normalized_dirs = [str(Path(d).resolve()) for d in downloads_dirs]  # Normalize monitored directories.
    last_seen_temp_file: Optional[str] = None  # Track last observed temporary filename for rename detection.

    while (time.time() - start_time) < timeout:  # Loop until timeout expires.
        unstable_found = False  # Track whether unstable files are detected.
        now = time.time()  # Capture current timestamp for modification comparison.

        for normalized_dir in normalized_dirs:  # Iterate monitored directories.
            try:  # Attempt directory listing.
                for name in os.listdir(normalized_dir):  # Iterate files in directory.
                    file_path = Path(normalized_dir) / name  # Build full file path.

                    if not file_path.exists():  # Verify file still exists.
                        continue  # Skip removed files.

                    if name.endswith(".crdownload") or name.endswith(".tmp"):  # Verify temporary download file presence.
                        last_seen_temp_file = name  # Track latest temporary filename.
                        verbose_output(f"{BackgroundColors.YELLOW}[DEBUG] Detected temporary download file: {BackgroundColors.CYAN}{file_path}{BackgroundColors.YELLOW}; waiting for stabilization...{Style.RESET_ALL}")  # Log detection of temporary file with path details when verbose.
                        unstable_found = True  # Mark unstable file detected.
                        break  # Stop scanning current directory.

                    try:  # Attempt to read file metadata.
                        mtime = file_path.stat().st_mtime  # Retrieve last modification time.
                    except Exception:  # Handle stat access issues.
                        continue  # Skip problematic file.

                    if (now - mtime) <= recent_window:  # Verify file was modified recently.
                        if last_seen_temp_file is not None: verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Download finalized: {BackgroundColors.CYAN}{last_seen_temp_file}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{name}{Style.RESET_ALL}")  # Log temp-to-final filename transition.
                        unstable_found = True  # Mark unstable file detected.
                        break  # Stop scanning current directory.
                if unstable_found:  # Verify if unstable file was found in this directory.
                    break  # Stop scanning remaining directories.
            except Exception:  # Handle directory access issues.
                continue  # Skip directory on failure.
        if not unstable_found:  # Verify no unstable files remain.
            verbose_output(f"{BackgroundColors.GREEN}[DEBUG] No unstable download files detected; stabilization achieved.{Style.RESET_ALL}")  # Log stabilization success when no unstable files are found.
            return  # Exit when downloads are stabilized.

        time.sleep(interval)  # Wait before next verification cycle.


def close_extension_download_tab(close_download_tab_img: Path) -> str:
    """
    Closes extension download tab using image or scaled fallback coordinates.

    :param close_download_tab_img: Path to close tab image.
    :return: Method name used for the click.
    """

    box = locate_image(close_download_tab_img)  # Locate close tab image on screen.

    if box is not None:  # Verify image was found.
        click_x = int(box.left + (box.width * 0.75))  # Compute X coordinate for right-quarter click within the matched box.
        click_y = int(box.top + (box.height / 2))  # Compute Y coordinate for vertically centered click within the matched box.
        pyautogui.click(click_x, click_y)  # Click the right-quarter of the matched box.
        time.sleep(0.5)  # Wait briefly after image click.
        return "ImageSearch"  # Return image search method label.

    scaled_x, scaled_y = get_scaled_fallback_coords(CLOSE_DOWNLOAD_TAB_X_REF, CLOSE_DOWNLOAD_TAB_Y_REF)  # Compute scaled close tab fallback coordinates.
    pyautogui.click(scaled_x, scaled_y)  # Click scaled close tab coordinates.
    time.sleep(0.5)  # Wait briefly after fallback click.
    return "Coordinates"  # Return coordinates method label.


def click_go_to_product_button(mercado_livre_img: Path) -> str:
    """
    Clicks MercadoLivre go-to-product button when available.

    :param mercado_livre_img: Path to MercadoLivre go-to-product image.
    :return: Action status string.
    """

    box = locate_image(mercado_livre_img)  # Locate MercadoLivre image on screen.

    if box is not None:  # Verify image was found.
        click_box_center(box)  # Click center of detected box to go to product page.
        time.sleep(5)  # Wait for page transition after clicking the product button.

        return "MercadoLivre Go To Product"  # Return action performed status.

    return "Not Found / Skipped"  # Return skipped status.


def close_current_tab() -> None:
    """
    Closes the current browser tab.

    :return: None
    """

    try:  # Attempt to close the current browser tab with graceful handling.
        pyautogui.hotkey("ctrl", "w")  # Trigger close-tab hotkey.
        time.sleep(0.4)  # Wait after closing the tab to allow focus stabilization.
        verbose_output(f"{BackgroundColors.GREEN}[DEBUG] Closed browser tab after processing URL{Style.RESET_ALL}")  # Log debug success message.
    except Exception as e:  # Handle failures to close the tab without crashing.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close browser tab: {e}{Style.RESET_ALL}")  # Log warning when closure fails.


def add_method(methods: Dict[str, List[int]], method: str, tab_index: int) -> None:
    """
    Adds a method usage entry to report dictionary.

    :param methods: Dictionary mapping methods to tab indices.
    :param method: Method label to append.
    :param tab_index: Tab index associated with method usage.
    :return: None
    """

    methods.setdefault(method, []).append(tab_index)  # Append tab index to grouped method list.


def handle_post_download_methods(ext_methods: Dict[str, List[int]], download_methods: Dict[str, List[int]], completion_methods: Dict[str, List[int]], close_methods: Dict[str, List[int]], extension_method: str, download_method: str, confirmation_method: str, close_method: str, current_tab: int) -> None:
    """
    Handles method tracking after download

    :param ext_methods: Dictionary tracking extension click methods by tab index.
    :param download_methods: Dictionary tracking download click methods by tab index.
    :param completion_methods: Dictionary tracking completion detection methods by tab index.
    :param close_methods: Dictionary tracking close tab methods by tab index.
    :param extension_method: Method used for extension click action.
    :param download_method: Method used for download click action.
    :param confirmation_method: Method used for download confirmation detection.
    :param close_method: Method used for close tab action.
    :param current_tab: Current browser tab index for method tracking association.
    :return: None
    """

    add_method(ext_methods, extension_method, current_tab)  # Store extension method for report.
    add_method(download_methods, download_method, current_tab)  # Store download method for report.
    add_method(completion_methods, confirmation_method, current_tab)  # Store completion method for report.
    add_method(close_methods, close_method, current_tab)  # Store close method for report.


def safely_close_product_tab(opened_tabs: int) -> int:
    """
    Safely closes the current product tab and restores focus.

    :param opened_tabs: Current opened tabs counter.
    :return: Updated opened tabs counter.
    """

    try:  # Attempt safe tab closure and focus restoration for download flow.
        if opened_tabs > 0:  # Verify that a tab opened by this loop exists before closing.
            close_current_tab()  # Close the current product tab that was opened earlier.
            opened_tabs -= 1  # Decrement opened tabs counter after successful closure.
            time.sleep(0.2)  # Wait briefly to stabilize focus after closing the tab.
        else:  # When no opened tabs tracked, skip closure to avoid closing base tab.
            print(f"{BackgroundColors.YELLOW}[DEBUG] No opened tab to close; skipping to preserve main tab{Style.RESET_ALL}")  # Log skipping closure.
    except Exception as e:  # Handle unexpected exceptions during closure.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close browser tab: {e}{Style.RESET_ALL}")  # Log warning on failure.

    return opened_tabs  # Return updated opened tabs counter.


def reset_browser_context_for_retry(close_download_tab_img: Path) -> bool:
    """
    Resets the browser context for a download retry by closing tabs and reopening the automation window.

    :param close_download_tab_img: Path to close extension download tab image.
    :return: True when the fresh automation context is ready, otherwise False.
    """

    close_extension_download_tab(close_download_tab_img)  # Close extension download tab before browser window reset.

    try:  # Attempt to close the current browser tab before window teardown.
        pyautogui.hotkey("ctrl", "w")  # Close current browser tab via hotkey.
        time.sleep(0.3)  # Wait after tab closure to allow browser to stabilize.
    except Exception as e:  # Handle tab closure failure without interrupting retry flow.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close browser tab during retry reset: {e}{Style.RESET_ALL}")  # Log warning when tab closure fails during retry.

    try:  # Attempt to close the current browser window to clear cached state.
        current_os = platform.system().lower()  # Detect current operating system for window close hotkey selection.

        if current_os == "darwin":  # Verify macOS for Command+Q hotkey.
            pyautogui.hotkey("command", "q")  # Send Command+Q to quit Chrome on macOS.
        else:  # Use Control+Shift+W on Windows/Linux to close the current window.
            pyautogui.hotkey("ctrl", "shift", "w")  # Send Control+Shift+W to close current Chrome window on Windows/Linux.

        time.sleep(0.6)  # Wait after close hotkey to allow window teardown.
    except Exception as e:  # Handle window closure failure without interrupting retry flow.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to close browser window during retry reset: {e}{Style.RESET_ALL}")  # Log warning when window closure fails during retry.

    time.sleep(1)  # Wait one second before reopening the browser context to avoid residual state.
    context_ready = prepare_dedicated_chrome_window_for_automation()  # Reopen fresh dedicated Chrome automation window.
    return context_ready  # Return browser context readiness status.


def join_array(values: List[int]) -> str:
    """
    Joins integer list into comma-separated string.

    :param values: Integer list to be joined.
    :return: Comma-separated string.
    """

    return ", ".join(str(v) for v in values)  # Join integers into comma-separated text.


def format_execution_time(total_seconds: int) -> str:
    """
    Formats total seconds into detailed time text.

    :param total_seconds: Total elapsed seconds.
    :return: Formatted time string.
    """

    h = total_seconds // 3600  # Compute hour component.
    m = (total_seconds % 3600) // 60  # Compute minute component.
    s = total_seconds % 60  # Compute second component.
    return f"{h:02d}:{m:02d}:{s:02d} ({h}h {m}m {s}s)"  # Return formatted execution time.


def click_share_affiliate_url_button(share_button_img: Path) -> str:
    """
    Locate and click the Share Affiliate URL button for Amazon product page.

    :param share_button_img: Path to the ShareAffiliateURL-Amazon.png image file.
    :return: String indicating which image was used or Not Found.
    """

    window_active = activate_automation_window()  # Activate dedicated automation Chrome window before image search.

    if not window_active:  # Verify whether Chrome window activation succeeded before searching share button images.
        print(f"{BackgroundColors.YELLOW}[WARNING] Unable to activate Chrome window before Share Affiliate URL button detection.{Style.RESET_ALL}")  # Log warning when Chrome activation fails before share-button search.

    window_bounds = get_active_window_bounds()  # Retrieve active Chrome window bounds for region-constrained image search.
    region_left = int(window_bounds.get("left", 0))  # Resolve left coordinate for region-constrained image search, preserving negative secondary-monitor offsets.
    region_top = int(window_bounds.get("top", 0))  # Resolve top coordinate for region-constrained image search, preserving negative secondary-monitor offsets.
    region_width = max(1, int(window_bounds.get("width", 0)))  # Resolve safe width for region-constrained image search.
    region_height = max(1, int(window_bounds.get("height", 0)))  # Resolve safe height for region-constrained image search.
    search_region = (region_left, region_top, region_width, region_height)  # Build active Chrome window region tuple for share-button image search.
    max_verifications = 60  # Define maximum number of image-detection retries.

    for _ in range(max_verifications):  # Iterate through share-button detection attempts.
        box = locate_image(share_button_img)  # Attempt to locate share affiliate URL button image without region constraint for higher detection reliability at the cost of potential false positives outside the window.

        if box is not None:  # Verify if share affiliate URL image was detected.
            click_box_center(box)  # Click center of detected share button box to trigger URL copy action.
            time.sleep(0.5)  # Wait briefly after image-based click.
            verbose_output(f"{BackgroundColors.GREEN}Clicked share button using image: {BackgroundColors.CYAN}{share_button_img.name}{BackgroundColors.GREEN}{Style.RESET_ALL}")  # Print name of used image.
            return "ImageSearch"  # Return image search method label for image.
        time.sleep(0.2)  # Wait before retrying image search.

    # Reference values: Screen: 1491, 159; Window: 621, -36; Client: 613, -67 (default)
    REFERENCE_SCREEN_WIDTH = 1920  # Set reference screen width for scaling.
    REFERENCE_SCREEN_HEIGHT = 1080  # Set reference screen height for scaling.
    REFERENCE_X = 1491  # Set reference X coordinate for share button.
    REFERENCE_Y = 159  # Set reference Y coordinate for share button.

    screen_width, screen_height = get_fallback_screen_dimensions(REFERENCE_SCREEN_WIDTH, REFERENCE_SCREEN_HEIGHT)  # Retrieve current screen dimensions with fallback.

    scaled_x, scaled_y = compute_scaled_coordinates(REFERENCE_X, REFERENCE_Y, screen_width, screen_height, REFERENCE_SCREEN_WIDTH, REFERENCE_SCREEN_HEIGHT)  # Compute scaled coordinates for current screen.

    click_x, click_y = adjust_coordinates_for_window_offset(scaled_x, scaled_y, window_bounds)  # Adjust coordinates for window offset.

    return execute_fallback_click(click_x, click_y)


def get_fallback_screen_dimensions(reference_width: int, reference_height: int) -> tuple:
    """
    Retrieve current screen dimensions with fallback to reference values.

    :param reference_width: Reference screen width for scaling.
    :param reference_height: Reference screen height for scaling.
    :return: Tuple of current screen width and height.
    """

    try: return get_screen_dimensions()  # Retrieve current screen dimensions using pyautogui backend.
    except Exception: return reference_width, reference_height  # Return reference dimensions if retrieval fails.


def compute_scaled_coordinates(reference_x: int, reference_y: int, screen_width: int, screen_height: int, reference_width: int, reference_height: int) -> tuple:
    """
    Compute scaled coordinates for current screen dimensions.

    :param reference_x: Reference X coordinate for scaling.
    :param reference_y: Reference Y coordinate for scaling.
    :param screen_width: Current screen width.
    :param screen_height: Current screen height.
    :param reference_width: Reference screen width.
    :param reference_height: Reference screen height.
    :return: Tuple of scaled X and Y coordinates.
    """

    scale_x = screen_width / reference_width  # Compute horizontal scaling factor.
    scale_y = screen_height / reference_height  # Compute vertical scaling factor.
    scaled_x = int(reference_x * scale_x)  # Apply horizontal scaling to reference X coordinate.
    scaled_y = int(reference_y * scale_y)  # Apply vertical scaling to reference Y coordinate.
    return scaled_x, scaled_y  # Return tuple of scaled coordinates.


def adjust_coordinates_for_window_offset(scaled_x: int, scaled_y: int, window_bounds: dict) -> tuple:
    """
    Adjust scaled coordinates for window offset.

    :param scaled_x: Scaled X coordinate.
    :param scaled_y: Scaled Y coordinate.
    :param window_bounds: Dictionary with window left and top offsets.
    :return: Tuple of adjusted X and Y coordinates.
    """

    offset_x = window_bounds.get("left", 0)  # Retrieve window left offset.
    offset_y = window_bounds.get("top", 0)  # Retrieve window top offset.
    click_x = offset_x + scaled_x  # Adjust X coordinate relative to window left edge.
    click_y = offset_y + scaled_y  # Adjust Y coordinate relative to window top edge.
    return click_x, click_y  # Return tuple of adjusted coordinates.


def execute_fallback_click(click_x: int, click_y: int) -> str:
    """
    Execute click at fallback coordinates with error handling.

    :param click_x: X coordinate for click action.
    :param click_y: Y coordinate for click action.
    :return: String indicating click result.
    """

    try:
        pyautogui.click(click_x, click_y)  # Click at computed fallback coordinates.
        time.sleep(0.5)  # Wait briefly after fallback click.
        verbose_output(f"{BackgroundColors.YELLOW}[COORDS] Used fallback coordinates: ({click_x}, {click_y}){Style.RESET_ALL}")  # Print fallback coordinates used.
        return "Coordinates"  # Return coordinates method label.
    except Exception as e:
        verbose_output(f"{BackgroundColors.RED}[ERROR] Failed to click fallback coordinates: {e}{Style.RESET_ALL}")  # Print error if click fails.
        return "Not Found"  # Return not found status if click fails.


def get_url_from_clipboard() -> str:
    """
    Extract affiliate URL from system clipboard after Ctrl+C copy operation.

    :return: Clipboard content string or empty string if retrieval fails.
    """

    pyautogui.hotkey("ctrl", "c")  # Trigger copy-to-clipboard hotkey.
    time.sleep(0.3)  # Wait for clipboard operation to complete.
    return normalize_affiliate_url(get_clipboard_text())  # Return normalized clipboard URL after copy operation.


def get_clipboard_text() -> str:
    """
    Retrieve clipboard content using available platform backends.

    :param: None.
    :return: Raw clipboard content string or empty string on failure.
    """

    try:  # Attempt clipboard retrieval using tkinter backend.
        root = tk.Tk()  # Create hidden tkinter root instance for clipboard access.
        root.withdraw()  # Hide tkinter root window from display.
        clipboard_content = root.clipboard_get()  # Retrieve clipboard content from active system clipboard.
        root.destroy()  # Destroy tkinter root window after retrieval.
        return str(clipboard_content)  # Return clipboard content converted to string.
    except Exception:  # Handle tkinter clipboard retrieval failures.
        pass  # Continue execution with subprocess-based fallback.

    try:  # Attempt clipboard retrieval using PowerShell backend.
        result = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], capture_output=True, text=True)  # Execute PowerShell clipboard command.
        return str(result.stdout)  # Return clipboard content from PowerShell output.
    except Exception:  # Handle subprocess clipboard retrieval failures.
        return ""  # Return empty string when all clipboard retrieval methods fail.


def normalize_affiliate_url(url: str) -> str:
    """
    Normalize affiliate URL text before validation and usage.

    :param url: URL text to normalize.
    :return: Normalized URL string.
    """

    return str(url).strip() if isinstance(url, str) else ""  # Return stripped URL when input is string, otherwise return empty string.


def is_valid_affiliate_url(url: str) -> bool:
    """
    Validate strict Amazon affiliate URL requirements.

    :param url: URL text to validate.
    :return: True when URL matches strict affiliate constraints, otherwise False.
    """

    normalized_url = normalize_affiliate_url(url)  # Normalize URL text before strict validation.

    if normalized_url == "":  # Verify whether URL is empty after normalization.
        return False  # Return validation failure when URL is empty.

    lower_url = normalized_url.lower()  # Convert URL text to lowercase for case-insensitive verification.

    if "amazon." not in lower_url and "amzn.to" not in lower_url:  # Verify whether Amazon domain marker exists in URL.
        return False  # Return validation failure when Amazon domain marker is missing.

    has_product_path = "/dp/" in lower_url or "/gp/product/" in lower_url  # Resolve whether URL includes full Amazon product path markers.
    has_short_domain = "amzn.to" in lower_url  # Resolve whether URL uses Amazon short-link domain format.

    if not has_product_path and not has_short_domain:  # Verify whether URL contains supported full-product path or short-link domain.
        return False  # Return validation failure when supported path/domain markers are missing.

    if "tag=" not in lower_url and not has_short_domain:  # Verify whether affiliate tag parameter exists in full Amazon URLs.
        return False  # Return validation failure when affiliate tag parameter is missing.

    if normalized_url != url.strip():  # Verify whether normalized URL differs from stripped source representation.
        return False  # Return validation failure when normalization reveals whitespace anomalies.

    return True  # Return validation success when all strict affiliate constraints pass.


def wait_for_valid_affiliate_url(previous_url: str, timeout: int = 5) -> str:
    """
    Wait for a valid renewed affiliate URL that differs from previous URL.

    :param previous_url: Previously known URL used for difference verification.
    :param timeout: Maximum wait duration in seconds for valid clipboard URL.
    :return: Valid normalized affiliate URL or empty string when timeout expires.
    """

    start_time = time.time()  # Capture start time for timeout guard.
    normalized_previous_url = normalize_affiliate_url(previous_url)  # Normalize previous URL for equality verification.

    while time.time() - start_time < max(1, int(timeout)):  # Iterate until timeout expires while reading clipboard content.
        pyautogui.hotkey("ctrl", "c")  # Trigger copy action to refresh clipboard with current affiliate URL.
        time.sleep(0.3)  # Wait briefly to allow clipboard propagation.
        clipboard_url = normalize_affiliate_url(get_clipboard_text())  # Retrieve and normalize current clipboard URL candidate.

        if clipboard_url == "":  # Verify whether clipboard URL candidate is empty.
            print(f"{BackgroundColors.YELLOW}[WARNING] Clipboard URL is empty while waiting for renewed Amazon affiliate URL.{Style.RESET_ALL}")  # Log warning for empty clipboard candidate.
            time.sleep(0.25)  # Wait briefly before retrying clipboard retrieval.
            continue  # Continue retry loop after empty clipboard candidate.

        if not validate_amazon_affiliate_url(clipboard_url):  # Verify whether clipboard candidate satisfies project affiliate URL validation.
            print(f"{BackgroundColors.YELLOW}[WARNING] Clipboard URL failed strict Amazon affiliate validation: {BackgroundColors.CYAN}{clipboard_url}{Style.RESET_ALL}")  # Log warning for invalid clipboard candidate.
            time.sleep(0.25)  # Wait briefly before retrying invalid clipboard candidate.
            continue  # Continue retry loop after invalid clipboard candidate.

        if normalized_previous_url != "" and clipboard_url == normalized_previous_url:  # Verify whether renewed URL differs from previous URL when previous URL exists.
            print(f"{BackgroundColors.YELLOW}[WARNING] Clipboard URL matches previous Amazon URL and will be retried.{Style.RESET_ALL}")  # Log warning for unchanged clipboard candidate.
            time.sleep(0.25)  # Wait briefly before retrying unchanged clipboard candidate.
            continue  # Continue retry loop after unchanged clipboard candidate.

        return clipboard_url  # Return valid renewed affiliate URL when strict validation succeeds.

    print(f"{BackgroundColors.YELLOW}[WARNING] Timed out waiting for a valid renewed Amazon affiliate URL from clipboard.{Style.RESET_ALL}")  # Log warning when timeout expires without valid URL.
    return ""  # Return empty string when timeout expires without valid renewed URL.


def validate_amazon_affiliate_url(url: str) -> bool:
    """
    Validate if URL is in correct Amazon affiliate format.

    :param url: URL string to validate.
    :return: True if URL matches Amazon affiliate pattern, False otherwise.
    """

    normalized_url = normalize_affiliate_url(url)  # Normalize URL before validation flow.

    if not is_valid_affiliate_url(normalized_url):  # Verify strict affiliate URL constraints before pattern matching.
        return False  # Return validation failure when strict constraints are not satisfied.

    try:  # Attempt URL validation using project affiliate pattern.
        if isinstance(AFFILIATE_URL_PATTERN, str):  # Verify whether AFFILIATE_URL_PATTERN is string regex.
            return bool(re.search(AFFILIATE_URL_PATTERN, normalized_url, re.IGNORECASE))  # Return validation result from string pattern matching.
        return bool(AFFILIATE_URL_PATTERN.search(normalized_url))  # Return validation result from compiled pattern matching.
    except Exception:  # Handle regex or parsing failures.
        return False  # Return validation failure on exception.


def replace_url_in_line(line: str, old_url: str, new_url: str) -> Tuple[str, bool]:
    """
    Replace old URL in a single line while preserving trailing content.

    :param line: Single line of text to process.
    :param old_url: Old URL to search for in the line.
    :param new_url: New URL to replace the old URL with.
    :return: Tuple containing the possibly modified line and a boolean indicating replacement.
    """

    tokens = line.split()  # Split current line into whitespace-separated tokens.
    if tokens and old_url in tokens[0]:  # Verify if the first token contains the old URL.
        new_line = line.replace(tokens[0], new_url, 1)  # Replace only the first token occurrence with new URL.
        return new_line, True  # Return modified line and True to indicate replacement.
    elif old_url in line:  # Verify if the old URL appears elsewhere in the line.
        new_line = line.replace(old_url, new_url)  # Replace all occurrences of the old URL in the line.
        return new_line, True  # Return modified line and True to indicate replacement.
    return line, False  # Return original line and False when no replacement occurred.


def write_atomic_temp_file(urls_file: Path, updated_lines: List[str]) -> None:
    """
    Write updated lines to a temporary file and atomically replace the original.

    :param urls_file: Path to the target urls file to be replaced.
    :param updated_lines: List of lines that constitute the updated file content.
    :return: None
    """

    temp_path = urls_file.with_name(f"{urls_file.name}.tmp-{os.getpid()}-{int(time.time() * 1000)}")  # Build unique temporary file path to avoid collisions.
    temp_text = "\n".join(updated_lines) + "\n"  # Join updated lines and ensure the file ends with a newline.

    parent_dir = urls_file.parent  # Get parent directory of the target file for writability verification.

    if not os.access(str(parent_dir), os.W_OK):  # Verify whether the parent directory is writable before attempting to write the temp file.
        print(f"{BackgroundColors.YELLOW}[WARNING] Cannot write to directory: {BackgroundColors.CYAN}{parent_dir}{Style.RESET_ALL}")
        return
    if urls_file.exists() and not os.access(str(urls_file), os.W_OK):  # Verify whether the file is writable before attempting replacement.
        print(f"{BackgroundColors.YELLOW}[WARNING] Skipping read-only file: {BackgroundColors.CYAN}{urls_file}{Style.RESET_ALL}")
        return

    try:  # Attempt safe write + atomic replace sequence.
        with open(temp_path, "w", encoding="utf-8") as f:  # Open temporary file for writing.
            f.write(temp_text)  # Write full content to temp file.
            f.flush()  # Flush Python buffer to OS.
            os.fsync(f.fileno())  # Force write to disk to avoid data loss on crash.

        os.replace(str(temp_path), str(urls_file))  # Atomically replace the original file with the temp file.

    except Exception as e:  # Handle any failure during write or replace.
        try:  # Attempt cleanup of temp file if it exists.
            if temp_path.exists(): temp_path.unlink()  # Remove orphan temp file.
        except Exception:  # Ignore cleanup errors.
            pass
        raise e  # Re-raise original exception to caller.


def read_file_lines(filepath: str) -> list:
    """
    Read file lines into a list.

    :param filepath: Path string to the file to read.
    :return: List of file lines or empty list on error.
    """

    try:  # Attempt to read the file into memory.
        path_obj = Path(filepath)  # Create Path object from the provided filepath string.
        text = path_obj.read_text(encoding="utf-8", errors="ignore")  # Read full file text using safe encoding.
        lines = text.splitlines()  # Split the file text into separate lines.
        return lines  # Return the list of lines read from the file.
    except Exception as e:  # Handle file IO exceptions gracefully.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to read file {filepath}: {e}{Style.RESET_ALL}")  # Log read failure with warning style.
        return []  # Return empty list when reading fails.


def url_exists_in_file(filepath: str, url: str) -> bool:
    """
    Verify whether a URL string exists inside a file.

    :param filepath: Path string to the file to search.
    :param url: URL string to search for within the file.
    :return: True when the URL appears in the file, otherwise False.
    """

    lines = read_file_lines(filepath)  # Read file lines using helper function.
    for line in lines:  # Iterate each line to search for the URL.
        if url in line:  # Verify whether the URL substring appears in the current line.
            return True  # Return True immediately when a match is found.
    return False  # Return False when no matching line is found.


def validate_url_update(old_url: str, new_url: str, filepaths: list) -> bool:
    """
    Validate that the new URL is present in all target files and the old URL is removed.

    :param old_url: Original URL that was replaced.
    :param new_url: Newly generated affiliate URL expected to be present.
    :param filepaths: List of file path strings to validate against.
    :return: True when validation passes for all files, otherwise False.
    """

    all_ok = True  # Initialize aggregated validation flag assuming success.
    for fp in filepaths:  # Iterate each file path to validate presence and absence of URLs.
        if not os.access(fp, os.W_OK):  # Verify whether the current file is writable before attempting validation.
            print(f"{BackgroundColors.YELLOW}[DEBUG] Skipping validation for read-only file: {BackgroundColors.CYAN}{fp}{Style.RESET_ALL}")
            continue  # Skip validation for read-only files to avoid false negatives.
        exists_new = url_exists_in_file(fp, new_url)  # Verify new URL presence in the file.
        if not exists_new:  # Verify whether new URL is missing in the current file.
            all_ok = False  # Mark aggregated flag as failed when missing new URL.
        exists_old = url_exists_in_file(fp, old_url)  # Verify old URL presence in the file.
        if exists_old:  # Verify whether old URL is still present in the current file.
            all_ok = False  # Mark aggregated flag as failed when old URL remains.
    return all_ok  # Return aggregated validation result.


def print_url_update(old_url: str, new_url: str) -> None:
    """
    Print colored terminal lines showing the old and new URLs.

    :param old_url: Original URL string to display.
    :param new_url: Renewed URL string to display.
    :return: None.
    """

    verbose_output(f"{BackgroundColors.RED}[OLD]{BackgroundColors.CYAN} {old_url}")  # Print OLD URL label in red and URL in cyan.
    verbose_output(f"{BackgroundColors.GREEN}[NEW]{BackgroundColors.CYAN} {new_url}{Style.RESET_ALL}")  # Print NEW URL label in green and URL in cyan then reset style.


def update_urls_txt_with_new_amazon_url(old_url: str, new_url: str, urls_file: Path) -> bool:
    """
    Update urls.txt file by replacing old Amazon URL with newly copied affiliate URL.

    :param old_url: Original Amazon URL to replace.
    :param new_url: New affiliate URL copied from clipboard.
    :param urls_file: Path to the urls.txt file.
    :return: True if update succeeded, False otherwise.
    """

    if urls_file.exists() and not os.access(str(urls_file), os.W_OK):  # Verify whether the urls.txt file exists and is writable before attempting update.
        print(f"{BackgroundColors.YELLOW}[WARNING] Skipping read-only file: {BackgroundColors.CYAN}{urls_file}{Style.RESET_ALL}")
        return False

    try:  # Attempt file read and update operation.
        if not urls_file.exists():  # Verify urls.txt file exists before reading.
            print(f"{BackgroundColors.RED}urls.txt file not found at: {urls_file.resolve()}{Style.RESET_ALL}")  # Log error when urls.txt is missing.
            return False  # Return failure when file does not exist.

        raw_text = urls_file.read_text(encoding="utf-8")  # Read the full urls.txt content into memory.
        lines = raw_text.splitlines()  # Split the content into individual lines for processing.

        updated_lines: List[str] = []  # Initialize container for updated lines collected during processing.
        replacement_occurred = False  # Initialize flag to indicate whether any replacement was performed.

        for line in lines:  # Iterate each line and delegate replacement to helper function.
            new_line, replaced = replace_url_in_line(line, old_url, new_url)  # Use helper to replace URL in single line.
            updated_lines.append(new_line)  # Append processed line to updated_lines container.
            if replaced:  # Verify whether helper reported a replacement for the current line.
                replacement_occurred = True  # Mark that a replacement occurred for later verification.

        if not replacement_occurred:  # Verify whether any replacement actually took place.
            return False  # Return failure when no replacement was detected in the file.

        write_atomic_temp_file(urls_file, updated_lines)  # Write updated content atomically using helper function.
        verbose_output(f"{BackgroundColors.GREEN}Updated Amazon URL in {BackgroundColors.CYAN}{urls_file.resolve()}{Style.RESET_ALL}")  # Log successful URL update when verbose enabled.
        return True  # Return success after atomic file replacement.
    except Exception as e:  # Handle file IO or replacement errors.
        verbose_output(f"{BackgroundColors.RED}Failed to update Amazon URL in {BackgroundColors.CYAN}{urls_file.resolve()}{Style.RESET_ALL}: {e}")  # Log URL update failure when verbose enabled.
        return False  # Return failure when exception occurs.


def resolve_outputs_directory() -> Path:
    """
    Resolve Outputs directory path from project root.

    :param: None.
    :return: Resolved Outputs directory path.
    """

    outputs_dir = Path(PROJECT_ROOT) / "Outputs"  # Build Outputs path from project root.
    return outputs_dir.resolve()  # Return resolved Outputs directory path.


def replace_url_in_file(filepath: str, old_url: str, new_url: str) -> None:
    """
    Replace old URL with new URL inside file.

    :param filepath: File path.
    :param old_url: Old URL string.
    :param new_url: New URL string.
    :return: None.
    """

    filepath_obj = Path(filepath)  # Build Path object from filepath string for text operations.

    if not os.access(str(filepath_obj), os.W_OK):  # Verify whether the file is writable before attempting replacement.
        print(f"{BackgroundColors.YELLOW}[WARNING] Skipping read-only file: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL}")
        return

    try:  # Attempt to read file text safely before replacement.
        text = filepath_obj.read_text(encoding="utf-8", errors="ignore")  # Read current file content using safe tolerant decoding.
    except Exception as e:  # Handle file read failures gracefully.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to read file for URL replacement: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL} - {e}")  # Print replacement read failure warning.
        return  # Return early when file cannot be read.

    updated_text = text.replace(old_url, new_url)  # Replace all occurrences of old URL with new URL.

    if updated_text == text:  # Verify whether content changed after replacement attempt.
        verbose_output(f"{BackgroundColors.GREEN} No URL replacement needed in file: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL}")  # Print no-change replacement warning.
        return  # Return early when no replacement occurred.

    try:  # Attempt to persist modified file content.
        filepath_obj.write_text(updated_text, encoding="utf-8")  # Write updated content back to the file.
    except Exception as e:  # Handle file write failures gracefully.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to write file for URL replacement: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL} - {e}")  # Print replacement write failure warning.
        return  # Return early when replacement write operation fails.

    try:  # Attempt to re-read file content for replacement validation.
        persisted_text = filepath_obj.read_text(encoding="utf-8", errors="ignore")  # Re-read file content after write for validation.
    except Exception as e:  # Handle validation read failures safely.
        print(f"{BackgroundColors.YELLOW}[WARNING] Failed to validate URL replacement in file: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL} - {e}")  # Print replacement validation read failure warning.
        return  # Return early when validation read operation fails.

    if new_url in persisted_text and old_url not in persisted_text:  # Verify replacement persisted with new URL present and old URL removed.
        verbose_output(f"{BackgroundColors.GREEN}Updated URL replacements in file: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL}")  # Print successful replacement update message.
        return  # Return after successful replacement validation.

    print(f"{BackgroundColors.YELLOW}[WARNING] URL replacement validation failed in file: {BackgroundColors.CYAN}{filepath_obj}{Style.RESET_ALL}")  # Print replacement validation failure warning.


def replace_url_recursively(base_path: Path, old_url: str, new_url: str) -> None:
    """
    Replace URL occurrences recursively for all files inside a base directory.

    :param base_path: Root directory to traverse recursively.
    :param old_url: Original URL to replace.
    :param new_url: New URL to persist.
    :return: None.
    """

    if not base_path.exists():  # Verify whether Outputs base directory exists.
        verbose_output(f"{BackgroundColors.YELLOW}[WARNING] Outputs directory not found for recursive URL replacement: {BackgroundColors.CYAN}{base_path}{Style.RESET_ALL}")  # Log missing Outputs directory when verbose enabled.
        return  # Return early when Outputs directory is unavailable.

    for filepath in base_path.rglob("*"):  # Traverse all filesystem entries under Outputs recursively.
        if filepath.is_file() and filepath.suffix in {".txt", ".json", ".csv"}:  # Verify file is a supported text-based format (txt, json, csv).
            replace_url_in_file(str(filepath), old_url, new_url)  # Replace URL occurrences in current supported text file.


def renew_amazon_affiliate_url(current_url: str, share_button_img: Path, urls_file: Path) -> tuple:
    """
    Orchestrate complete Amazon affiliate URL renewal workflow.

    :param current_url: Original Amazon URL to replace.
    :param share_button_img: Path to ShareAffiliateURL-Amazon.png image.
    :param urls_file: Path to the urls.txt file.
    :return: Tuple containing True if renewal succeeded, otherwise False, and the new URL if successful or the original URL if failed.
    """

    verbose_output(f"{BackgroundColors.GREEN}Initiating {BackgroundColors.CYAN}Amazon affiliate URL Renewal{BackgroundColors.GREEN} for: {BackgroundColors.CYAN}{current_url}{Style.RESET_ALL}")  # Log renewal workflow start when verbose enabled.

    click_method = click_share_affiliate_url_button(share_button_img)  # Click share affiliate URL button using image or fallback coordinates.

    time.sleep(1)  # Wait for menu to appear after button click.

    copied_url = wait_for_valid_affiliate_url(current_url, 5)  # Wait for a valid renewed affiliate URL from clipboard.
    if not copied_url:  # Verify if clipboard retrieval succeeded.
        verbose_output(f"{BackgroundColors.RED}Failed to retrieve valid renewed URL from clipboard{Style.RESET_ALL}")  # Log clipboard retrieval failure when verbose enabled.
        return False, current_url  # Return failure and original URL when clipboard is empty.

    if not validate_amazon_affiliate_url(copied_url):  # Verify if copied URL matches strict and project affiliate validation.
        verbose_output(f"{BackgroundColors.RED}Invalid Amazon affiliate URL format: {copied_url}{Style.RESET_ALL}")  # Log invalid URL format when verbose enabled.
        return False, current_url  # Return failure and original URL when URL format is invalid.

    if normalize_affiliate_url(copied_url) == normalize_affiliate_url(current_url):  # Verify whether renewed URL differs from original URL.
        verbose_output(f"{BackgroundColors.RED}Renewed Amazon URL is identical to original URL: {copied_url}{Style.RESET_ALL}")  # Log unchanged URL failure when verbose enabled.
        return False, current_url  # Return failure and original URL when renewed URL matches the original URL.

    RENEWED_URL_MAP[current_url] = copied_url  # Store successful renewal mapping for fallback mapped-file replacements.
    print(f"{BackgroundColors.GREEN}Old URL: {BackgroundColors.CYAN}{current_url}{BackgroundColors.GREEN} -> New URL: {BackgroundColors.CYAN}{copied_url}{Style.RESET_ALL}")  # Print old and new URL mapping after successful renewal.

    success = update_urls_txt_with_new_amazon_url(current_url, copied_url, urls_file)  # Update urls.txt with new affiliate URL.
    if success:  # Verify if urls.txt was successfully updated.
        backup_urls_file = urls_file.with_name(urls_file.stem + "-backup" + urls_file.suffix)  # Create backup file path by adding -backup suffix before the extension.
        success = update_urls_txt_with_new_amazon_url(current_url, copied_url, backup_urls_file)  # Update urls-backup.txt with new affiliate URL.

        outputs_dir = resolve_outputs_directory()  # Resolve Outputs directory path from project root.
        replace_url_recursively(outputs_dir, current_url, copied_url)  # Replace renewed Amazon URL recursively inside Outputs files.
        verbose_output(f"{BackgroundColors.GREEN}Amazon URL successfully renewed from {BackgroundColors.CYAN}{current_url}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{copied_url}{Style.RESET_ALL}")  # Log successful renewal completion when verbose enabled.

        print_url_update(current_url, copied_url)  # Print colored OLD and NEW URL output to terminal for visibility.
        if ONLY_RENEW_AMAZON_AFFILIATE_URLS:  # Verify if running in renew-only mode.
            files_to_validate = [str(urls_file.resolve()), str(backup_urls_file.resolve())]  # Include both urls.txt and urls-backup.txt for validation when enabled.
        else:  # Verify if running in normal mode.
            files_to_validate = [str(urls_file.resolve())]  # Include only urls.txt for validation in default mode.
        if not validate_url_update(current_url, copied_url, files_to_validate):  # Verify new URL presence and old URL absence across selected files.
            print(f"{BackgroundColors.YELLOW}[WARNING] Affiliate URL validation failed for files: {BackgroundColors.CYAN}{files_to_validate}{Style.RESET_ALL}")  # Log validation failure and mention only the files actually validated.
            return False, current_url  # Return failure and original URL when validation does not pass to avoid continuing silently.

        return True, copied_url  # Return success and new URL when full workflow completes successfully.

    return False, current_url  # Return failure and original URL when initial update step fails.


def build_report(ext_methods: Dict[str, List[int]], download_methods: Dict[str, List[int]], completion_methods: Dict[str, List[int]], close_methods: Dict[str, List[int]]) -> str:
    """
    Builds grouped execution report text.

    :param ext_methods: Grouped extension click methods.
    :param download_methods: Grouped download click methods.
    :param completion_methods: Grouped completion detection methods.
    :param close_methods: Grouped close tab methods.
    :return: Consolidated report string.
    """

    lines: List[str] = []  # Initialize report line buffer.

    for method, tabs in ext_methods.items():  # Iterate extension method groups.
        lines.append(f"{BackgroundColors.GREEN}Extension Click - {BackgroundColors.CYAN}{method}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{join_array(tabs)}{Style.RESET_ALL}")  # Append extension report line.

    lines.append("")  # Append visual separator line.

    for method, tabs in download_methods.items():  # Iterate download method groups.
        lines.append(f"{BackgroundColors.GREEN}Download Click - {BackgroundColors.CYAN}{method}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{join_array(tabs)}{Style.RESET_ALL}")  # Append download report line.

    lines.append("")  # Append visual separator line.

    for method, tabs in completion_methods.items():  # Iterate completion method groups.
        lines.append(f"{BackgroundColors.GREEN}Completion Detection - {BackgroundColors.CYAN}{method}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{join_array(tabs)}{Style.RESET_ALL}")  # Append completion report line.

    lines.append("")  # Append visual separator line.

    for method, tabs in close_methods.items():  # Iterate close tab method groups.
        lines.append(f"{BackgroundColors.GREEN}Close Extension Tab - {BackgroundColors.CYAN}{method}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{join_array(tabs)}{Style.RESET_ALL}")  # Append close tab report line.

    return "\n".join(lines).strip()  # Return report text.


def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape sequences from text so GUI messageboxes show plain text.

    :param text: Input string possibly containing ANSI codes.
    :return: Cleaned string without ANSI sequences.
    """

    if not isinstance(text, str):  # Verify input is a string before processing.
        return text  # Return original input when it's not a string.

    return re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text)  # This regex matches most ANSI escape sequences (CSI and related codes).


def maybe_show_messagebox(title: str, message: str) -> None:
    """
    Displays messagebox when tkinter is available.

    :param title: Messagebox title string.
    :param message: Messagebox body string.
    :return: None
    """

    try:  # Attempt tkinter messagebox display.
        root = tk.Tk()  # Create tkinter root instance.
        root.withdraw()  # Hide root window.

        clean_title = strip_ansi(title)  # Strip ANSI codes from title for clean display.
        clean_message = strip_ansi(message)  # Strip ANSI codes from message for clean display.

        messagebox.showinfo(clean_title, clean_message)  # Show informational messagebox without ANSI codes.
        root.destroy()  # Destroy root window.
    except Exception:  # Handle tkinter availability and GUI exceptions.
        pass  # Skip messagebox display on exception.


def run(tab_count: int | None, urls_file: Path, assets_dir: Path, headerless: bool = True, renew_amazon_affiliate: bool = False, only_renew_amazon_urls: bool = False, process_only_unlinked_urls: bool = False) -> int:
    """
    Runs the affiliate pages automation workflow.

    :param tab_count: Number of tabs and URLs to process.
    :param urls_file: Path to URLs input file.
    :param assets_dir: Path to image assets directory.
    :param headerless: Whether to suppress GUI messagebox when True.
    :param renew_amazon_affiliate: Override global renewal flag when True.
    :param only_renew_amazon_urls: Override global only-renew mode when True.
    :param process_only_unlinked_urls: Whether to filter URLs against existing report links and process only unlinked URLs when True.
    :return: Exit code where 0 means success and 1 means failure.
    """

    raw_lines = load_urls_to_process(str(urls_file))  # Read raw trimmed lines from input file using centralized helper
    
    if raw_lines is None:  # Verify whether loading lines failed due to file issues.
        print(f"{BackgroundColors.RED}Error: Failed to read URLs from file: {BackgroundColors.CYAN}{urls_file}{BackgroundColors.RED}. Please ensure the file exists and is readable in that specified paths. Be careful with the parent directory of the file as well.{Style.RESET_ALL}")  # Print file read error with details and suggestions.
        return 1  # Return error exit code when lines cannot be loaded.
    
    preprocessed_urls = preprocess_urls(raw_lines)  # Preprocess lines (strip, remove dash prefixes, sort)
    write_urls_to_file(preprocessed_urls, str(urls_file), True)  # Write preprocessed lines back to the file for consistency and potential manual review.
    urls = [url.split()[0] for url in preprocessed_urls]  # Keep only the URL token (first token) per previous behavior

    downloads_dirs = ACTIVE_DOWNLOADS_DIRS if ACTIVE_DOWNLOADS_DIRS else prepare_active_downloads_directory()  # Use cached downloads directories or resolve if cache is empty.

    if tab_count is None or tab_count <= 0:  # Verify tab count validity.
        tab_count = len(urls)  # Use full URL list length when tab count is not positive.

    fallback_outputs_url_map: Dict[str, List[str]] = {}  # Initialize Outputs fallback URL mapping dictionary.
    fallback_outputs_mode = False  # Initialize Outputs fallback mode status flag.

    if only_renew_amazon_urls:  # Verify whether only-renew mode is enabled before processing URLs.
        urls, fallback_outputs_mode, fallback_outputs_url_map, tab_count = setup_only_renew_amazon_urls(
            tab_count,  # Provide current tab count for validation and normalization.
            urls,  # Provide initial URL list for processing.
            urls_file,  # Provide primary URLs file path for validation and extraction.
            AFFILIATE_URL_PATTERN  # Provide Amazon affiliate URL pattern for extraction filtering.
        )  # Execute consolidated URL preparation pipeline including fallback Outputs scan when required.

    if tab_count <= 0:  # Verify there are URLs to process.
        print(f"{BackgroundColors.RED}Error: The file {BackgroundColors.CYAN}{urls_file}{BackgroundColors.RED} is empty or contains no valid URLs.{Style.RESET_ALL}")  # Print empty URLs error.
        return 1  # Return error exit code.

    urls = urls[:tab_count]  # Limit URL list to requested tab count.

    extension_img, download_img, enable_permission_img, confirmation_img, failed_file_download_img, close_download_tab_img, mercado_livre_img, share_button_img, save_button_img = setup_image_paths(assets_dir)  # Initialize all required UI image asset paths from assets directory

    print(f"{BackgroundColors.GREEN}Starting automation immediately and activating Chrome window.{Style.RESET_ALL}")  # Print immediate start message.

    if not activate_chrome_window():  # Verify Chrome activation before sending hotkeys.
        return 1  # Return failure exit code when activation fails.

    dedicated_created = False  # Track dedicated automation window creation state.
    
    if not prepare_dedicated_chrome_window_for_automation():  # Verify dedicated Chrome window preparation before opening automation tabs.
        return 1  # Return failure exit code when dedicated automation window is unavailable.
    
    dedicated_created = True  # Mark that a dedicated window was prepared for later cleanup.

    try:  # Begin main processing block so dedicated window can be closed in finally.
        pyautogui.hotkey("ctrl", "t")  # Open a constant empty tab in the dedicated window for settings navigation.
        time.sleep(0.2)  # Wait after opening the constant empty tab.

        chrome_download_settings_ready = True  # Initialize downloads settings readiness as true for only-renew mode.

        if not only_renew_amazon_urls:  # Verify whether normal mode requires downloads settings validation.
            chrome_download_settings_ready = verify_and_correct_chrome_download_settings(assets_dir, open_in_new_tab=False)  # Verify Chrome downloads settings in the current tab before processing product URLs.

            if not chrome_download_settings_ready:  # Verify whether Chrome downloads settings could not be verified or corrected automatically.
                print(f"{BackgroundColors.YELLOW}[WARNING] Chrome downloads settings could not be verified or corrected automatically. Continuing execution.{Style.RESET_ALL}")  # Log non-blocking downloads settings verification warning.

        ext_methods, download_methods, completion_methods, close_methods = setup_method_maps()  # Initialize grouped automation method maps for extension, download, completion, and close actions.

        processed_count = 0  # Initialize processed tab counter.
        start_tick = time.time()  # Capture workflow start timestamp.
        url_to_download: Dict[str, str] = {}  # Initialize URL to downloaded filename mapping dictionary.
        
        if process_only_unlinked_urls:  # Verify whether only unlinked URLs must be processed.
            existing_report_urls = set()  # Load existing linked urls from report file for filtering.
            urls = [url for url in urls if url not in existing_report_urls]  # Filter already linked urls from processing list.
        
        processed_count, url_to_download, process_success = process_urls_with_download_tracking(urls, urls_file, tab_count, downloads_dirs, extension_img, download_img, enable_permission_img, confirmation_img, failed_file_download_img, close_download_tab_img, mercado_livre_img, share_button_img, save_button_img, ext_methods, download_methods, completion_methods, close_methods, chrome_download_settings_ready, renew_amazon_affiliate, only_renew_amazon_urls)  # Process URLs with download tracking and retrieve mapping details.
        
        verbose_output(f"{BackgroundColors.GREEN}URL to Downloaded Filename Mapping:\n{BackgroundColors.CYAN}" + "\n".join(f'    "{k}": "{v}"' for k, v in url_to_download.items()) + f"{Style.RESET_ALL}")  # Print URL to downloaded filename mapping details when verbose enabled.

        if not process_success:  # Verify if URL processing completed without activation failure.
            return 1  # Return failure exit code when URL processing fails.

        if processed_count > 0:  # Verify that at least one URL was processed before reporting execution time and showing messagebox.
            elapsed_sec = round(time.time() - start_tick)  # Compute elapsed seconds.
            formatted = format_execution_time(elapsed_sec)  # Format elapsed time string.
            report = build_report(ext_methods, download_methods, completion_methods, close_methods)  # Build consolidated report text.
            final_report = f"{BackgroundColors.GREEN}Execution Time: {BackgroundColors.CYAN}{formatted}{BackgroundColors.GREEN}\n\n{report}{Style.RESET_ALL}"  # Compose final report output.

            if only_renew_amazon_urls and fallback_outputs_mode:  # Verify whether Outputs fallback mapped replacements must execute after renewal processing.
                for old_url, mapped_filepaths in fallback_outputs_url_map.items():  # Iterate Outputs fallback URL map for mapped-file replacements.
                    renewed_url = RENEWED_URL_MAP.get(old_url, "")  # Resolve renewed URL from successful renewal mapping store.

                    if renewed_url == "":  # Verify whether renewal mapping exists for current fallback URL.
                        continue  # Skip processing when no renewed URL mapping is available.

                    for mapped_filepath in mapped_filepaths:  # Iterate mapped filepaths associated with current fallback URL.
                        replace_url_in_file(str(mapped_filepath), old_url, renewed_url)  # Replace old URL with renewed URL in mapped file.

            if not only_renew_amazon_urls:  # Verify whether normal mode requires urls-to-download mapping updates.
                update_urls_file(urls_file, url_to_download)  # Rewrite URLs file with URL to downloaded filename mapping.

            print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Automation Finished{Style.RESET_ALL}\n")  # Print automation completion message.

            if not headerless:  # Verify if headerless flag is disabled before showing GUI messagebox.
                maybe_show_messagebox("Automation Finished", final_report)  # Display optional messagebox report when allowed.

        return 0  # Return success exit code.
    finally:  # Ensure dedicated automation window cleanup regardless of success or failure.
        if dedicated_created:  # Verify whether a dedicated automation window was created earlier.
            close_dedicated_automation_window()  # Attempt to close the dedicated automation window to restore original state.


def verify_filepath_exists(filepath):
    """
    Verify if a file or folder exists at the specified path.

    :param filepath: Path to the file or folder
    :return: True if the file or folder exists, False otherwise
    """

    verbose_output(
        f"{BackgroundColors.GREEN}Verifying if the file or folder exists at the path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}"
    )  # Output the verbose message

    return os.path.exists(filepath)  # Return True if the file or folder exists, False otherwise


def to_seconds(obj):
    """
    Converts various time-like objects to seconds.
    
    :param obj: The object to convert (can be int, float, timedelta, datetime, etc.)
    :return: The equivalent time in seconds as a float, or None if conversion fails
    """
    
    if obj is None:  # None can't be converted
        return None  # Signal failure to convert
    if isinstance(obj, (int, float)):  # Already numeric (seconds or timestamp)
        return float(obj)  # Return as float seconds
    if hasattr(obj, "total_seconds"):  # Timedelta-like objects
        try:  # Attempt to call total_seconds()
            return float(obj.total_seconds())  # Use the total_seconds() method
        except Exception:
            pass  # Fallthrough on error
    if hasattr(obj, "timestamp"):  # Datetime-like objects
        try:  # Attempt to call timestamp()
            return float(obj.timestamp())  # Use timestamp() to get seconds since epoch
        except Exception:
            pass  # Fallthrough on error
    return None  # Couldn't convert


def calculate_execution_time(start_time, finish_time=None):
    """
    Calculates the execution time and returns a human-readable string.

    Accepts either:
    - Two datetimes/timedeltas: `calculate_execution_time(start, finish)`
    - A single timedelta or numeric seconds: `calculate_execution_time(delta)`
    - Two numeric timestamps (seconds): `calculate_execution_time(start_s, finish_s)`

    Returns a string like "1h 2m 3s".
    """

    if finish_time is None:  # Single-argument mode: start_time already represents duration or seconds
        total_seconds = to_seconds(start_time)  # Try to convert provided value to seconds
        if total_seconds is None:  # Conversion failed
            try:  # Attempt numeric coercion
                total_seconds = float(start_time)  # Attempt numeric coercion
            except Exception:
                total_seconds = 0.0  # Fallback to zero
    else:  # Two-argument mode: Compute difference finish_time - start_time
        st = to_seconds(start_time)  # Convert start to seconds if possible
        ft = to_seconds(finish_time)  # Convert finish to seconds if possible
        if st is not None and ft is not None:  # Both converted successfully
            total_seconds = ft - st  # Direct numeric subtraction
        else:  # Fallback to other methods
            try:  # Attempt to subtract (works for datetimes/timedeltas)
                delta = finish_time - start_time  # Try subtracting (works for datetimes/timedeltas)
                total_seconds = float(delta.total_seconds())  # Get seconds from the resulting timedelta
            except Exception:  # Subtraction failed
                try:  # Final attempt: Numeric coercion
                    total_seconds = float(finish_time) - float(start_time)  # Final numeric coercion attempt
                except Exception:  # Numeric coercion failed
                    total_seconds = 0.0  # Fallback to zero on failure

    if total_seconds is None:  # Ensure a numeric value
        total_seconds = 0.0  # Default to zero
    if total_seconds < 0:  # Normalize negative durations
        total_seconds = abs(total_seconds)  # Use absolute value

    days = int(total_seconds // 86400)  # Compute full days
    hours = int((total_seconds % 86400) // 3600)  # Compute remaining hours
    minutes = int((total_seconds % 3600) // 60)  # Compute remaining minutes
    seconds = int(total_seconds % 60)  # Compute remaining seconds

    if days > 0:  # Include days when present
        return f"{days}d {hours}h {minutes}m {seconds}s"  # Return formatted days+hours+minutes+seconds
    if hours > 0:  # Include hours when present
        return f"{hours}h {minutes}m {seconds}s"  # Return formatted hours+minutes+seconds
    if minutes > 0:  # Include minutes when present
        return f"{minutes}m {seconds}s"  # Return formatted minutes+seconds
    return f"{seconds}s"  # Fallback: only seconds


def play_sound():
    """
    Plays a sound when the program finishes and skips if the operating system is Windows.

    :param: None
    :return: None
    """

    current_os = platform.system()  # Get the current operating system
    if current_os == "Windows":  # If the current operating system is Windows
        return  # Do nothing

    if verify_filepath_exists(SOUND_FILE):  # If the sound file exists
        if current_os in SOUND_COMMANDS:  # If the platform.system() is in the SOUND_COMMANDS dictionary
            os.system(f"{SOUND_COMMANDS[current_os]} {SOUND_FILE}")  # Play the sound
        else:  # If the platform.system() is not in the SOUND_COMMANDS dictionary
            print(
                f"{BackgroundColors.RED}The {BackgroundColors.CYAN}{current_os}{BackgroundColors.RED} is not in the {BackgroundColors.CYAN}SOUND_COMMANDS dictionary{BackgroundColors.RED}. Please add it!{Style.RESET_ALL}"
            )
    else:  # If the sound file does not exist
        print(
            f"{BackgroundColors.RED}Sound file {BackgroundColors.CYAN}{SOUND_FILE}{BackgroundColors.RED} not found. Make sure the file exists.{Style.RESET_ALL}"
        )


def main():
    """
    Main function.

    :param: None
    :return: None
    """

    print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Affiliate Pages Downloader Automation{BackgroundColors.GREEN} program!{Style.RESET_ALL}", end="\n")  # Print welcome banner.
    start_time = datetime.datetime.now()  # Capture program start timestamp.

    repo_root = Path(PROJECT_ROOT)  # Convert project root string into Path object.

    args = parse_arguments(repo_root)  # Parse command-line arguments
    
    if args.verbose:  # Verify if verbose mode is enabled
        global VERBOSE  # Set the global VERBOSE variable to True when the --verbose flag is provided
        VERBOSE = True  # Enable verbose output

    global ONLY_RENEW_AMAZON_AFFILIATE_URLS  # Reference global only-renew mode constant for CLI override.
    argv_only_renew = next((arg.split("=", 1)[1] if "=" in arg else "true" for arg in sys.argv[1:] if arg.lower().startswith("--only-renew-amazon-urls")), "")  # Resolve only-renew argument raw value from sys.argv.
    if str(argv_only_renew).lower() in ("true", "1"):  # Verify whether sys.argv includes truthy only-renew value.
        ONLY_RENEW_AMAZON_AFFILIATE_URLS = True  # Enable global only-renew mode when sys.argv override is truthy.

    if args.only_renew_amazon_urls is not None and str(args.only_renew_amazon_urls).lower() in ("true", "1"):  # Verify whether argparse includes truthy only-renew value.
        ONLY_RENEW_AMAZON_AFFILIATE_URLS = True  # Enable global only-renew mode when argparse value is truthy.

    global USE_MAIN_MONITOR  # Reference global monitor selection flag for CLI override.
    USE_MAIN_MONITOR = args.main_monitor  # Set monitor selection based on parsed CLI argument.

    update_chrome_profile(CHROME_PROFILE_DISPLAY_NAME)  # Resolve and set CHROME_PROFILE_DIRECTORY using configured display name with Default fallback.

    exit_code = run(args.tab_count, args.urls_file, args.assets_dir, args.headerless, args.renew_amazon_affiliate_url, ONLY_RENEW_AMAZON_AFFILIATE_URLS, args.process_only_unlinked_urls)  # Execute automation flow with headerless option, renewal override, only-renew mode, and unlinked URLs processing.

    finish_time = datetime.datetime.now()  # Capture program finish timestamp.
    print(f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}")  # Print execution timing summary.
    print(f"\n{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}")  # Print program completion message.
    (atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None)  # Register completion sound callback when enabled.


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
