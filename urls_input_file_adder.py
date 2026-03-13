"""
================================================================================
URLs Input File Adder (Affiliate URLs -> Numbered ZIPs) - urls_input_file_adder.py
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-03-13
Description :
    Reads `urls.txt` from the ./Inputs/ directory, validates each URL using the
    project's `verify_affiliate_url_format` function, appends a two-digit ZIP
    filename to each URL, and overwrites the file with the numbered entries.

    Key features include:
        - Validates affiliate-format short URLs using existing project logic.
        - Appends zero-padded two-digit ZIP filenames (01.zip, 02.zip, ...).
        - Verifies total ZIP count against URL count and reports warnings.
        - Verifies individual assigned ZIP file existence and reports warnings.

Usage:
    1. Place `urls.txt` with one URL per line inside `./Inputs/`.
    2. Execute the script:
            $ python urls_input_file_adder.py
    3. Inspect `./Inputs/urls.txt` for updated entries and `./Inputs/` for ZIPs.

Outputs:
    - Overwritten `./Inputs/urls.txt` containing lines of the form: URL XX.zip.
    - Console/log warnings for validation failures or missing ZIP files.

Dependencies:
    - Python >= 3.9
    - colorama
    - Logger module from the project

Assumptions & Notes:
    - `verify_affiliate_url_format` is available from `main.py` and must be used.
    - The script overwrites `urls.txt` when all URLs validate successfully.
    - ZIP filenames are zero-padded to two digits per specification.
"""


import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import shutil  # For copying files and creating backups
import sys  # For system-specific parameters and functions
from colorama import Style  # For coloring the terminal
from Logger import Logger  # For logging output to both terminal and file
from main import verify_affiliate_url_format  # Import affiliate URL validator from main.py
from pathlib import Path  # For handling file paths
from typing import Optional  # For optional return type annotations


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
INPUT_DIRECTORY = "./Inputs/"  # Directory containing URLs and ZIP files
URLS_FILENAME = "urls.txt"  # Name of the input URLs file

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


def resolve_input_paths(input_directory: str, urls_filename: str) -> tuple:
    """
    Resolve input directory and urls file path.

    :param input_directory: Path to the input directory.
    :param urls_filename: Name of the urls file.
    :return: Tuple of (input_dir Path, urls_path Path or None).
    """

    input_dir = Path(input_directory)  # Create Path for the input directory

    urls_path = input_dir / urls_filename  # Build path to the urls file

    if not urls_path.exists() or not urls_path.is_file():  # Verify that urls.txt exists
        print(f"{BackgroundColors.RED}Error: {BackgroundColors.CYAN}{urls_path}{BackgroundColors.RED} not found or is not a file.{Style.RESET_ALL}")  # Print missing file error
        return input_dir, None  # Return with None to signal missing file

    return input_dir, urls_path  # Return resolved paths


def load_urls_from_file(urls_path: Path, encoding: str) -> Optional[list]:
    """
    Load and clean URL lines from the urls file.

    :param urls_path: Path to the urls file.
    :param encoding: File encoding to use when reading.
    :return: List of cleaned URL strings or None on error.
    """

    try:  # Try to read the urls file
        with open(urls_path, "r", encoding=encoding) as fh:  # Open urls file for reading
            raw_lines = [ln.strip() for ln in fh.readlines() if ln.strip()]  # Read lines and strip whitespace
    except Exception as e:  # If reading fails
        print(f"{BackgroundColors.RED}Error reading {BackgroundColors.CYAN}{urls_path}{BackgroundColors.RED}: {e}{Style.RESET_ALL}")  # Print read error
        return None  # Return None to indicate failure

    return raw_lines  # Return cleaned URL list


def validate_affiliate_urls(urls: list, tag: str) -> bool:
    """
    Validate each URL using project's affiliate URL validator.

    :param urls: List of URL strings to validate.
    :param tag: Arbitrary tag parameter to satisfy signature requirements.
    :return: True when all URLs validate, False otherwise.
    """

    for url in urls:  # Iterate through URLs to validate formats
        if not verify_affiliate_url_format(url):  # Verify each URL using imported validator
            print(f"{BackgroundColors.YELLOW}WARNING: Invalid affiliate URL detected: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}")  # Print invalid URL warning
            return False  # Return False to indicate validation failure

    return True  # Return True when all URLs validate


