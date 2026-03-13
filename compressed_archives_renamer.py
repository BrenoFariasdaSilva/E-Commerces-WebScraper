"""
================================================================================
Compressed Archives Renamer by Creation Date - compressed_archives_renamer.py
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-03-13
Description :
    Reads compressed archive files from the Inputs directory and renames them
    in chronological creation order using sequential numeric filenames.
    This script standardizes archive naming for downstream processing.

    Key features include:
        - Detects only .zip, .7z, and .rar files in ./Inputs/.
        - Collects file creation timestamps with cross-platform-safe fallback.
        - Sorts archives from oldest to newest before renaming.
        - Preserves original archive extensions in final filenames.
        - Uses a two-phase temporary rename workflow to avoid overwrite risks.

Usage:
    1. Place archive files in ./Inputs/.
    2. Execute the script.
        $ python compressed_archives_renamer.py
    3. Verify renamed archive files in ./Inputs/ with numeric names.

Outputs:
    - Renamed archives in ./Inputs/ (01.ext, 02.ext, ..., NN.ext).
    - Execution logs in ./Logs/compressed_archives_renamer.log.

TODOs:
    - Add dry-run mode to preview rename operations.
    - Add configurable input directory via CLI arguments.
    - Add rollback strategy for interrupted rename sessions.
    - Add optional JSON operation report generation.

Dependencies:
    - Python >= 3.9
    - colorama
    - telegram_bot module
    - Logger module

Assumptions & Notes:
    - Only files with .zip, .7z, and .rar extensions are processed.
    - File creation time uses st_birthtime when available, else st_ctime.
    - On Windows, st_ctime usually represents true creation time.
    - Renaming runs in-place inside ./Inputs/ using a conflict-safe two-phase flow.
"""


import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import sys  # For system-specific parameters and functions
from colorama import Style  # For coloring the terminal
from Logger import Logger  # For logging output to both terminal and file
from pathlib import Path  # For handling file paths


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
INPUT_DIRECTORY = "./Inputs/"  # Directory containing compressed files to rename
SUPPORTED_EXTENSIONS = (".zip", ".7z", ".rar")  # Supported compressed archive extensions

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


def list_supported_archives(input_directory):
    """
    Lists archive files in the input directory that match supported extensions.

    :param input_directory: Directory containing files to process.
    :return: List of Path objects for supported archive files.
    """

    directory_path = Path(input_directory)  # Create Path instance for input directory

    if not directory_path.exists() or not directory_path.is_dir():  # Verify if input directory is valid
        return []  # Return empty list when input directory is invalid

    return [file for file in directory_path.iterdir() if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS]  # Return only supported archive files


def get_creation_timestamp(file_path):
    """
    Gets the most reliable creation timestamp for a file.

    :param file_path: Path object of the target file.
    :return: Creation timestamp as float seconds.
    """

    stats = file_path.stat()  # Get filesystem metadata for the file

    if hasattr(stats, "st_birthtime"):  # Verify if true birth time is available on the platform
        return float(stats.st_birthtime)  # Return true creation time when available

    return float(stats.st_ctime)  # Return ctime fallback when birth time is unavailable


def assign_temporary_names(archive_files_sorted: list[Path], temporary_mappings: list) -> None:
    """
    Assign temporary unique names to sorted archive files.

    :param archive_files_sorted: List of Path objects sorted by creation time.
    :param temporary_mappings: List to be populated with (original, temporary) tuples.
    :return: None
    """

    temporary_index = 0  # Initialize the temporary index counter

    for index, source_file in enumerate(archive_files_sorted, start=1):  # Iterate over sorted files to assign temporary names
        temporary_file = source_file.with_name(f"__tmp__{index:04d}{source_file.suffix}")  # Build temporary file name with original extension

        while temporary_file.exists():  # Verify if generated temporary name already exists
            temporary_file = source_file.with_name(f"__tmp__{index:04d}_{datetime.datetime.now().strftime('%f')}{source_file.suffix}")  # Build a unique temporary name using microseconds

        source_file.rename(temporary_file)  # Rename source file to temporary file name
        temporary_mappings.append((source_file, temporary_file))  # Store mapping for phase two rename
        temporary_index += 1  # Increment the temporary index counter


def finalize_renames(temporary_mappings: list) -> None:
    """
    Rename temporary files to final sequential numeric names.

    :param temporary_mappings: List of (original, temporary) Path tuples produced earlier.
    :return: None
    """

    for index, (original_file, temporary_file) in enumerate(temporary_mappings, start=1):  # Iterate over temporary mappings to assign final names
        final_file = temporary_file.with_name(f"{index:02d}{original_file.suffix}")  # Build final sequential file name with original extension

        if final_file.exists():  # Verify if final file already exists unexpectedly
            raise FileExistsError(f"Target file already exists and cannot be overwritten: {final_file}")  # Raise overwrite protection error

        verbose_output(f"{BackgroundColors.GREEN}Renaming {BackgroundColors.CYAN}{original_file.name}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{final_file.name}{Style.RESET_ALL}")  # Output rename operation message

        temporary_file.rename(final_file)  # Rename temporary file to final file name


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
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Compressed Archives Renamer Python{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program
    
    archive_files = list_supported_archives(INPUT_DIRECTORY)  # Get supported archive files from the input directory

    verbose_output(f"{BackgroundColors.GREEN}Detected {BackgroundColors.CYAN}{len(archive_files)}{BackgroundColors.GREEN} compressed files.{Style.RESET_ALL}")  # Output detected archive count
    
    if len(archive_files) == 0:  # If no archive files were found
        print(f"{BackgroundColors.GREEN}No supported compressed files found in {BackgroundColors.CYAN}{INPUT_DIRECTORY}{BackgroundColors.GREEN}.{Style.RESET_ALL}")  # Output no files found message
        return

    verbose_output(f"{BackgroundColors.GREEN}Sorting files by creation time...{Style.RESET_ALL}")  # Output sorting operation message

    archive_files_sorted = sorted(archive_files, key=lambda file: (get_creation_timestamp(file), file.name.lower()))  # Sort files from oldest to newest

    temporary_mappings = []  # Store source and temporary path mappings

    assign_temporary_names(archive_files_sorted, temporary_mappings)  # Assign temporary names to all sorted archive files

    finalize_renames(temporary_mappings)  # Rename temporary files to final sequential numeric names

    verbose_output(f"{BackgroundColors.GREEN}Renaming complete.{Style.RESET_ALL}")  # Output completion message

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
