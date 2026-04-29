"""
================================================================================
Compressed Archives Renamer by URL Mapping - compressed_archives_renamer.py
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-03-13
Description :
    Reads compressed archive files from the Inputs directory and renames them
    using a deterministic URL-driven mapping system based on urls.txt.
    This script standardizes archive naming for downstream processing.

    Key features include:
        - Detects only .zip, .7z, and .rar files in ./Inputs/.
        - Parses urls.txt into (product_url, expected_filename) entries.
        - Sorts URL entries alphabetically (case-insensitive) by product URL.
        - Assigns deterministic index-based filenames based on sorted URL position.
        - Renames only archives that have an expected_filename in urls.txt.
        - Persists the updated URL-to-filename mapping back into urls.txt.
        - Preserves original archive extensions in final filenames.

Usage:
    1. Populate urls.txt with lines in format:
           {product_url}
           OR
           {product_url} -> {expected_filename}
    2. Place archive files in ./Inputs/.
    3. Execute the script.
        $ python compressed_archives_renamer.py
    4. Verify renamed archive files in ./Inputs/ with numeric names.

Outputs:
    - Renamed archives in ./Inputs/ (01.ext, 02.ext, ..., NN.ext).
    - Updated urls.txt with new filename mappings after renaming.
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
    - urls_utils module

Assumptions & Notes:
    - Only files with .zip, .7z, and .rar extensions are processed.
    - Renaming order is fully determined by alphabetical sort of product URLs in urls.txt.
    - Timestamp-based sorting has been removed in favor of URL-driven deterministic mapping.
    - Renaming runs in-place inside ./Inputs/ without overwriting existing files.
"""


import argparse  # For parsing command-line arguments
import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import re  # For matching duplicate archive naming patterns
import sys  # For system-specific parameters and functions
from colorama import Style  # For coloring the terminal
from Logger import Logger  # For logging output to both terminal and file
from pathlib import Path  # For handling file paths
from typing import Optional  # Optional type hint utility for nullable return values
from urls_utils import preprocess_urls, load_urls_to_process, write_urls_to_file  # URL loading and writing utilities


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
URLS_INPUT_FILE = str(next(Path(__file__).resolve().parents[i] for i, p in enumerate(Path(__file__).resolve().parents) if p.name.lower() == "e-commerces-webscraper") / "Inputs" / "urls.txt")  # Path to the URLs input file containing URL-to-filename mappings

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


def parse_arguments() -> argparse.Namespace:
    """
    Parse and return command-line arguments for the compressed archives renamer program.

    :param: None
    :return: Parsed argument namespace containing all CLI flags.
    """

    parser = argparse.ArgumentParser(description="E-Commerces WebScraper")  # Initialize argument parser

    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output (default: False)")  # Register verbose flag that sets True when provided

    args = parser.parse_args()  # Parse command-line arguments

    return args  # Return parsed argument namespace


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


def list_supported_archives(input_directory):
    """
    Lists archive files in the input directory that match supported extensions.

    :param input_directory: Directory containing files to process.
    :return: List of Path objects for supported archive files.
    """

    directory_path = Path(input_directory)  # Create Path instance for input directory

    if not verify_filepath_exists(directory_path) or not directory_path.is_dir():  # Verify if the input directory exists and is a valid directory
        verbose_output(f"{BackgroundColors.YELLOW}Input directory {BackgroundColors.CYAN}{input_directory}{BackgroundColors.YELLOW} does not exist or is not a valid directory. No files will be processed.{Style.RESET_ALL}")  # Log warning when input directory is invalid with color
        return []  # Return empty list when input directory is invalid

    return [file for file in directory_path.iterdir() if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS]  # Return only supported archive files


