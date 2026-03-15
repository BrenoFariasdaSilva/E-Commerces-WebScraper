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
import shutil  # Move files between directories.
import sys  # Access process-level runtime controls.
import time  # Manage sleep and elapsed time operations.
from colorama import Style  # Reset ANSI style output.
from pathlib import Path  # Build and resolve filesystem paths.
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

pyautogui.FAILSAFE = True  # Enable fail-safe by moving cursor to the top-left corner.
pyautogui.PAUSE = 0.05  # Apply default pause between pyautogui actions.

EXTENSION_X = 1752  # Define extension click fallback X coordinate.
EXTENSION_Y = 705  # Define extension click fallback Y coordinate.
DOWNLOAD_BUTTON_X = 1590  # Define download button fallback X coordinate.
DOWNLOAD_BUTTON_Y = 64  # Define download button fallback Y coordinate.
CLOSE_DOWNLOAD_TAB_X = 1905  # Define close download tab fallback X coordinate.
CLOSE_DOWNLOAD_TAB_Y = 148  # Define close download tab fallback Y coordinate.
DOWNLOADS_DIR = r"D:\Sem Backup\Download"  # Define monitored downloads directory path.


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

TARGET_CHROME_TITLE = ""  # Store selected Chrome window title for reuse.


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

    try:  # Attempt cross-platform window enumeration.
        get_all_windows = getattr(pyautogui, "getAllWindows", None)  # Resolve optional window listing API.
        windows_raw = get_all_windows() if callable(get_all_windows) else []  # Retrieve all desktop windows when API is available.
        windows = windows_raw if isinstance(windows_raw, list) else []  # Normalize window collection to a list.
    except Exception:  # Handle unsupported window-management backend.
        print(f"{BackgroundColors.YELLOW}Window activation API is unavailable on this system. Keep Chrome focused manually.{Style.RESET_ALL}")  # Print manual-focus warning.
        return True  # Continue execution with manual focus fallback.

    chrome_windows = [w for w in windows if w.title and "chrome" in w.title.lower()]  # Filter Chrome windows by title.

    if not chrome_windows:  # Verify at least one Chrome window exists.
        print(f"{BackgroundColors.RED}No Chrome windows were detected. Automation cannot continue.{Style.RESET_ALL}")  # Print Chrome not found error.
        return False  # Return failure status when no Chrome window is available.

    target_window = None  # Initialize selected window reference.

    if TARGET_CHROME_TITLE != "":  # Verify previous window title is available.
        for window in chrome_windows:  # Iterate candidate Chrome windows.
            if window.title == TARGET_CHROME_TITLE:  # Verify title match with previously selected window.
                target_window = window  # Reuse previously selected window.
                break  # Stop search after finding matching window.

    if target_window is None:  # Verify selected window availability.
        if len(chrome_windows) == 1:  # Verify single-window scenario.
            target_window = chrome_windows[0]  # Select the only Chrome window.
            TARGET_CHROME_TITLE = target_window.title  # Persist selected window title.
        else:  # Enter multi-window selection scenario.
            print(f"{BackgroundColors.YELLOW}Multiple Chrome windows detected:{Style.RESET_ALL}")  # Print multi-window selection header.
            for index, window in enumerate(chrome_windows, start=1):  # Enumerate Chrome windows for user selection.
                print(f"{BackgroundColors.CYAN}{index}.{Style.RESET_ALL} {window.title}")  # Print selectable Chrome window entry.

            try:  # Attempt user selection parsing.
                selected_index = int(input("Select the Chrome window index: ").strip())  # Read selected index from user input.
            except Exception:  # Handle invalid index input.
                print(f"{BackgroundColors.RED}Invalid selection. Automation cannot continue.{Style.RESET_ALL}")  # Print invalid selection error.
                return False  # Return failure status on invalid selection input.

            if selected_index < 1 or selected_index > len(chrome_windows):  # Verify selected index bounds.
                print(f"{BackgroundColors.RED}Selected index is out of range. Automation cannot continue.{Style.RESET_ALL}")  # Print out-of-range selection error.
                return False  # Return failure status on out-of-range selection.

            target_window = chrome_windows[selected_index - 1]  # Select user-chosen Chrome window.
            TARGET_CHROME_TITLE = target_window.title  # Persist selected window title.

    try:  # Attempt window activation sequence.
        target_window.activate()  # Activate selected Chrome window.
        time.sleep(0.2)  # Wait after activation.
        target_window.maximize()  # Maximize selected Chrome window.
        time.sleep(0.8)  # Wait after maximize.
        return True  # Return success status after activation.
    except Exception:  # Handle window activation failure.
        print(f"{BackgroundColors.RED}Failed to activate Chrome window. Keep Chrome focused manually and retry.{Style.RESET_ALL}")  # Print activation failure message.
        return False  # Return failure status after activation exception.


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


