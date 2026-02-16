"""
product_utils.py — Product directory name normalization utilities

Author      : Breno Farias da Silva
Created     : 2026-02-16
Description :
    Small utility module that provides a single source-of-truth for producing
    filesystem-safe product directory names across the scrapers and
    orchestration code. The main export is `normalize_product_dir_name`, which
    performs the following steps in order:

    - Normalizes non-breaking spaces to regular spaces and collapses
    consecutive whitespace.
    - Optionally applies title-casing.
    - Replaces filesystem-invalid characters (e.g. < > : " / \ | ? *) with
    a configurable replacement string (defaults to underscore).
    - Enforces deterministic truncation to 80 characters after all
    sanitization steps to avoid platform-specific truncation/lookup
    mismatches.

Usage:
    from product_utils import normalize_product_dir_name
    safe_name = normalize_product_dir_name(raw_name, replace_with="_", title_case=True)

Returns:
    A sanitized string suitable for use as a directory name.

Dependencies:
    - Python standard library: `re`

Notes:
    - Truncation intentionally happens after sanitization to keep names
      deterministic and consistent between creation and lookup.
"""


import re  # Used for regex-based sanitization of product names for directory naming


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


def normalize_product_dir_name(raw_name: str, replace_with: str = "_", title_case: bool = True) -> str:
    """
    Normalize and sanitize a product name for use as a directory name.

    - Preserves existing sanitization behaviour used across scrapers by allowing
      control over whether to title-case and what to replace invalid filesystem
      characters with.
    - Enforces a strict 80-character limit AFTER sanitization (deterministic
      truncation via slicing).

    :param raw_name: Raw product name string (may contain NBSP, extra spaces, invalid chars)
    :param replace_with: Character to replace invalid filesystem characters with
                         (use empty string to remove them, like Amazon did)
    :param title_case: Whether to apply title-casing (some scrapers use title case)
    :return: Sanitized, truncated product-name-safe string
    """

    if raw_name is None:  # Handle None input gracefully by treating it as an empty string
        raw_name = ""  # This ensures the function always returns a string, even if the input is None

    name = raw_name.replace("\u00A0", " ")  # Normalize NBSP (non-breaking space) to regular space
    name = re.sub(r"\s+", " ", name).strip()  # Collapse multiple spaces and trim leading/trailing whitespace

    if title_case:  # Apply title-casing if enabled (some scrapers use title case, so this is optional)
        name = name.title()  # Convert to title case (first letter of each word capitalized, rest lowercase)

    name = re.sub(r'[<>:"/\\|?*]', replace_with, name)  # Replace invalid filesystem characters with the specified replacement (default is "_", but can be set to "" to remove them)

    name = re.sub(r"\s+", " ", name).strip()  # Collapse multiple spaces again after replacement and trim again, in case replacement introduced extra spaces

    if len(name) > 80:  # Enforce a strict 80-character limit on the final directory name after all sanitization steps (deterministic truncation via slicing)
        name = name[:80]  # Truncate to the first 80 characters if it exceeds the limit

    return name  # Return the fully normalized, sanitized, and truncated product name suitable for use as a directory name
