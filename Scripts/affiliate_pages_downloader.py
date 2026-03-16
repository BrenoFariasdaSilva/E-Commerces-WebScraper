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
import datetime  # Capture execution timestamps.
import os  # Execute operating-system commands.
import platform  # Identify active operating system.
import pyautogui  # Automate keyboard and mouse interactions.
import re  # Regular expressions for stripping ANSI escape sequences.
import shutil  # Move files between directories.
import sys  # Access process-level runtime controls.
import time  # Manage sleep and elapsed time operations.
import tkinter as tk  # Import tkinter module.
from colorama import Style  # Reset ANSI style output.
from pathlib import Path  # Build and resolve filesystem paths.
from tkinter import messagebox  # Import tkinter messagebox utility.
from tqdm import tqdm  # Import tqdm progress bar iterator.
from typing import Any, Dict, List, Tuple  # Provide typing annotations for containers and dynamic objects.


PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)  # Project root directory
if PROJECT_ROOT not in sys.path:  # Ensure project root is in sys.path
    sys.path.insert(0, PROJECT_ROOT)  # Insert at the beginning
from Logger import Logger  # For logging output to both terminal and file


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

ACTIVE_DOWNLOADS_DIRS = []  # Store the resolved active downloads directories path for reuse.

DOWNLOADS_DIR = {
    "windows": [os.path.join(os.path.expanduser("~"), "Downloads"), r"D:\Sem Backup\Download"],  # Define Windows downloads directory candidates.
    "linux": [os.path.join(os.path.expanduser("~"), "Downloads")],  # Define Linux downloads directory candidates.
    "darwin": [os.path.join(os.path.expanduser("~"), "Downloads")],  # Define macOS downloads directory candidates.
}  # Define monitored downloads directory candidates by operating system.

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

TARGET_CHROME_TITLE = ""  # Store selected Chrome window title for reuse.
ACTIVE_CHROME_BOUNDS = {"left": 0, "top": 0, "width": 0, "height": 0}  # Store active Chrome window bounds for coordinate calculations.

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