def move_downloaded_archives(downloads_dir: Path, destination_dir: Path, url_to_download: Dict[str, str]) -> None:
    """
    Moves downloaded archives from downloads directory to URLs directory.

    :param downloads_dir: Path to the monitored downloads directory.
    :param destination_dir: Path to the target directory where URLs file is located.
    :param url_to_download: Dictionary mapping URL to downloaded filename.
    :return: None.
    """

    unique_filenames = sorted({filename for filename in url_to_download.values() if filename != ""})  # Build sorted unique list of detected downloaded filenames.

    for filename in unique_filenames:  # Iterate over detected downloaded filenames.
        source_path = downloads_dir / filename  # Build source archive file path in downloads directory.
        destination_path = destination_dir / filename  # Build destination archive file path in URLs directory.

        if not source_path.exists():  # Verify if source archive exists before move.
            print(f"{BackgroundColors.YELLOW}[WARNING] Downloaded file not found for move: {source_path}{Style.RESET_ALL}")  # Log missing source archive warning.
            continue  # Continue with next detected archive.

        if destination_path.exists():  # Verify if destination archive already exists.
            print(f"{BackgroundColors.YELLOW}[WARNING] Destination file already exists. Skipping move: {destination_path}{Style.RESET_ALL}")  # Log existing destination archive warning.
            continue  # Continue with next detected archive.

        try:  # Attempt to move archive into destination directory.
            shutil.move(str(source_path), str(destination_path))  # Move detected downloaded archive to URLs directory.
        except Exception:  # Handle archive move failures.
            print(f"{BackgroundColors.YELLOW}[WARNING] Failed to move downloaded file: {source_path}{Style.RESET_ALL}")  # Log archive move failure warning.


