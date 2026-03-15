r"""
Product Directory Name Normalization Utility - product_utils.py

Author      : Breno Farias da Silva
Created     : 2026-02-16
Description :
    Small utility module that provides a single source-of-truth for producing
    filesystem-safe product directory names across the scrapers and
    orchestration code. The main export is `normalize_product_name`, which
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
    from product_utils import normalize_product_name
    safe_name = normalize_product_name(raw_name, replace_with="", title_case=True)

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
VERBOSE = True  # Set to True to output verbose messages


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


def normalize_product_name(raw_name: str, replace_with: str = "", title_case: bool = True) -> str:
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
    
    verbose_output(f"Before Normalization: '{raw_name}'")  # Log the raw product name being normalized

    if raw_name is None:  # Handle None input gracefully by treating it as an empty string
        raw_name = ""  # Ensure function always processes a string value

    name = str(raw_name)  # Convert input to string for deterministic normalization flow
    name = name.replace("\u00A0", " ")  # Normalize NBSP (non-breaking space) to regular space
    name = re.sub(r"[\\/]+", " - ", name)  # Replace slash and backslash runs with a safe textual separator
    name = re.sub(r"(?:\s*-\s*){2,}", " - ", name)  # Collapse repeated textual separators into a single readable separator
    name = name.replace(",", "")  # Remove commas from directory name content
    name = re.sub(r"\s+", " ", name)  # Collapse multiple consecutive spaces to a single space
    name = re.sub(r"\s*-\s*", " - ", name)  # Normalize separator spacing around textual dash separator
    name = name.strip()  # Remove leading and trailing whitespace from the full normalized string

    if title_case:  # Apply title-casing if enabled (some scrapers use title case, so this is optional)
        name = name.title()  # Convert to title case while preserving separator readability

    name = re.sub(r'[<>:"|?*]', replace_with, name)  # Replace invalid filesystem characters while preserving readable textual separators
    name = re.sub(r"\s+", " ", name)  # Collapse spaces again to keep deterministic output after replacement
    name = re.sub(r"\s*-\s*", " - ", name)  # Normalize separator spacing again after replacement step
    name = name.strip().rstrip("-/")  # Remove leading and trailing whitespace and trailing textual separator characters

    max_length = 80  # Define strict maximum length for deterministic truncation safety
    if len(name) > max_length:  # Verify whether normalized name exceeds maximum length
        truncated_name = name[:max_length].rstrip(" -/")  # Truncate to length limit and remove trailing spaces or separators

        if max_length < len(name) and not name[max_length].isspace():  # Verify whether truncation occurred in the middle of a word
            last_space_index = truncated_name.rfind(" ")  # Locate the last safe word boundary inside the truncated region
            last_separator_index = truncated_name.rfind(" - ")  # Locate the last safe textual separator boundary inside the truncated region
            cut_index = max(last_space_index, last_separator_index)  # Select the furthest safe boundary to avoid partial word endings

            if cut_index > 0:  # Verify whether a safe boundary exists beyond the first character
                truncated_name = truncated_name[:cut_index].rstrip(" -/")  # Remove partial trailing word and clean trailing spaces or separators

        name = truncated_name  # Apply hardened truncated value back to the normalized name

    name = re.sub(r"(?:\s*-\s*){2,}", " - ", name)  # Collapse repeated textual separators after truncation adjustments
    name = re.sub(r"\s+", " ", name)  # Collapse multiple spaces after truncation adjustments
    name = name.strip().rstrip("-/")  # Enforce no trailing whitespace or separator characters in final normalized value

    verbose_output(f"After Normalization: '{name}'\n")  # Log the final normalized product name
    return name  # Return the fully normalized, sanitized, and truncated product name suitable for use as a directory name
