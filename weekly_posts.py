"""
================================================================================
Weekly Posts Distribution
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-06-18
Description :
    Merge timestamped output directories into a weekly distribution structure
    grouped by platform and spread across weekday directories.

    Key features include:
        - Timestamp directory detection using the existing output naming format
        - Duplicate directory resolution by structure, file count, and size
        - Platform and title directory normalization before distribution
        - Weekday distribution with remaining items assigned to Sunday
        - Two-digit indexing for child directories inside each weekday folder

Usage:
    1. Keep the default output path configured in the constants below.
    2. Execute the script directly with Python.
        $ python weekly_posts.py
    3. Review distributed folders in the configured Outputs directory.

Outputs:
    - Outputs/To-Distribute
    - Outputs/Next-Week or Outputs/Next-Week-N
    - Outputs/<weekday name> (<post count>)

TODOs:
    - None.

Dependencies:
    - Python >= 3.10
    - colorama

Assumptions & Notes:
    - The default Outputs directory is the canonical target for this project.
    - Files and directories not matched by the workflow remain untouched unless
      the existing merge rules move them from timestamp directories.
"""


from __future__ import annotations  # Enable postponed annotation evaluation.

import atexit  # Register a finish action.
import datetime  # Capture program timing.
import os  # Run operating system commands.
import platform  # Detect the operating system.
import re  # Match directory naming patterns.
import shutil  # Move and remove directories.
import sys  # Redirect standard streams.
from collections import defaultdict  # Group post directories by platform.
from pathlib import Path  # Handle filesystem paths.
from typing import Any  # Import Any for flexible timing values.
from colorama import Style  # Reset terminal colors
from Logger import Logger  # Log output to terminal and file.


class BackgroundColors:  # Define terminal color constants.
    CYAN = "\033[96m"  # Set cyan color.
    GREEN = "\033[92m"  # Set green color.
    YELLOW = "\033[93m"  # Set yellow color.
    RED = "\033[91m"  # Set red color.
    BOLD = "\033[1m"  # Set bold style.
    UNDERLINE = "\033[4m"  # Set underline style.
    CLEAR_TERMINAL = "\033[H\033[J"  # Clear the terminal.


VERBOSE = False  # Set verbose output off by default.

logger = Logger(f"./Logs/{Path(__file__).stem}.log", clean=True)  # Create a Logger instance.
sys.stdout = logger  # Redirect stdout to the logger.
sys.stderr = logger  # Redirect stderr to the logger.

SOUND_COMMANDS = {  # Define sound commands by operating system.
    "Darwin": "afplay",  # Set macOS sound command.
    "Linux": "aplay",  # Set Linux sound command.
    "Windows": "start",  # Set Windows sound command.
}  # Close sound command mapping.
SOUND_FILE = "./.assets/Sounds/NotificationSound.wav"  # Set the notification sound path.

RUN_FUNCTIONS = {  # Configure optional finish actions.
    "Play Sound": True,  # Enable finish sound registration.
}  # Close optional finish actions.

OUTPUTS_DIR = Path(r"D:\Backup\GitHub\Public\E-Commerces-WebScraper\Outputs")  # Set the default outputs directory.
TO_DISTRIBUTE_DIR = OUTPUTS_DIR / "To-Distribute"  # Set the staging distribution directory.
TIMESTAMP_DIR_PATTERN = re.compile(r"^\d+\.\s\d{4}-\d{2}-\d{2}\s-\s\d{2}h\d{2}m\d{2}s$")  # Match timestamp directory names.
POST_DIR_PATTERN = re.compile(r"^(\d+)\.\s(.+?)\s-\s(.+)$")  # Match indexed post directory names.
CHILD_INDEX_PATTERN = re.compile(r"^\d+\.\s(.+)$")  # Match indexed weekday child directory names.
TEMP_INDEX_PREFIX = ".weekly-posts-indexing-"  # Set temporary indexing prefix.
WEEKDAYS = [  # Define weekday directory names.
    "1. Monday",  # Set Monday directory name.
    "2. Tuesday",  # Set Tuesday directory name.
    "3. Wednesday",  # Set Wednesday directory name.
    "4. Thursday",  # Set Thursday directory name.
    "5. Friday",  # Set Friday directory name.
    "6. Saturday",  # Set Saturday directory name.
    "7. Sunday",  # Set Sunday directory name.
]  # Close weekday directory names.


# Functions Definitions:


def index_all_weekday_child_directories() -> None:  # Index children inside all weekdays.
    """
    Index child directories inside every staged weekday directory.

    :param: None
    :return: None
    """

    for weekday in WEEKDAYS:  # Iterate weekday names.
        weekday_path = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday path.

        if weekday_path.is_dir():  # Detect staged weekday directory.
            index_weekday_child_directories(weekday_path)  # Index child directories.


