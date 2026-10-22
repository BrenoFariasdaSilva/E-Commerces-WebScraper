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
        - Optional IANA-timezone timestamps are applied once at the shared
            terminal/file emission boundary.
        - ANSI escape sequences are removed from the file output using a
            conservative regex; lines are flushed immediately to keep logs live.
        - Provides minimal API: `write()`, `flush()` and `close()` so it can be
            used as a drop-in replacement for `sys.stdout`.

Usage:
    from Logger import Logger
    logger = Logger("./Logs/myrun.log", clean=True)
    sys.stdout = logger # optional: redirect all prints to logger

Notes & TODOs:
    - Consider adding log rotation and JSON output format.
    - The ANSI regex is intentionally simple; adjust if you need broader support.

Dependencies:
    - Python >= 3.9 (no external runtime dependencies required)

Assumptions:
    - The log file will contain cleaned, human-readable text (no ANSI codes).
    - The logger is safe for short-lived scripts and long-running processes.
"""
if __name__ in {"__main__", "__mp_main__"}:
    try:
        from setproctitle import setproctitle
        setproctitle(f"DDoS-{__file__.rsplit('/', 1)[-1].rsplit('.', 1)[0]}")
    except ImportError:
        pass


import os  # For interacting with the filesystem
if os.name == "nt":
    import msvcrt  # Windows byte-range locks
else:
    import fcntl  # Unix advisory file locks
import re  # For stripping ANSI escape sequences
import sys  # For replacing stdout/stderr
import threading  # For serializing partial print writes within one process
from datetime import datetime  # Obtain timezone-aware wall-clock timestamps at record emission
from zoneinfo import ZoneInfo  # Resolve the standard-library São Paulo timezone

# Regex Constants:
ANSI_ESCAPE_REGEX = re.compile(r"\x1B\[[0-9;]*[a-zA-Z]")  # Pattern to remove ANSI colors
LEADING_ANSI_ESCAPE_REGEX = re.compile(r"^(?:\x1B\[[0-9;]*[a-zA-Z])+")  # Preserve leading terminal controls before the visible timestamp
LOG_TIMESTAMP_PREFIX_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4} - \d{2}h\d{2}m\d{2}s: ")  # Recognize the exact durable timestamp prefix
SAO_PAULO_TIMEZONE_NAME = "America/Sao_Paulo"  # Define the explicit Brazilian runtime log timezone

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

    def __init__(self, logfile_path, clean=False, timestamp_timezone=None, timestamp_now=None):  # Initialize optional per-record timezone formatting
        """
        Initialize the Logger.

        :param self: Instance of the Logger class.
        :param logfile_path: Path to the log file.
        :param clean: If True, truncate the log file on init; otherwise append.
        :param timestamp_timezone: Optional IANA timezone applied to every non-empty physical line.
        :param timestamp_now: Optional timezone-aware clock callable used for deterministic testing.
        """

        self.logfile_path = logfile_path  # Store log file path

        parent = os.path.dirname(logfile_path)  # Ensure log directory exists
        if parent and not os.path.exists(parent):  # Create parent directories if needed
            os.makedirs(parent, exist_ok=True)  # Safe creation

        self.logfile = open(logfile_path, "a+", encoding="utf-8")  # Keep every process descriptor append-only so stale offsets cannot overwrite records
        if clean:  # Reset prior run contents before concurrent writers exist
            self.logfile.seek(0)  # Position the initial coordinator descriptor for truncation
            self.logfile.truncate()  # Clear prior run contents while retaining append-only writes
        self._lockfile = None  # Keep a dedicated stable lock file on Windows
        if os.name == "nt":
            self._lockfile = open(f"{logfile_path}.lock", "a+b")
            if os.fstat(self._lockfile.fileno()).st_size == 0:
                self._lockfile.write(b"\0")
                self._lockfile.flush()
        self.is_tty = sys.stdout.isatty()  # Verify if stdout is a TTY
        self.timestamp_zone = ZoneInfo(str(timestamp_timezone)) if timestamp_timezone is not None else None  # Resolve the explicit timezone once per logger instance
        self.timestamp_now = timestamp_now if timestamp_now is not None else datetime.now  # Use an injectable timezone-aware emission clock
        self._pending = ""  # Buffer partial print messages until the terminating newline arrives
        self._thread_lock = threading.RLock()  # Synchronize pending fragments and explicit flushes between threads

    def format_message(self, message):  # Prefix every non-empty physical line at emission time
        """
        Format one complete log record with optional timezone-aware timestamps.

        :param self: Instance of the Logger class.
        :param message: Newline-terminated record text.
        :return: Record text with exactly one timestamp on every non-empty physical line.
        """

        if self.timestamp_zone is None:  # Preserve callers that do not opt into timestamp formatting
            return message  # Return the original record unchanged
        emitted_at = self.timestamp_now(self.timestamp_zone)  # Obtain the current explicit-zone time when the record is emitted
        timestamp_prefix = emitted_at.strftime("%d/%m/%Y - %Hh%Mm%Ss: ")  # Format the exact zero-padded Brazilian timestamp
        formatted_lines = []  # Collect physical lines while preserving original line endings
        for line in message.splitlines(keepends=True):  # Format every physical line in one locked logical record
            leading_match = LEADING_ANSI_ESCAPE_REGEX.match(line)  # Locate leading terminal controls such as screen clearing and colors
            leading_ansi = leading_match.group(0) if leading_match is not None else ""  # Preserve leading terminal controls before visible output
            visible_line = line[len(leading_ansi):]  # Read record content after leading terminal controls
            clean_visible_line = ANSI_ESCAPE_REGEX.sub("", visible_line)  # Normalize content before duplicate-prefix detection
            if not clean_visible_line.strip() or LOG_TIMESTAMP_PREFIX_REGEX.match(clean_visible_line):  # Preserve blank lines and already timestamped records
                formatted_lines.append(line)  # Keep the physical line unchanged
            else:  # Prefix one previously untimestamped non-empty physical line
                formatted_lines.append(f"{leading_ansi}{timestamp_prefix}{visible_line}")  # Place terminal controls before the visible timestamp without duplicating content
        return "".join(formatted_lines)  # Return one complete formatted record for locked output

    def _emit_line(self, line):  # Write one complete log line atomically across processes
        """
        Emit one complete physical line while enforcing at most one consecutive blank line.

        :param self: Instance of the Logger class.
        :param line: One newline-terminated physical line to emit.
        """

        lock_acquired = False  # Track whether this call owns the interprocess file lock
        try:  # Serialize log output and blank-line verification across all processes
            if os.name == "nt":
                self._lockfile.seek(0)
                msvcrt.locking(self._lockfile.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(self.logfile.fileno(), fcntl.LOCK_EX)
            lock_acquired = True  # Record successful lock acquisition
            self.logfile.flush()  # Ensure previously written records are visible to file-size queries

            if not ANSI_ESCAPE_REGEX.sub("", line).strip():  # Detect a visually empty line, including ANSI-only output
                file_size = os.fstat(self.logfile.fileno()).st_size  # Determine the shared log's current size
                with open(self.logfile_path, "rb") as reader:
                    reader.seek(max(0, file_size - 2))
                    trailing = reader.read(2)
                if file_size == 0 or trailing.endswith(b"\n\n"):  # Reject leading or repeated physical blank lines
                    return  # Preserve no more than one empty line between records
                line = "\n"  # Normalize an accepted whitespace-only record to exactly one blank line

            output = self.format_message(line)  # Apply an optional timestamp to this complete physical line
            clean_output = ANSI_ESCAPE_REGEX.sub("", output)  # Remove ANSI escapes from the file record
            self.logfile.write(clean_output)  # Append the complete record under the shared process lock
            self.logfile.flush()  # Make the record immediately visible to tail and other processes
            if sys.__stdout__ is not None:  # Mirror the same record to the original output stream
                if self.is_tty:  # Preserve ANSI sequences on interactive terminals
                    sys.__stdout__.write(output)  # Emit the original formatted output
                else:  # Remove terminal control sequences for redirected output
                    sys.__stdout__.write(clean_output)  # Emit the cleaned formatted output
                sys.__stdout__.flush()  # Flush the complete terminal record immediately
        except Exception:  # Preserve the logger's existing best-effort error behavior
            pass  # Do not interrupt the application because logging failed
        finally:  # Release the interprocess lock on every exit path
            if lock_acquired:  # Unlock only when the advisory lock was acquired
                try:  # Protect application execution from unlock errors
                    if os.name == "nt":
                        self._lockfile.seek(0)
                        msvcrt.locking(self._lockfile.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(self.logfile.fileno(), fcntl.LOCK_UN)
                except Exception:  # Preserve the best-effort logger interface
                    pass  # Ignore lock-release failures

    def write(self, message):  # Collect separate print fragments before emitting complete records
        """
        Buffer text and write only newline-terminated physical lines atomically.

        :param self: Instance of the Logger class.
        :param message: The output fragment to log.
        """

        if message is None:  # Ignore absent messages
            return  # Preserve the original silent handling of None
        out = str(message)  # Convert the output fragment to a string without appending newlines
        if not out:  # Ignore empty fragments
            return  # Avoid unnecessary locking and output

        with self._thread_lock:  # Prevent local threads from interleaving message fragments
            self._pending += out  # Append this fragment to the current partial physical line
            while "\n" in self._pending:  # Emit every complete line found in the buffer
                line, self._pending = self._pending.split("\n", 1)  # Separate the first complete line and remaining fragment
                self._emit_line(line + "\n")  # Atomically emit one complete line across processes

    def flush(self):  # Finish any incomplete output and flush the log file
        """
        Flush the pending output fragment and underlying log file.

        :param self: Instance of the Logger class.
        """

        with self._thread_lock:  # Synchronize with writes to the pending buffer
            if self._pending:  # Preserve explicit flush semantics for partial records
                pending = self._pending  # Capture the pending partial physical line
                self._pending = ""  # Clear the buffer before emitting the record
                self._emit_line(pending + "\n")  # Complete the partial line atomically
            try:  # Flush the underlying file buffer
                self.logfile.flush()  # Flush log file
            except Exception:  # Preserve the original best-effort behavior
                pass  # Fail silently

    def close(self):  # Flush buffered text before closing the logger
        """
        Close the log file.

        :param self: Instance of the Logger class.
        """

        try:  # Close the log file
            self.flush()  # Emit any remaining partial physical line before closing
            self.logfile.close()  # Close log file
            if self._lockfile is not None:
                self._lockfile.close()
        except Exception:  # Preserve the original best-effort behavior
            pass  # Fail silently