def activate_chrome_window() -> bool:
    """
    Activates a Chrome window to receive automation keystrokes.

    :return: True if a Chrome window is active, otherwise False.
    """

    global TARGET_CHROME_TITLE  # Reference global selected window title.

    chrome_windows = get_chrome_windows()  # Retrieve visible non-minimized Chrome windows.

    if len(chrome_windows) == 0:  # Verify at least one Chrome window exists.
        print(f"{BackgroundColors.RED}No Chrome windows were detected. Automation cannot continue.{Style.RESET_ALL}")  # Print Chrome not found error.
        return False  # Return failure status when no Chrome window is available.

    target_window = select_chrome_window(chrome_windows)  # Resolve deterministic Chrome target window.

    if target_window is None:  # Verify if a deterministic target window was selected.
        print(f"{BackgroundColors.RED}Failed to select a Chrome window. Automation cannot continue.{Style.RESET_ALL}")  # Print selection failure error.
        return False  # Return failure status when no target window can be selected.

    TARGET_CHROME_TITLE = str(getattr(target_window, "title", ""))  # Persist selected Chrome window title for next cycle.

    if not activate_window_with_fallback(target_window):  # Verify if Chrome activation succeeded.
        print(f"{BackgroundColors.RED}Failed to activate Chrome window. Keep Chrome focused manually and retry.{Style.RESET_ALL}")  # Print activation failure message.
        return False  # Return failure status after activation attempts.

    ensure_result = ensure_chrome_on_primary_monitor(target_window)  # Ensure active Chrome window is usable on the primary monitor.

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
        center_x = left + max(1, width // 2)  # Compute safe window center X coordinate.
        center_y = top + max(1, height // 2)  # Compute safe window center Y coordinate.
        pyautogui.click(center_x, center_y)  # Focus window by clicking inside it.
        time.sleep(0.2)  # Wait after focus click.
        target_window.activate()  # Retry window activation after focus click.
        time.sleep(0.2)  # Wait after activation retry.
        target_window.maximize()  # Retry maximize operation for consistent coordinates.
        time.sleep(0.8)  # Wait after maximize retry.

        ACTIVE_CHROME_BOUNDS = {"left": left, "top": top, "width": width, "height": height}  # Cache active window bounds for coordinate calculations.

        return True  # Return success status after secondary activation strategy.
    except Exception:  # Handle secondary activation strategy failure.
        return False  # Return failure status when all activation strategies fail.


def get_primary_monitor_bounds() -> Tuple[int, int, int, int]:
    """
    Retrieves primary monitor bounds from screen size.

    :param: None.
    :return: Tuple of primary monitor bounds as left, top, right, bottom.
    """

    screen_size = pyautogui.size()  # Retrieve primary monitor size from pyautogui backend.
    return 0, 0, int(screen_size.width), int(screen_size.height)  # Return primary monitor bounds tuple.


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
        primary_left, primary_top, primary_right, primary_bottom = get_primary_monitor_bounds()  # Retrieve primary monitor bounds.

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


def read_urls(urls_file: Path) -> List[str]:
    """
    Reads URLs from the specified file.

    :param urls_file: Path to the URLs input file.
    :return: List of cleaned URLs.
    """

    urls: List[str] = []  # Initialize URL list.

    if not urls_file.exists():  # Verify URLs file existence.
        return urls  # Return empty list when file does not exist.

    for raw in urls_file.read_text(encoding="utf-8", errors="ignore").splitlines():  # Iterate over file lines.
        line = raw.strip()  # Remove leading and trailing whitespace.

        if not line:  # Verify line has content.
            continue  # Skip empty lines.

        clean = line.split()[0].strip()  # Extract first token from the line.

        if clean:  # Verify extracted token has content.
            urls.append(clean)  # Append cleaned URL to list.

    return urls  # Return collected URLs.


def read_urls_file(urls_file: Path) -> List[str]:
    """
    Reads URL entries from the URLs file.

    :param urls_file: Path to the URLs input file.
    :return: List of cleaned URLs.
    """

    return read_urls(urls_file)  # Return URL entries parsed from the URLs file.


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
    return any(lower.endswith(suf) for suf in compressed_suffixes)  # Return True when any suffix matches.


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

    for downloads_dir in downloads_dirs:  # Iterate monitored downloads directory paths.
        resolved_dir = str(Path(downloads_dir).resolve())  # Resolve and normalize current monitored directory path.
        before_snapshot = before_snapshots.get(resolved_dir, {})  # Retrieve pre-processing snapshot for current directory.
        after_snapshot = after_snapshots.get(resolved_dir, {})  # Retrieve post-processing snapshot for current directory.
        new_filenames = [filename for filename in after_snapshot if filename not in before_snapshot]  # Build list of new filenames for current monitored directory.

        if len(new_filenames) == 0:  # Verify whether current monitored directory has new files.
            continue  # Continue iteration when current directory has no new files.

        selected_filename = max(new_filenames, key=lambda filename: after_snapshot.get(filename, 0.0))  # Select most recently modified new filename for current monitored directory.
        detected_entries.append((resolved_dir, selected_filename, after_snapshot.get(selected_filename, 0.0)))  # Append detected directory, filename, and modified timestamp entry.

    if len(detected_entries) == 0:  # Verify whether any monitored directory received new files.
        print(f"{BackgroundColors.YELLOW}[WARNING] No new download detected for URL: {url}{Style.RESET_ALL}")  # Log missing download warning for current URL.
        return "", ""  # Return empty detection tuple when no new download is found.

    if len(detected_entries) > 1:  # Verify whether multiple directories or files were detected in the same cycle.
        print(f"{BackgroundColors.YELLOW}[WARNING] Multiple downloads detected. Using most recent file.{Style.RESET_ALL}")  # Log multiple downloads warning.

    selected_dir, selected_filename, _ = max(detected_entries, key=lambda item: item[2])  # Select most recently modified file across all monitored directories.
    return selected_dir, selected_filename  # Return detected directory and filename.


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


def move_downloaded_archives(downloads_dirs: List[str], destination_dir: Path, url_to_download: Dict[str, str]) -> None:
    """
    Moves downloaded archives from downloads directory to URLs directory.

    :param downloads_dirs: Paths to monitored downloads directories.
    :param destination_dir: Path to the target directory where URLs file is located.
    :param url_to_download: Dictionary mapping URL to downloaded filename.
    :return: None.
    """

    unique_filenames = sorted({filename for filename in url_to_download.values() if filename != ""})  # Build sorted unique list of detected downloaded filenames.
    normalized_downloads_dirs = [str(Path(downloads_dir).resolve()) for downloads_dir in downloads_dirs]  # Resolve and normalize monitored downloads directory paths.

    for filename in unique_filenames:  # Iterate over detected downloaded filenames.
        source_path = None  # Initialize source archive file path placeholder.
        destination_path = destination_dir / filename  # Build destination archive file path in URLs directory.

        for downloads_dir in normalized_downloads_dirs:  # Iterate monitored downloads directories while searching for current archive.
            candidate_path = Path(downloads_dir) / filename  # Build candidate source archive path for current monitored downloads directory.

            if candidate_path.exists():  # Verify whether current candidate source archive path exists.
                source_path = candidate_path  # Persist existing source archive path.
                break  # Stop iteration after locating the first existing source archive path.

        if source_path is None:  # Verify whether a source archive path was located.
            print(f"{BackgroundColors.YELLOW}[WARNING] Downloaded file not found for move: {filename}{Style.RESET_ALL}")  # Log missing source archive warning.
            continue  # Continue with next detected archive.

        if destination_path.exists():  # Verify if destination archive already exists.
            print(f"{BackgroundColors.YELLOW}[WARNING] Destination file already exists. Skipping move: {destination_path}{Style.RESET_ALL}")  # Log existing destination archive warning.
            continue  # Continue with next detected archive.

        try:  # Attempt to move archive into destination directory.
            shutil.move(str(source_path), str(destination_path))  # Move detected downloaded archive to URLs directory.
        except Exception:  # Handle archive move failures.
            print(f"{BackgroundColors.YELLOW}[WARNING] Failed to move downloaded file: {source_path}{Style.RESET_ALL}")  # Log archive move failure warning.


def process_urls_with_download_tracking(urls: List[str], tab_count: int, downloads_dirs: List[str], extension_img: Path, download_img: Path, confirmation_img: Path, close_download_tab_img: Path, mercado_livre_img: Path, ext_methods: Dict[str, List[int]], download_methods: Dict[str, List[int]], completion_methods: Dict[str, List[int]], close_methods: Dict[str, List[int]]) -> Tuple[int, Dict[str, str], bool]:
    """
    Processes URLs while tracking downloaded files by directory snapshots.

    :param urls: URL list to process.
    :param tab_count: Number of URLs to process.
    :param downloads_dirs: Paths to monitored downloads directories.
    :param extension_img: Path to extension action image.
    :param download_img: Path to download button image.
    :param confirmation_img: Path to download confirmation image.
    :param close_download_tab_img: Path to close extension tab image.
    :param mercado_livre_img: Path to MercadoLivre go-to-product image.
    :param ext_methods: Grouped extension click methods dictionary.
    :param download_methods: Grouped download click methods dictionary.
    :param completion_methods: Grouped completion detection methods dictionary.
    :param close_methods: Grouped close extension tab methods dictionary.
    :return: Processed count, URL mapping dictionary, and success status.
    """

    url_to_download: Dict[str, str] = {}  # Initialize URL to downloaded filename mapping dictionary.
    processed_count = 0  # Initialize processed URL counter.
    downloads_dirs[:] = [str(Path(downloads_dir).resolve()) for downloads_dir in downloads_dirs]  # Resolve and normalize monitored downloads directory paths.

    if tab_count > 0:  # Verify if there are URLs to process.
        if not activate_chrome_window():  # Verify if Chrome activation succeeds before opening separator tab.
            return processed_count, url_to_download, False  # Return failure state when Chrome activation fails.

        pyautogui.hotkey("ctrl", "t")  # Open blank separator tab.
        time.sleep(0.2)  # Wait after opening separator tab.

    for index, url in enumerate(tqdm(urls, total=len(urls), desc=f"{BackgroundColors.GREEN}Processing URLs{Style.RESET_ALL}"), start=1):  # Initialize tqdm progress bar for URL processing while preserving enumerate indexing
        pre_download_snapshots = snapshot_download_directories(downloads_dirs)  # Capture downloads directory snapshots before URL processing.

        if not activate_chrome_window():  # Verify if Chrome activation succeeds before URL navigation.
            return processed_count, url_to_download, False  # Return failure state when Chrome activation fails.

        pyautogui.hotkey("ctrl", "t")  # Open new browser tab.
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
        time.sleep(7)  # Wait for page loading.

        current_tab = index  # Store current tab index.

        click_go_to_product_button(mercado_livre_img)  # Execute MercadoLivre button action when available.

        extension_method = click_image_or_coords(extension_img, EXTENSION_X_REF, EXTENSION_Y_REF)  # Execute extension click action with scaled fallback coordinates.
        download_method = click_download_button(download_img)  # Execute download click action.
        confirmation_method = wait_for_download_confirmation(confirmation_img)  # Execute completion polling action.
        close_method = close_extension_download_tab(close_download_tab_img)  # Execute close extension tab action.

        post_download_snapshots = snapshot_download_directories(downloads_dirs)  # Capture downloads directory snapshots after download completion.

        if len(downloads_dirs) > 1:  # Verify whether monitored downloads directories are unresolved.
            resolved_download_dir = resolve_first_download_directory(downloads_dirs, pre_download_snapshots, post_download_snapshots)  # Resolve monitored downloads directory using first detected file.

            if resolved_download_dir is not None:  # Verify whether monitored downloads directory resolution succeeded.
                update_active_download_directory(resolved_download_dir)  # Persist resolved monitored downloads directory in global cache.
                downloads_dirs[:] = ACTIVE_DOWNLOADS_DIRS  # Update local monitored downloads directories list with resolved cache.

        detected_download_dir, detected_filename = detect_new_download_from_directories(pre_download_snapshots, post_download_snapshots, downloads_dirs, url)  # Detect downloaded filename and source directory associated with current URL.

        if detected_download_dir != "" and len(downloads_dirs) > 1:  # Verify whether detected directory exists while local list remains unresolved.
            update_active_download_directory(detected_download_dir)  # Persist detected monitored downloads directory in global cache.
            downloads_dirs[:] = ACTIVE_DOWNLOADS_DIRS  # Update local monitored downloads directories list with detected cache.

        associate_url_with_download(url_to_download, url, detected_filename)  # Persist URL to downloaded filename mapping when detection succeeds.

        add_method(ext_methods, extension_method, current_tab)  # Store extension method for report.
        add_method(download_methods, download_method, current_tab)  # Store download method for report.
        add_method(completion_methods, confirmation_method, current_tab)  # Store completion method for report.
        add_method(close_methods, close_method, current_tab)  # Store close method for report.

        close_current_tab()  # Close current product tab.

        processed_count += 1  # Increment processed counter.

    return processed_count, url_to_download, True  # Return processed counter, URL mapping, and success status.


def locate_image(image_path: Path) -> Any:
    """
    Locates an image on screen.

    :param image_path: Path to the image file.
    :return: Box location when found, otherwise None.
    """

    if not image_path.exists():  # Verify image file existence.
        return None  # Return None when image file does not exist.

    try:  # Attempt image location on screen.
        return pyautogui.locateOnScreen(str(image_path))  # Return located box coordinates.
    except Exception:  # Handle image search exception.
        return None  # Return None when image search fails.


def get_screen_dimensions() -> Tuple[int, int]:
    """
    Retrieves current screen dimensions.

    :param: None.
    :return: Tuple of screen width and height in pixels.
    """

    screen_size = pyautogui.size()  # Retrieve primary monitor size from pyautogui backend.
    return int(screen_size.width), int(screen_size.height)  # Return screen dimensions as tuple.


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


def click_download_button(download_img: Path) -> str:
    """
    Clicks the download button with retry fallback and scaled coordinates.

    :param download_img: Path to the download button image.
    :return: Method name used for the click.
    """

    start = time.time()  # Store start timestamp for retry window.

    while time.time() - start < 3.0:  # Repeat until timeout window expires.
        box = locate_image(download_img)  # Locate download image on screen.

        if box is not None:  # Verify image was found.
            pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
            return "ImageSearch"  # Return image search method label.

        time.sleep(0.2)  # Wait before retrying image search.

    scaled_x, scaled_y = get_scaled_fallback_coords(DOWNLOAD_BUTTON_X_REF, DOWNLOAD_BUTTON_Y_REF)  # Compute scaled download button fallback coordinates.
    pyautogui.click(scaled_x, scaled_y)  # Click scaled download button coordinates.
    return "Coordinates"  # Return coordinates method label.


def wait_for_download_confirmation(confirmation_img: Path) -> str:
    """
    Waits for download confirmation image.

    :param confirmation_img: Path to the confirmation image.
    :return: Detection status string.
    """

    max_verifications = 60  # Set maximum number of verification iterations.

    for _ in range(max_verifications):  # Iterate polling attempts.
        if locate_image(confirmation_img) is not None:  # Verify confirmation image detection.
            return "Image Detected"  # Return image detected status.

        time.sleep(5)  # Wait before the next polling attempt.

    return "Timeout"  # Return timeout status after all iterations.


def close_extension_download_tab(close_download_tab_img: Path) -> str:
    """
    Closes extension download tab using image or scaled fallback coordinates.

    :param close_download_tab_img: Path to close tab image.
    :return: Method name used for the click.
    """

    box = locate_image(close_download_tab_img)  # Locate close tab image on screen.

    if box is not None:  # Verify image was found.
        pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
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
        pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
        time.sleep(5)  # Wait for page transition.
        return "MercadoLivre Go To Product"  # Return action performed status.

    return "Not Found / Skipped"  # Return skipped status.


def close_current_tab() -> None:
    """
    Closes the current browser tab.

    :return: None
    """

    pyautogui.hotkey("ctrl", "w")  # Trigger close-tab hotkey.
    time.sleep(1)  # Wait after closing the tab.


def add_method(methods: Dict[str, List[int]], method: str, tab_index: int) -> None:
    """
    Adds a method usage entry to report dictionary.

    :param methods: Dictionary mapping methods to tab indices.
    :param method: Method label to append.
    :param tab_index: Tab index associated with method usage.
    :return: None
    """

    methods.setdefault(method, []).append(tab_index)  # Append tab index to grouped method list.


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


def run(tab_count: int | None, urls_file: Path, assets_dir: Path, headerless: bool = True) -> int:
    """
    Runs the affiliate pages automation workflow.

    :param tab_count: Number of tabs and URLs to process.
    :param urls_file: Path to URLs input file.
    :param assets_dir: Path to image assets directory.
    :param headerless: Whether to suppress GUI messagebox when True.
    :return: Exit code where 0 means success and 1 means failure.
    """

    urls = read_urls_file(urls_file)  # Read URLs from input file.

    downloads_dirs = ACTIVE_DOWNLOADS_DIRS if ACTIVE_DOWNLOADS_DIRS else prepare_active_downloads_directory()  # Use cached downloads directories or resolve if cache is empty.

    if tab_count is None or tab_count <= 0:  # Verify tab count validity.
        tab_count = len(urls)  # Use full URL list length when tab count is not positive.

    if tab_count <= 0:  # Verify there are URLs to process.
        print(f"{BackgroundColors.RED}Error: The file {BackgroundColors.CYAN}{urls_file}{BackgroundColors.RED} is empty or contains no valid URLs.{Style.RESET_ALL}")  # Print empty URLs error.
        return 1  # Return error exit code.

    urls = urls[:tab_count]  # Limit URL list to requested tab count.

    extension_img = assets_dir / "Extension.png"  # Define extension image path.
    download_img = assets_dir / "DownloadButton.png"  # Define download button image path.
    confirmation_img = assets_dir / "ConfirmationFileDownloaded.png"  # Define confirmation image path.
    close_download_tab_img = assets_dir / "CloseDownloadTab.png"  # Define close download tab image path.
    mercado_livre_img = assets_dir / "MercadoLivre-GoToProduct.png"  # Define MercadoLivre go-to-product image path.

    print(f"{BackgroundColors.GREEN}Starting automation immediately and activating Chrome window.{Style.RESET_ALL}")  # Print immediate start message.

    if not activate_chrome_window():  # Verify Chrome activation before sending hotkeys.
        return 1  # Return failure exit code when activation fails.

    ext_methods: Dict[str, List[int]] = {}  # Initialize extension method map.
    download_methods: Dict[str, List[int]] = {}  # Initialize download method map.
    completion_methods: Dict[str, List[int]] = {}  # Initialize completion method map.
    close_methods: Dict[str, List[int]] = {}  # Initialize close tab method map.

    processed_count = 0  # Initialize processed tab counter.
    start_tick = time.time()  # Capture workflow start timestamp.
    url_to_download: Dict[str, str] = {}  # Initialize URL to downloaded filename mapping dictionary.
    processed_count, url_to_download, process_success = process_urls_with_download_tracking(urls, tab_count, downloads_dirs, extension_img, download_img, confirmation_img, close_download_tab_img, mercado_livre_img, ext_methods, download_methods, completion_methods, close_methods)  # Process URLs with download tracking and retrieve mapping details.

    if not process_success:  # Verify if URL processing completed without activation failure.
        return 1  # Return failure exit code when URL processing fails.

    if processed_count == tab_count:  # Verify all tabs were processed.
        elapsed_sec = round(time.time() - start_tick)  # Compute elapsed seconds.
        formatted = format_execution_time(elapsed_sec)  # Format elapsed time string.
        report = build_report(ext_methods, download_methods, completion_methods, close_methods)  # Build consolidated report text.
        final_report = f"{BackgroundColors.GREEN}Execution Time: {BackgroundColors.CYAN}{formatted}{BackgroundColors.GREEN}\n\n{report}{Style.RESET_ALL}"  # Compose final report output.

        update_urls_file(urls_file, url_to_download)  # Rewrite URLs file with URL to downloaded filename mapping.
        move_downloaded_archives(downloads_dirs, urls_file.resolve().parent, url_to_download)  # Move downloaded archives into URLs file directory.

        print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Automation Finished{Style.RESET_ALL}\n")  # Print automation completion message.
        print(f"{final_report}")  # Print final report details.

        if not headerless:  # Verify if headerless flag is disabled before showing GUI messagebox
            maybe_show_messagebox("Automation Finished", final_report)  # Display optional messagebox report when allowed

    return 0  # Return success exit code.


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

    repo_root = Path(__file__).resolve().parent.parent  # Resolve repository root path.
    parser = argparse.ArgumentParser(description="Cross-platform affiliate pages downloader automation")  # Initialize argument parser.
    parser.add_argument("--tab-count", type=int, default=0, help="Number of URLs/tabs to process (0 = use all URLs from Inputs/urls.txt)")  # Register tab-count argument.
    parser.add_argument("--urls-file", type=Path, default=repo_root / "Inputs" / "urls.txt", help="Path to URLs input file")  # Register urls-file argument.
    parser.add_argument("--assets-dir", type=Path, default=repo_root / ".assets" / "Browser", help="Directory containing image assets")  # Register assets-dir argument.
    parser.add_argument("--headerless", type=lambda s: str(s).lower() in ("true", "1", "yes", "y"), default=True, help="Whether to suppress GUI messagebox (default: True)")  # Register headerless argument with boolean conversion

    args = parser.parse_args()  # Parse command-line arguments.
    
    exit_code = run(args.tab_count, args.urls_file, args.assets_dir, args.headerless)  # Execute automation flow with headerless option

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
