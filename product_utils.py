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