def remove_duplicate_archives(input_directory: str) -> None:
    """
    Detects and removes duplicate archive copies before renaming starts.

    :param input_directory: Directory containing archive files to sanitize.
    :return: None.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}Verifying for duplicate archive copies in {BackgroundColors.CYAN}{input_directory}{BackgroundColors.GREEN}...{Style.RESET_ALL}")  # Log the start of duplicate archive checking with color

    directory_path = Path(input_directory)  # Build the Path object for the target input directory

    if not verify_filepath_exists(directory_path) or not directory_path.is_dir():  # Verify if the input directory exists and is a valid directory
        verbose_output(f"{BackgroundColors.YELLOW}Input directory {BackgroundColors.CYAN}{input_directory}{BackgroundColors.YELLOW} does not exist or is not a valid directory. Skipping duplicate archive removal.{Style.RESET_ALL}")  # Log warning when input directory is invalid with color
        return  # Exit early when the input directory is not available

    archive_files = list_supported_archives(input_directory)  # Load all supported archive files from the input directory

    if len(archive_files) == 0:  # Verify if there are archive files available for duplicate removal
        return  # Exit early when there are no archive files to process

    duplicate_suffix_pattern = re.compile(r"(?:\s*\(\d+\)|\s*-\s*Copy(?:\s*\(\d+\))?|\s+Copy(?:\s*\(\d+\))?)$", re.IGNORECASE)  # Build a regex to match common duplicate suffix variants

    original_archives_by_key: dict[tuple[str, str], Path] = {}  # Store original archives indexed by normalized stem and extension
    duplicate_archives_by_key: dict[tuple[str, str], list[Path]] = {}  # Store duplicate archives indexed by normalized stem and extension

    for archive_file in archive_files:  # Iterate through each archive file to classify original and duplicate variants
        original_stem = archive_file.stem  # Capture the current filename stem without extension
        normalized_stem = original_stem  # Initialize the normalized stem with the current filename stem
        has_duplicate_pattern = False  # Initialize duplicate pattern flag for the current archive file

        while True:  # Repeatedly remove duplicate suffix blocks until no further change occurs
            updated_stem = duplicate_suffix_pattern.sub("", normalized_stem).strip()  # Remove one trailing duplicate suffix block from the normalized stem

            if updated_stem == normalized_stem:  # Verify if no more duplicate suffix block remains in the normalized stem
                break  # Exit the normalization loop when the stem remains unchanged

            normalized_stem = updated_stem  # Update the normalized stem with the cleaned stem value
            has_duplicate_pattern = True  # Mark this archive as a duplicate-pattern variant

        archive_key = (normalized_stem.lower(), archive_file.suffix.lower())  # Build a deterministic grouping key using normalized stem and extension

        if has_duplicate_pattern:  # Verify if the current archive filename contains duplicate suffix patterns
            duplicate_archives_by_key.setdefault(archive_key, []).append(archive_file)  # Store the archive as duplicate under its grouping key
        else:  # Handle archive files that do not contain duplicate suffix patterns
            if archive_key not in original_archives_by_key:  # Verify if an original archive is not already registered for this grouping key
                original_archives_by_key[archive_key] = archive_file  # Register the clean archive as the original file for this grouping key

    for archive_key, duplicate_files in duplicate_archives_by_key.items():  # Iterate through each duplicate group to remove duplicate files safely
        if len(duplicate_files) == 0:  # Verify if the duplicate group has files available for processing
            continue  # Skip groups with no duplicate files

        original_file = original_archives_by_key.get(archive_key)  # Retrieve the clean original archive associated with this duplicate group

        if original_file is None:  # Verify if no clean original archive is available for this duplicate group
            continue  # Skip deletion when a clean original archive is not found

        print(f"{BackgroundColors.YELLOW} Duplicate archive detected for base file: {BackgroundColors.CYAN}{original_file.name}{Style.RESET_ALL}")  # Log duplicate detection for the preserved original archive with color

        for duplicate_file in duplicate_files:  # Iterate through each duplicate archive file mapped to the current original archive
            if not verify_filepath_exists(duplicate_file):  # Verify if the duplicate archive file still exists before deletion
                continue  # Skip deletion when the duplicate file path no longer exists

            print(f"{BackgroundColors.YELLOW} Removing duplicate archive: {BackgroundColors.CYAN}{duplicate_file.name}{Style.RESET_ALL}")  # Log duplicate archive deletion before removing the file with color

            try:  # Start protected duplicate archive deletion block
                duplicate_file.unlink()  # Delete the duplicate archive file from disk
            except Exception as exception_error:  # Capture deletion failures without breaking the remaining workflow
                print(f"{BackgroundColors.RED} Failed to remove duplicate archive: {BackgroundColors.CYAN}{duplicate_file.name}{BackgroundColors.RED} | Error: {exception_error}{Style.RESET_ALL}")  # Log deletion failure details for troubleshooting with color


def parse_url_entries(input_file_path: str) -> list[tuple[str, Optional[str]]]:
    """
    Parse the URLs input file into structured product_url and expected_filename entries.

    :param input_file_path: Path to the URLs input file to parse.
    :return: List of (product_url, expected_filename or None) tuples.
    """

    raw_lines = load_urls_to_process(input_file_path)  # Load raw lines from the URLs input file
    preprocessed_lines = preprocess_urls(raw_lines)  # Preprocess the raw lines to clean and sort them
    url_entries: list[tuple[str, Optional[str]]] = []  # Initialize list to hold parsed URL entries

    for line in preprocessed_lines:  # Iterate over each preprocessed line from the URLs file
        parts = line.split(None, 1)  # Split on first whitespace (URL + optional filename)

        product_url = parts[0].strip() if parts else ""  # Extract product URL from first token
        expected_filename = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None  # Extract optional filename when present

        if product_url:  # Verify if the parsed product URL is not empty before appending
            url_entries.append((product_url, expected_filename))  # Append the parsed URL entry to the list

    return url_entries  # Return the list of parsed URL entries


def resolve_archive_match(expected_filename: str, input_directory: str) -> Optional[Path]:
    """
    Resolve an expected filename to a matching archive file path in the input directory.

    :param expected_filename: Filename to resolve against files in the input directory.
    :param input_directory: Directory path to search for the matching archive file.
    :return: Path of the matched archive file, or None if no match is found.
    """

    directory_path = Path(input_directory)  # Build the Path object for the input directory

    if not verify_filepath_exists(directory_path) or not directory_path.is_dir():  # Verify if the input directory exists and is a valid directory
        print(f"{BackgroundColors.YELLOW}Input directory {BackgroundColors.CYAN}{input_directory}{BackgroundColors.YELLOW} does not exist or is not a valid directory. Cannot resolve expected filename: {BackgroundColors.CYAN}{expected_filename}{Style.RESET_ALL}")  # Log warning when input directory is invalid with color and expected filename details
        return None  # Return None when the input directory is not accessible

    candidate = directory_path / expected_filename  # Build the full candidate path for the expected archive file

    if verify_filepath_exists(candidate) and candidate.is_file():  # Verify if the expected file exists in the input directory
        verbose_output(f"{BackgroundColors.GREEN}Found matching archive for expected filename: {BackgroundColors.CYAN}{expected_filename}{Style.RESET_ALL}")  # Log successful match of expected filename with color
        return candidate  # Return the resolved Path when the expected file is found

    return None  # Return None when no matching archive file is found


def perform_safe_rename(source_path: Path, target_path: Path) -> bool:
    """
    Rename source archive file to target path without overwriting existing files.

    :param source_path: Original Path of the archive file to rename.
    :param target_path: Destination Path for the renamed archive file.
    :return: True if the rename succeeded, False otherwise.
    """

    if not verify_filepath_exists(source_path):  # Verify if the source file exists before attempting rename
        print(f"{BackgroundColors.RED}Source file not found for rename: {BackgroundColors.CYAN}{source_path.name}{Style.RESET_ALL}")  # Log missing source file error
        return False  # Return False when source file is not accessible

    if verify_filepath_exists(target_path):  # Verify if the target path already exists to prevent overwrite
        print(f"{BackgroundColors.RED}Target file already exists, skipping rename: {BackgroundColors.CYAN}{target_path.name}{Style.RESET_ALL}")  # Log overwrite prevention warning
        return False  # Return False when target file already exists

    try:  # Attempt the rename operation safely
        source_path.rename(target_path)  # Rename the source archive file to the target path
        return True  # Return True when the rename operation completes successfully
    except Exception as rename_error:  # Capture any rename operation failures without breaking execution
        print(f"{BackgroundColors.RED}Failed to rename {BackgroundColors.CYAN}{source_path.name}{BackgroundColors.RED} to {BackgroundColors.CYAN}{target_path.name}{BackgroundColors.RED}: {rename_error}{Style.RESET_ALL}")  # Log rename failure details
        return False  # Return False when the rename operation fails


def build_updated_mapping(url_entries: list[tuple[str, Optional[str]]], rename_map: dict[str, str]) -> list:
    """
    Build the updated URL-to-filename mapping list for writing back to urls.txt.

    :param url_entries: Sorted list of (product_url, expected_filename or None) tuples.
    :param rename_map: Dictionary mapping old filenames to new filenames from completed renames.
    :return: List of URLs or (url, filename) tuples suitable for write_urls_to_file.
    """

    updated_mapping: list = []  # Initialize the list to hold the updated URL-filename mapping entries

    for product_url, expected_filename in url_entries:  # Iterate over each sorted URL entry
        if expected_filename is None:  # Verify if this entry has no associated expected filename
            updated_mapping.append(product_url)  # Append URL as plain string when no filename mapping exists
        else:  # Handle entries that contain an associated expected filename
            new_filename = rename_map.get(expected_filename, expected_filename)  # Retrieve new filename from rename map, falling back to original
            updated_mapping.append((product_url, new_filename))  # Append the URL-filename tuple with the updated filename

    return updated_mapping  # Return the complete updated mapping list


def process_url_based_renames(input_directory: str, urls_file_path: str) -> None:
    """
    Orchestrate URL-driven deterministic archive renaming using urls.txt mappings.

    :param input_directory: Directory containing the archive files to rename.
    :param urls_file_path: Path to the URLs input file containing URL-filename mappings.
    :return: None.
    """

    url_entries = parse_url_entries(urls_file_path)  # Parse the URLs file into structured URL-filename entries

    if not url_entries:  # Verify if any URL entries were loaded from the input file
        print(f"{BackgroundColors.YELLOW}No URL entries found in: {BackgroundColors.CYAN}{urls_file_path}{Style.RESET_ALL}")  # Log warning when no entries are found
        return  # Exit early when there are no URL entries to process

    rename_map: dict[str, str] = {}  # Initialize dictionary to track old-to-new filename renames

    for index, (product_url, expected_filename) in enumerate(url_entries, start=1):  # Iterate with 1-based index over sorted URL entries
        if expected_filename is None:  # Verify if this entry has no expected filename to process
            continue  # Skip entries without an expected filename mapping

        source_path = resolve_archive_match(expected_filename, input_directory)  # Resolve the expected filename to a real archive file path

        if source_path is None:  # Verify if the expected archive file was found in the input directory
            verbose_output(f"{BackgroundColors.YELLOW}No matching archive found for: {BackgroundColors.CYAN}{expected_filename}{Style.RESET_ALL}")  # Log warning when no matching archive is found
            continue  # Skip this entry when no matching archive file is found

        new_filename = f"{index:02d}{source_path.suffix}"  # Build the deterministic index-based filename for this archive
        target_path = source_path.parent / new_filename  # Build the full target path for the renamed archive

        verbose_output(f"{BackgroundColors.GREEN}Renaming {BackgroundColors.CYAN}{source_path.name}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{new_filename}{Style.RESET_ALL}")  # Log the rename operation details

        rename_success = perform_safe_rename(source_path, target_path)  # Perform the safe rename of the archive file

        if rename_success:  # Verify if the rename operation completed successfully
            verbose_output(f"{BackgroundColors.GREEN}Successfully renamed {BackgroundColors.CYAN}{source_path.name}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{new_filename}{Style.RESET_ALL}")
            rename_map[expected_filename] = new_filename  # Record the successful rename in the tracking dictionary

    updated_mapping = build_updated_mapping(url_entries, rename_map)  # Build the updated URL-filename mapping from rename results
    write_urls_to_file(updated_mapping, urls_file_path, recursive=True, sort=True)  # Write updated mapping to the URLs file sorted alphabetically


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
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Compressed Archives Renamer Python{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program
    
    args = parse_arguments()  # Parse command-line arguments

    if args.verbose:  # Verify if verbose mode is enabled
        global VERBOSE  # Set the global VERBOSE variable to True when the --verbose flag is provided
        VERBOSE = False  # Enable verbose output
    
    print(f"{BackgroundColors.GREEN}Scanning {BackgroundColors.CYAN}{INPUT_DIRECTORY}{BackgroundColors.GREEN} for compressed files...{Style.RESET_ALL}")  # Output scanning message 
    
    remove_duplicate_archives(INPUT_DIRECTORY)  # Remove duplicate archive copies before collecting files for sequential renaming
    
    archive_files = list_supported_archives(INPUT_DIRECTORY)  # Get supported archive files from the input directory

    verbose_output(f"{BackgroundColors.GREEN}Detected {BackgroundColors.CYAN}{len(archive_files)}{BackgroundColors.GREEN} compressed files.{Style.RESET_ALL}")  # Output detected archive count
    
    if len(archive_files) == 0:  # If no archive files were found
        print(f"{BackgroundColors.GREEN}No supported compressed files found in {BackgroundColors.CYAN}{INPUT_DIRECTORY}{BackgroundColors.GREEN}.{Style.RESET_ALL}")  # Output no files found message
        return

    process_url_based_renames(INPUT_DIRECTORY, URLS_INPUT_FILE)  # Process URL-driven deterministic archive renaming

    verbose_output(f"{BackgroundColors.GREEN}Renaming of the compressed files in {BackgroundColors.CYAN}{INPUT_DIRECTORY}{BackgroundColors.GREEN} completed successfully.{Style.RESET_ALL}")  # Output rename completion message
    
    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the start and finish times
    print(
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
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