def generate_numbered_lines(urls: list, input_dir: Path) -> list:
    """
    Generate two-digit ZIP assignments for each URL and report ZIP availability warnings.

    :param urls: List of URL strings to assign ZIP filenames.
    :param input_dir: Path to the input directory where ZIPs are located.
    :return: List of transformed lines as strings.
    """

    zip_files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".zip"]  # List ZIP files in input directory

    zip_count = len(zip_files)  # Count available ZIP files

    url_count = len(urls)  # Count URLs to process

    if url_count > zip_count:  # If URLs exceed ZIPs available
        print(f"{BackgroundColors.YELLOW}WARNING: The number of URLs ({url_count}) exceeds the number of ZIP files available ({zip_count}).{Style.RESET_ALL}")  # Print warning about mismatch

    new_lines = []  # Prepare list to hold updated lines

    for idx, url in enumerate(urls, start=1):  # Iterate and assign numbered ZIP names
        zip_name = f"{str(idx).zfill(2)}.zip"  # Build zero-padded two-digit zip filename
        assigned_zip_path = input_dir / zip_name  # Path to the assigned zip file
        if not assigned_zip_path.exists():  # Verify if the assigned ZIP exists
            print(f"{BackgroundColors.YELLOW}WARNING: Assigned ZIP file {BackgroundColors.CYAN}{zip_name}{BackgroundColors.YELLOW} does not exist in {BackgroundColors.CYAN}{INPUT_DIRECTORY}{BackgroundColors.YELLOW}.{Style.RESET_ALL}")  # Print missing assigned zip warning
        new_lines.append(f"{url} {zip_name}")  # Append the transformed line to the new content

    return new_lines  # Return the updated lines


def write_updated_urls_file(urls_path: Path, new_lines: list) -> bool:
    """
    Write the updated URL lines back to the urls file.

    :param urls_path: Path to the urls file to overwrite.
    :param new_lines: List of updated lines to write.
    :return: True on success, False on failure.
    """

    try:  # Try to overwrite the urls file with updated content
        with open(urls_path, "w", encoding="utf-8") as fh:  # Open urls file for writing
            fh.write("\n".join(new_lines) + ("\n" if new_lines else ""))  # Write updated lines back to file
    except Exception as e:  # If writing fails
        print(f"{BackgroundColors.RED}Error writing updated urls file {BackgroundColors.CYAN}{urls_path}{BackgroundColors.RED}: {e}{Style.RESET_ALL}")  # Print write error
        return False  # Return False to indicate failure

    print(f"{BackgroundColors.GREEN}Updated {BackgroundColors.CYAN}{urls_path}{BackgroundColors.GREEN} with {BackgroundColors.CYAN}{len(new_lines)}{BackgroundColors.GREEN} entries.{Style.RESET_ALL}")  # Print success message

    return True  # Return True to indicate success


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

    print(
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}URLs Input File Adder{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program
    
    input_dir, urls_path = resolve_input_paths(INPUT_DIRECTORY, URLS_FILENAME)  # Resolve input directory and urls path

    if urls_path is None:  # Verify result from path resolution
        return  # Exit when path resolution failed

    urls = load_urls_from_file(urls_path, "utf-8")  # Load URLs from the file with UTF-8 encoding

    if urls is None:  # Verify that URLs loaded successfully
        return  # Exit when loading URLs failed

    if not validate_affiliate_urls(urls, "validator") :  # Validate all affiliate URLs using project validator
        return  # Exit when any URL fails validation

    new_lines = generate_numbered_lines(urls, input_dir)  # Generate numbered ZIP assignments and warnings

    backup_path = input_dir / "urls-backup.txt"  # Build path for the backup file next to urls.txt

    try:  # Attempt to create a backup of the original urls file before modifying it
        shutil.copy2(urls_path, backup_path)  # Copy the original urls file to the backup path preserving metadata
    except Exception as e:  # Catch any exceptions raised during the backup copy operation
        print(f"{BackgroundColors.RED}Error creating backup {BackgroundColors.CYAN}{backup_path}{BackgroundColors.RED}: {e}{Style.RESET_ALL}")  # Report backup creation failure and details
        return  # Abort execution to avoid modifying urls.txt without a safe backup

    if not write_updated_urls_file(urls_path, new_lines) :  # Write the updated urls file back to disk
        return  # Exit when writing the updated file failed

    print(f"{BackgroundColors.GREEN}Updated {BackgroundColors.CYAN}{urls_path}{BackgroundColors.GREEN} with {BackgroundColors.CYAN}{len(new_lines)}{BackgroundColors.GREEN} entries.{Style.RESET_ALL}")  # Print success message

    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the start and finish times
    print(
        f"\n{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )  # Output the end of the program message

    (
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None
    )  # Register the play_sound function to be called when the program finishes


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