def distribute_platform_directories() -> None:  # Distribute post directories across weekdays.
    """
    Distribute platform directories evenly across weekdays.

    :param: None
    :return: None
    """

    weekday_paths = create_weekday_directories()  # Create weekday directories.
    platform_map: defaultdict[str, list[Path]] = defaultdict(list)  # Initialize platform mapping.
    post_dirs = [path for path in TO_DISTRIBUTE_DIR.iterdir() if path.is_dir() and path.name not in WEEKDAYS]  # Collect post directories.
    post_dirs.sort(key=lambda path: path.name.lower())  # Sort post directories case-insensitively.

    for post_dir in post_dirs:  # Iterate post directories.
        platform = get_platform_name(post_dir.name)  # Extract platform name.

        if platform:  # Detect valid platform name.
            platform_map[platform].append(post_dir)  # Store post directory by platform.

    for platform_dirs in platform_map.values():  # Iterate platform directory groups.
        total = len(platform_dirs)  # Count platform directories.
        base_amount = total // 7  # Calculate base weekday amount.
        remainder = total % 7  # Calculate Sunday remainder.
        index = 0  # Initialize platform directory index.

        for weekday_index, weekday in enumerate(WEEKDAYS):  # Iterate weekdays in configured order.
            amount = base_amount  # Set base amount for weekday.

            if weekday_index == 6:  # Detect Sunday.
                amount += remainder  # Assign remainder to Sunday.

            for _ in range(amount):  # Move configured amount for weekday.
                source = platform_dirs[index]  # Get source post directory.
                destination = weekday_paths[weekday] / source.name  # Build weekday destination.
                shutil.move(str(source), str(destination))  # Move post directory to weekday.
                index += 1  # Advance platform directory index.


def outputs_already_has_weekdays() -> bool:  # Detect existing weekday directories in Outputs.
    """
    Return whether Outputs already contains weekday directories.

    :param: None
    :return: True when Outputs contains an uncounted weekday directory.
    """

    return any((OUTPUTS_DIR / weekday).exists() for weekday in WEEKDAYS)  # Return existing weekday result.


def rename_weekday_with_count(weekday_path: Path) -> None:  # Rename weekday with child count.
    """
    Rename a weekday directory with its child directory count.

    :param weekday_path: Weekday directory path.
    :return: None
    """

    weekday_path.rename(get_weekday_directory_with_count(weekday_path))  # Rename weekday path with count.


def finalize_distribution() -> None:  # Finalize staged distribution.
    """
    Move weekday directories to Outputs unless they already exist.

    :param: None
    :return: None
    """

    index_all_weekday_child_directories()  # Index child directories inside staged weekdays.

    if outputs_already_has_weekdays():  # Detect existing weekday directories.
        target_dir = get_next_week_directory()  # Get Next-Week target directory.

        for weekday in WEEKDAYS:  # Iterate weekday names.
            weekday_path = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday path.

            if weekday_path.exists():  # Detect staged weekday path.
                rename_weekday_with_count(weekday_path)  # Rename weekday with count.

        TO_DISTRIBUTE_DIR.rename(target_dir)  # Rename staging directory to Next-Week target.
        return  # Stop finalization.

    for weekday in WEEKDAYS:  # Iterate weekday names.
        source = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday source.

        if not source.exists():  # Skip missing weekday source.
            continue  # Continue to next weekday.

        rename_weekday_with_count(source)  # Rename weekday with count.

    for source in TO_DISTRIBUTE_DIR.iterdir():  # Iterate remaining staged entries.
        if not source.is_dir():  # Skip non-directory entries.
            continue  # Continue to next entry.

        destination = OUTPUTS_DIR / source.name  # Build final destination path.
        shutil.move(str(source), str(destination))  # Move directory to Outputs.

    shutil.rmtree(TO_DISTRIBUTE_DIR)  # Remove staging directory.


def run_weekly_posts_distribution() -> None:  # Run weekly post distribution workflow.
    """
    Run the weekly post distribution workflow.

    :param: None
    :return: None
    """

    move_timestamp_directories()  # Move timestamp directories into staging.

    if not TO_DISTRIBUTE_DIR.exists():  # Detect missing staging directory.
        return  # Stop workflow when staging is absent.

    remove_indexes_from_post_directories()  # Normalize post directory names.
    distribute_platform_directories()  # Distribute post directories by weekday.
    finalize_distribution()  # Finalize distribution output.


def to_seconds(obj: Any) -> float | None:  # Convert time-like values.
    """
    Convert various time-like objects to seconds.

    :param obj: Object to convert.
    :return: Equivalent time in seconds, or None when conversion fails.
    """

    if obj is None:  # Detect missing value.
        return None  # Return no conversion.

    if isinstance(obj, (int, float)):  # Detect numeric value.
        return float(obj)  # Return numeric seconds.

    if hasattr(obj, "total_seconds"):  # Detect timedelta-like object.
        try:  # Attempt timedelta conversion.
            return float(obj.total_seconds())  # Return total seconds.
        except Exception:  # Handle conversion failure.
            pass  # Continue to other conversions.

    if hasattr(obj, "timestamp"):  # Detect datetime-like object.
        try:  # Attempt timestamp conversion.
            return float(obj.timestamp())  # Return timestamp seconds.
        except Exception:  # Handle conversion failure.
            pass  # Continue to fallback.

    return None  # Return no conversion.


