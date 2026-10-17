r"""
================================================================================
Logger Utility Module
================================================================================
Author      : Breno Farias da Silva
Created     : 2025-12-11
Description :
    Dual-channel logger that mirrors console output to both the terminal
    (preserving ANSI color sequences when the terminal is a TTY) and a
    sanitized log file (ANSI sequences removed). Designed for use in
    interactive sessions, background jobs, CI pipelines and Makefile runs.

    Behavior:
        - When attached to `sys.stdout`/`sys.stderr` the logger writes colored
            output to the controlling terminal (when available) and a color-free
            record to the specified log file.
        - ANSI escape sequences are removed from the file output using a
            conservative regex; lines are flushed immediately to keep logs live.
        - Provides minimal API: `write()`, `flush()` and `close()` so it can be
            used as a drop-in replacement for `sys.stdout`.

Usage:
    from Logger import Logger
    logger = Logger("./Logs/myrun.log", clean=True)
    sys.stdout = logger # optional: redirect all prints to logger

Notes & TODOs:
    - Consider adding timestamps, log rotation, and JSON output format.
    - The ANSI regex is intentionally simple; adjust if you need broader support.

Dependencies:
    - Python >= 3.8 (no external runtime dependencies required)

Assumptions:
    - The log file will contain cleaned, human-readable text (no ANSI codes).
    - The logger is safe for short-lived scripts and long-running processes.
"""

import os  # For interacting with the filesystem
import re  # For stripping ANSI escape sequences
import sys  # For replacing stdout/stderr

# Regex Constants:
ANSI_ESCAPE_REGEX = re.compile(r"\x1B\[[0-9;]*[a-zA-Z]")  # Pattern to remove ANSI colors

# Classes Definitions:


class Logger:
    """
    Simple logger class that prints colored messages to the terminal and
    writes a cleaned (ANSI-stripped) version to a log file.

    Usage:
       logger = Logger("./Logs/output.log", clean=True)
       logger.info("\x1b[92mHello world\x1b[0m")

    :param logfile_path: Path to the log file.
    :param clean: If True, truncate the log file on init; otherwise append.
    """

    def __init__(self, logfile_path, clean=False):
        """
        Initialize the Logger.

        :param self: Instance of the Logger class.
        :param logfile_path: Path to the log file.
        :param clean: If True, truncate the log file on init; otherwise append.
        """

        self.logfile_path = logfile_path  # Store log file path

        parent = os.path.dirname(logfile_path)  # Ensure log directory exists
        if parent and not os.path.exists(parent):  # Create parent directories if needed
            os.makedirs(parent, exist_ok=True)  # Safe creation

        mode = "w" if clean else "a"  # Choose file mode based on 'clean' flag
        self.logfile = open(logfile_path, mode, encoding="utf-8")  # Open log file
        self.is_tty = sys.__stdout__ is not None and sys.__stdout__.isatty()  # Verify if stdout is a TTY

    def write(self, message):
        """
        Internal method to write messages to both terminal and log file.

        :param self: Instance of the Logger class.
        :param message: The message to log.
        """

        if message is None:  # Ignore None messages
            return  # Early exit

        out = str(message)  # Preserve the exact output-stream content
        if not out:  # Ignore empty writes without inserting line breaks
            return  # No content to emit

        clean_out = ANSI_ESCAPE_REGEX.sub("", out)  # Strip ANSI sequences for log file

        try:  # Write to log file
            self.logfile.write(clean_out)  # Write cleaned message
            self.logfile.flush()  # Ensure immediate write
        except Exception:  # Fail silently to avoid breaking user code
            pass  # Silent fail

        try:  # Write to terminal: colored when TTY, cleaned otherwise
            if sys.__stdout__ is not None:
                if self.is_tty:  # Terminal supports colors
                    sys.__stdout__.write(out)  # Write colored message
                    sys.__stdout__.flush()  # Flush immediately
                else:  # Terminal does not support colors
                    sys.__stdout__.write(clean_out)  # Write cleaned message
                    sys.__stdout__.flush()  # Flush immediately
        except Exception:  # Fail silently to avoid breaking user code
            pass  # Silent fail

    def flush(self):
        """
        Flush the log file.

        :param self: Instance of the Logger class.
        """

        try:  # Flush log file buffer
            self.logfile.flush()  # Flush log file
        except Exception:  # Fail silently
            pass  # Silent fail

    def close(self):
        """
        Close the log file.

        :param self: Instance of the Logger class.
        """

        try:  # Close log file
            self.logfile.close()  # Close log file
        except Exception:  # Fail silently
            pass  # Silent fail
