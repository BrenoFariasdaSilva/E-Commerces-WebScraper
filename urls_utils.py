r"""
URLs Utilities - urls_utils.py

Author      : Breno Farias da Silva
Created     : 2026-04-06
Description :
    Small utility module that provides helper functions for preprocessing
    lists of URL strings (for example, lines read from Inputs/urls.txt).
    The primary utilities are:

    - `strip_whitespace_and_filter(urls)`: strip leading/trailing whitespace
      and remove empty entries.
    - `remove_dash_prefixes(urls)`: remove leading "- " or "-- " prefixes
      commonly used to mark or comment-out lines.
    - `sort_urls(urls)`: return an alphabetically sorted copy of the list.
    - `preprocess_urls(urls)`: convenience wrapper that runs the above
      steps in the recommended order.

Usage:
    from urls_utils import preprocess_urls
    cleaned = preprocess_urls(raw_lines)

Returns:
    Processed list of URL strings ready for downstream scraping.

Dependencies:
    - Python standard library: `re`

Notes:
    - Functions are pure and return new lists instead of mutating inputs.
    - Keep the helpers small and composable so they are easy to test.
"""


import re  # Used for regex-based sanitization of product names for directory naming
import os  # Filesystem utilities for reading/writing input files
from pathlib import Path  # Path utilities for atomic write operations
from colorama import Style  # Colorize terminal text output


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


def strip_whitespace_and_filter(input_urls: list[str]) -> list[str]:
    """
    Strip leading/trailing whitespace and remove empty strings.

    :param input_urls: List of URL strings to clean.
    :return: Cleaned list with no empty entries.
    """

    cleaned: list[str] = []  # Initialize an empty list to hold the cleaned URLs
    
    for url in input_urls:  # Iterate over each URL in the input list
        cleaned_url = url.strip()  # Remove leading and trailing whitespace from the URL
        if cleaned_url:  # If the resulting string is not empty after stripping
            cleaned.append(cleaned_url)  # Add the cleaned URL to the list of cleaned URLs
        
    return cleaned  # Return the list of cleaned URLs


def remove_dash_prefixes(input_urls: list[str]) -> list[str]:
    """
    Remove both '- ' or ' - ' and '-- ' or ' -- ' prefixes from the start of lines (before the urls).

    The order matters: remove the longer prefix first so "-- " isn't
    partially consumed by the shorter prefix removal.
    
    :param input_urls: List of URL strings to process.
    :return: List of URLs with specified prefixes removed.
    """

    updated: list[str] = []  # Initialize an empty list to hold the updated URLs after prefix removal
    
    for url in input_urls:  # Iterate over each URL in the input list
        if re.match(r"^\s*--\s+", url):  # Check if line starts with optional whitespace followed by '-- ' prefix
            updated.append(re.sub(r"^\s*--\s+", "", url))  # Remove '-- ' or ' -- ' prefix (including leading whitespace) and append result
            continue  # Move to next URL after handling double-dash case

        if re.match(r"^\s*-\s+", url):  # Check if line starts with optional whitespace followed by '- ' prefix
            updated.append(re.sub(r"^\s*-\s+", "", url))  # Remove '- ' or ' - ' prefix (including leading whitespace) and append result
            continue  # Move to next URL after handling single-dash case

        updated.append(url)  # Append URL unchanged if no matching prefix is found

    return updated  # Return the processed list of URLs