def calculate_execution_time(start_time: Any, finish_time: Any | None = None) -> str:  # Calculate readable duration.
    """
    Calculate execution time and return a human-readable string.

    :param start_time: Start time, duration, or numeric seconds.
    :param finish_time: Finish time or numeric seconds.
    :return: Formatted execution time.
    """

    if finish_time is None:  # Use single-argument duration mode.
        total_seconds = to_seconds(start_time)  # Convert provided duration.
        if total_seconds is None:  # Detect conversion failure.
            try:  # Attempt numeric conversion.
                total_seconds = float(start_time)  # Convert value to float.
            except Exception:  # Handle numeric conversion failure.
                total_seconds = 0.0  # Use zero fallback.
    else:  # Use start and finish mode.
        st = to_seconds(start_time)  # Convert start time.
        ft = to_seconds(finish_time)  # Convert finish time.
        if st is not None and ft is not None:  # Detect successful conversions.
            total_seconds = ft - st  # Calculate numeric difference.
        else:  # Use subtraction fallback.
            try:  # Attempt direct subtraction.
                delta = finish_time - start_time  # Calculate time delta.
                total_seconds = float(delta.total_seconds())  # Convert delta to seconds.
            except Exception:  # Handle subtraction failure.
                try:  # Attempt numeric fallback.
                    total_seconds = float(finish_time) - float(start_time)  # Calculate numeric difference.
                except Exception:  # Handle numeric fallback failure.
                    total_seconds = 0.0  # Use zero fallback.

    if total_seconds is None:  # Detect missing total seconds.
        total_seconds = 0.0  # Use zero fallback.

    if total_seconds < 0:  # Detect negative duration.
        total_seconds = abs(total_seconds)  # Normalize to positive duration.

    days = int(total_seconds // 86400)  # Calculate full days.
    hours = int((total_seconds % 86400) // 3600)  # Calculate remaining hours.
    minutes = int((total_seconds % 3600) // 60)  # Calculate remaining minutes.
    seconds = int(total_seconds % 60)  # Calculate remaining seconds.

    if days > 0:  # Detect day-level duration.
        return f"{days}d {hours}h {minutes}m {seconds}s"  # Return days format.

    if hours > 0:  # Detect hour-level duration.
        return f"{hours}h {minutes}m {seconds}s"  # Return hours format.

    if minutes > 0:  # Detect minute-level duration.
        return f"{minutes}m {seconds}s"  # Return minutes format.

    return f"{seconds}s"  # Return seconds format.


def play_sound() -> None:  # Play finish sound when available.
    """
    Play a sound when the program finishes and skip Windows.

    :param: None
    :return: None
    """

    current_os = platform.system()  # Get the current operating system.

    if current_os == "Windows":  # Detect Windows platform.
        return  # Skip sound on Windows.

    if verify_filepath_exists(SOUND_FILE):  # Verify sound file existence.
        if current_os in SOUND_COMMANDS:  # Detect supported operating system.
            os.system(f"{SOUND_COMMANDS[current_os]} {SOUND_FILE}")  # Play notification sound.
        else:  # Handle unsupported operating system.
            print(f"{BackgroundColors.RED}The {BackgroundColors.CYAN}{current_os}{BackgroundColors.RED} is not in the {BackgroundColors.CYAN}SOUND_COMMANDS dictionary{BackgroundColors.RED}. Please add it!{Style.RESET_ALL}")  # Log unsupported platform.
    else:  # Handle missing sound file.
        print(f"{BackgroundColors.RED}Sound file {BackgroundColors.CYAN}{SOUND_FILE}{BackgroundColors.RED} not found. Make sure the file exists.{Style.RESET_ALL}")  # Log missing sound file.


def main() -> None:  # Run program entrypoint.
    """
    Main function.

    :param: None
    :return: None
    """

    print(f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Weekly Posts Distribution{BackgroundColors.GREEN} program!{Style.RESET_ALL}", end="\n\n")  # Output welcome message.
    
    start_time = datetime.datetime.now()  # Get program start time.
    
    run_weekly_posts_distribution()  # Run weekly post distribution workflow.
    
    finish_time = datetime.datetime.now()  # Get program finish time.
    
    print(f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}")  # Output timing summary.
    
    print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}")  # Output finish message.
    
    (atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None)  # Register finish sound action.


if __name__ == "__main__":  # Run script entrypoint.
    """
    This is the standard boilerplate that calls the main function.

    :return: None
    """

    main()  # Call main function.
