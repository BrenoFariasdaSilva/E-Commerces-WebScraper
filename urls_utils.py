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
