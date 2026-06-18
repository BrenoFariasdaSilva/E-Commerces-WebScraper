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