def process_urls_with_download_tracking(urls: List[str], tab_count: int, downloads_dir: Path, extension_img: Path, download_img: Path, confirmation_img: Path, close_download_tab_img: Path, mercado_livre_img: Path, ext_methods: Dict[str, List[int]], download_methods: Dict[str, List[int]], completion_methods: Dict[str, List[int]], close_methods: Dict[str, List[int]]) -> Tuple[int, Dict[str, str], bool]:
    """
    Processes URLs while tracking downloaded files by directory snapshots.

    :param urls: URL list to process.
    :param tab_count: Number of URLs to process.
    :param downloads_dir: Path to the monitored downloads directory.
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

    if tab_count > 0:  # Verify if there are URLs to process.
        if not activate_chrome_window():  # Verify if Chrome activation succeeds before opening separator tab.
            return processed_count, url_to_download, False  # Return failure state when Chrome activation fails.

        pyautogui.hotkey("ctrl", "t")  # Open blank separator tab.
        time.sleep(0.2)  # Wait after opening separator tab.

    for index, url in enumerate(urls, start=1):  # Iterate URL list with one-based indexing.
        pre_download_snapshot = snapshot_download_directory(downloads_dir)  # Capture downloads directory snapshot before URL processing.

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

        extension_method = click_image_or_coords(extension_img, EXTENSION_X, EXTENSION_Y)  # Execute extension click action.
        download_method = click_download_button(download_img)  # Execute download click action.
        confirmation_method = wait_for_download_confirmation(confirmation_img)  # Execute completion polling action.
        close_method = close_extension_download_tab(close_download_tab_img)  # Execute close extension tab action.

        post_download_snapshot = snapshot_download_directory(downloads_dir)  # Capture downloads directory snapshot after download completion.
        detected_filename = detect_new_download_file(pre_download_snapshot, post_download_snapshot, url)  # Detect downloaded filename associated with current URL.
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


def click_image_or_coords(image_path: Path, x: int, y: int) -> str:
    """
    Clicks image center or fallback coordinates.

    :param image_path: Path to the primary image target.
    :param x: Fallback X coordinate.
    :param y: Fallback Y coordinate.
    :return: Method name used for the click.
    """

    box = locate_image(image_path)  # Locate image on screen.

    if box is not None:  # Verify image was found.
        pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
        return "ImageSearch"  # Return image search method label.

    pyautogui.click(x, y)  # Click fallback coordinates.
    return "Coordinates"  # Return coordinates method label.


def click_download_button(download_img: Path) -> str:
    """
    Clicks the download button with retry fallback.

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

    pyautogui.click(DOWNLOAD_BUTTON_X, DOWNLOAD_BUTTON_Y)  # Click fallback download coordinates.
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
    Closes extension download tab using image or coordinates.

    :param close_download_tab_img: Path to close tab image.
    :return: Method name used for the click.
    """

    box = locate_image(close_download_tab_img)  # Locate close tab image on screen.

    if box is not None:  # Verify image was found.
        pyautogui.click(box.left, box.top)  # Click top-left point like AHK ImageSearch behavior.
        time.sleep(0.5)  # Wait briefly after image click.
        return "ImageSearch"  # Return image search method label.

    pyautogui.click(CLOSE_DOWNLOAD_TAB_X, CLOSE_DOWNLOAD_TAB_Y)  # Click fallback close tab coordinates.
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


def maybe_show_messagebox(title: str, message: str) -> None:
    """
    Displays messagebox when tkinter is available.

    :param title: Messagebox title string.
    :param message: Messagebox body string.
    :return: None
    """

    try:  # Attempt tkinter import and display flow.
        import tkinter as tk  # Import tkinter module.
        from tkinter import messagebox  # Import tkinter messagebox utility.

        root = tk.Tk()  # Create tkinter root instance.
        root.withdraw()  # Hide root window.
        messagebox.showinfo(title, message)  # Show informational messagebox.
        root.destroy()  # Destroy root window.
    except Exception:  # Handle tkinter availability and GUI exceptions.
        pass  # Skip messagebox display on exception.


def run(tab_count: int | None, urls_file: Path, assets_dir: Path) -> int:
    """
    Runs the affiliate pages automation workflow.

    :param tab_count: Number of tabs and URLs to process.
    :param urls_file: Path to URLs input file.
    :param assets_dir: Path to image assets directory.
    :return: Exit code where 0 means success and 1 means failure.
    """

    urls = read_urls_file(urls_file)  # Read URLs from input file.
    downloads_dir = Path(DOWNLOADS_DIR)  # Build monitored downloads directory path object.

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
    processed_count, url_to_download, process_success = process_urls_with_download_tracking(urls, tab_count, downloads_dir, extension_img, download_img, confirmation_img, close_download_tab_img, mercado_livre_img, ext_methods, download_methods, completion_methods, close_methods)  # Process URLs with download tracking and retrieve mapping details.

    if not process_success:  # Verify if URL processing completed without activation failure.
        return 1  # Return failure exit code when URL processing fails.

    if processed_count == tab_count:  # Verify all tabs were processed.
        elapsed_sec = round(time.time() - start_tick)  # Compute elapsed seconds.
        formatted = format_execution_time(elapsed_sec)  # Format elapsed time string.
        report = build_report(ext_methods, download_methods, completion_methods, close_methods)  # Build consolidated report text.
        final_report = f"{BackgroundColors.GREEN}Execution Time: {BackgroundColors.CYAN}{formatted}{BackgroundColors.GREEN}\n\n{report}{Style.RESET_ALL}"  # Compose final report output.

        update_urls_file(urls_file, url_to_download)  # Rewrite URLs file with URL to downloaded filename mapping.
        move_downloaded_archives(downloads_dir, urls_file.resolve().parent, url_to_download)  # Move downloaded archives into URLs file directory.

        print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Automation Finished{Style.RESET_ALL}\n")  # Print automation completion message.
        print(f"{final_report}")  # Print final report details.
        maybe_show_messagebox("Automation Finished", final_report)  # Display optional messagebox report.

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

    args = parser.parse_args()  # Parse command-line arguments.
    
    exit_code = run(args.tab_count, args.urls_file, args.assets_dir)  # Execute automation flow.

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