def sort_urls(input_urls: list[str]) -> list[str]:
    """
    Return an alphabetically sorted copy of the list.

    :param input_urls: List of URL strings.
    :return: New sorted list.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}Sorting {BackgroundColors.CYAN}{len(input_urls)}{BackgroundColors.GREEN} URLs...{Style.RESET_ALL}")  # Log the start of URL sorting

    return sorted(input_urls)  # Return a new list sorted in alphabetical order without modifying the original list


def preprocess_urls(urls: list[str]) -> list[str]:
    """
    Preprocesses a list of URLs by stripping whitespace and removing empty entries.
    Also, it calls two functions. One for detecting "- " and "-- " at the start of the line of the urls.txt file and another for sorting the urls in alphabetical order.

    :param urls: A list of URL strings to preprocess.
    :return: A new list of preprocessed URL strings.
    """
    
    verbose_output(f"{BackgroundColors.GREEN}Preprocessing {BackgroundColors.CYAN}{len(urls)}{BackgroundColors.GREEN}URLs...{Style.RESET_ALL}")  # Log the start of URL preprocessing

    cleaned = strip_whitespace_and_filter(urls)  # Remove leading/trailing whitespace and filter out empty strings
    without_prefixes = remove_dash_prefixes(cleaned)  # Remove any leading "-- " or "- " prefixes from the URLs
    sorted_urls = sort_urls(without_prefixes)  # Sort the URLs in alphabetical order
    
    return sorted_urls  # Return the URLs sorted in alphabetical order


def load_urls_to_process(input_file) -> list[str]:
    """
    Load the input file and return a list of non-empty trimmed lines.

    Each returned list item is the raw trimmed line from the file. The
    caller is responsible for splitting URL and optional local path if
    needed.

    Args:
        input_file (str): path to the input file to read.

    Returns:
        list[str]: list of non-empty, trimmed lines from the file.
    """

    url_list: list[str] = []  # Initialize list to collect URL strings from the input file

    try:  # Attempt to read the input file
        if os.path.exists(input_file):  # Check that the input file exists before attempting to read
            with open(input_file, "r", encoding="utf-8") as fh:  # Open input file for reading with UTF-8 encoding
                for line in fh:  # Iterate over each line in the input file
                    line = line.strip()  # Trim leading/trailing whitespace from the line
                    if not line:  # Skip blank/empty lines
                        continue  # Continue to next file line when current is empty
                    url_list.append(line)  # Append the raw line (URL or 'URL local_path') to the list
        else:
            print(f"{BackgroundColors.YELLOW}Input file not found: {input_file}{Style.RESET_ALL}")  # Warn when input file is missing
    except Exception as e:  # Catch and report any IO/OS errors
        print(f"{BackgroundColors.RED}Error reading input file {input_file}: {e}{Style.RESET_ALL}")  # Report read errors

    return url_list  # Return the collected URL lines as strings


def write_urls_to_file(input_file, urls_to_write):
    """
    Write a list of URLs (with optional local paths) to the specified input file.

    Each item in `urls_to_write` must be a tuple (url, local_html_path)
    where `local_html_path` may be None. The file is replaced atomically
    using a temporary sibling file.

    Returns True on success, False otherwise.
    """

    tmp_path = None  # Temporary path reference, defined here to ensure it's always bound
    try:
        input_path = Path(input_file)  # Construct Path object for the target input file
        if not input_path.parent.exists():  # Ensure parent directory exists before writing
            input_path.parent.mkdir(parents=True, exist_ok=True)  # Create parent directories as needed

        tmp_path = input_path.with_suffix(input_path.suffix + ".tmp")  # Create a sibling temporary filename
        written = 0  # Counter for written entries
        with open(tmp_path, "w", encoding="utf-8") as fh:  # Open temporary file for atomic write
            for url, local in urls_to_write:  # Iterate over tuples to write
                if not url:  # Skip entries with empty URL
                    continue  # Continue to next tuple when URL is falsy
                line = url if not local else f"{url} {local}"  # Compose line with optional local path
                fh.write(line.rstrip() + "\n")  # Write the composed line and ensure newline
                written += 1  # Increment written counter

        os.replace(str(tmp_path), str(input_path))  # Atomically replace original file with temporary file
        verbose_output(f"{BackgroundColors.GREEN}Wrote {written} entries to {BackgroundColors.CYAN}{input_file}{Style.RESET_ALL}")  # Verbose log of success
        return True  # Success

    except Exception as e:
        print(f"{BackgroundColors.RED}Failed to write input file {input_file}: {e}{Style.RESET_ALL}")  # Report failure
        try:
            if tmp_path and tmp_path.exists():  # Guard tmp_path access to avoid unbound-variable issues
                tmp_path.unlink()  # Attempt to remove temporary file on failure
        except Exception:
            pass  # Ignore cleanup errors
        return False  # Indicate failure
