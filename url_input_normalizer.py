"""
================================================================================
URL INPUT NORMALIZER
================================================================================
Author      : Breno Farias da Silva
Description :
    Normalizes the repository URL input file while preserving the template's
    terminal formatting, execution-time reporting, path utilities, and sound
    notification behavior.

Usage:
    Run this script with the repository's configured Python command.

Outputs:
    - Inputs/urls.txt
    - Inputs/urls-backup.txt
    - Weekly_Urls_Sorted.txt beside the selected input file

Dependencies:
    - Python
    - colorama

Assumptions & Notes:
    - Input is read from Inputs/urls.txt before Input/urls.txt.
    - Only trimmed HTTP and HTTPS URL lines are retained.
    - Duplicate URL occurrences are removed after URL normalization.
"""

import atexit  # Register the optional completion sound.
from collections import Counter  # Count normalized URLs per detected platform domain.
import datetime  # Capture program start and finish times.
import os  # Access operating-system and file replacement operations.
import platform  # Identify the current operating system.
import re  # Split URLs into numeric and nonnumeric sorting components.
import tempfile  # Create staged files for atomic replacement.
from pathlib import Path  # Resolve repository-relative input and output paths.
from typing import Any, Dict, List, Optional, Tuple, Union  # Define compatible type annotations.
from urllib.parse import urlsplit, urlunsplit  # Parse URLs with standard-library components.

from colorama import Style  # Reset terminal formatting after colored output.


class BackgroundColors:  # Store terminal formatting escape sequences.
    CYAN = "\033[96m"  # Apply cyan foreground formatting.
    GREEN = "\033[92m"  # Apply green foreground formatting.
    YELLOW = "\033[93m"  # Apply yellow foreground formatting.
    RED = "\033[91m"  # Apply red foreground formatting.
    BOLD = "\033[1m"  # Apply bold terminal formatting.
    UNDERLINE = "\033[4m"  # Apply underlined terminal formatting.
    CLEAR_TERMINAL = "\033[H\033[J"  # Clear the terminal display.


VERBOSE = False  # Control optional verbose terminal output.

SOUND_COMMANDS = {  # Map supported operating systems to sound commands.
    "Darwin": "afplay",  # Use the macOS audio player.
    "Linux": "aplay",  # Use the Linux audio player.
    "Windows": "start",  # Preserve the configured Windows command.
}  # Complete the sound-command mapping.
SOUND_FILE = "./.assets/Sounds/NotificationSound.wav"  # Store the completion sound path.

RUN_FUNCTIONS = {  # Control optional program behaviors.
    "Play Sound": True,  # Enable the completion sound registration.
}  # Complete the runtime behavior mapping.

WEEKLY_URLS_FILENAME = "Weekly_Urls_Sorted.txt"  # Store the Google Keep weekly URL output filename.
WEEKDAY_LABELS = (  # Store weekday labels in the required Google Keep order.
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    "Domingo",
)  # Complete the weekday label tuple.


def verbose_output(true_string: str = "", false_string: str = "") -> None:  # Output the configured verbose or fallback message.
    """
    Output a message according to the verbose configuration.

    :param true_string: Message to output when verbose mode is enabled.
    :param false_string: Message to output when verbose mode is disabled.
    :return: None.
    """

    if VERBOSE and true_string != "":  # Verify verbose mode and message availability.
        print(true_string)  # Output the verbose message.
    elif false_string != "":  # Verify fallback message availability.
        print(false_string)  # Output the fallback message.


def resolve_entry_with_trailing_space(current_path: str, entry: str, stripped_part: str) -> str:  # Resolve one path entry with surrounding spaces.
    """
    Resolve and optionally rename a directory entry with trailing spaces.

    :param current_path: Current directory path.
    :param entry: Directory entry name.
    :param stripped_part: Normalized target name without surrounding spaces.
    :return: Resolved path after an optional rename.
    """

    try:  # Preserve the existing fallback behavior for unexpected failures.
        resolved = os.path.join(current_path, entry)  # Build the original resolved path.

        if entry != stripped_part:  # Verify whether the entry requires normalization.
            corrected = os.path.join(current_path, stripped_part)  # Build the corrected path.

            try:  # Attempt to rename the entry safely.
                os.rename(resolved, corrected)  # Rename the entry to its normalized name.
                verbose_output(true_string=f"{BackgroundColors.GREEN}Renamed: {BackgroundColors.CYAN}{resolved}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{corrected}{Style.RESET_ALL}")  # Report the successful rename in verbose mode.
                resolved = corrected  # Retain the corrected resolved path.
            except Exception:  # Preserve execution when the rename fails.
                verbose_output(true_string=f"{BackgroundColors.RED}Failed to rename: {BackgroundColors.CYAN}{resolved}{Style.RESET_ALL}")  # Report the rename failure in verbose mode.

        return resolved  # Return the resolved path.
    except Exception:  # Preserve the original fallback path construction.
        return os.path.join(current_path, entry)  # Return the unresolved entry path.


def resolve_full_trailing_space_path(filepath: str) -> str:  # Resolve trailing-space mismatches across a complete path.
    """
    Resolve trailing-space mismatches across all path components.

    :param filepath: Path containing possible trailing-space mismatches.
    :return: Corrected full path when matches exist, otherwise the original path.
    """

    try:  # Preserve the existing nonfatal path-resolution behavior.
        verbose_output(true_string=f"{BackgroundColors.GREEN}Resolving full trailing space path for: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}")  # Report the resolution attempt in verbose mode.

        if not isinstance(filepath, str) or not filepath:  # Verify filepath validity before processing.
            verbose_output(true_string=f"{BackgroundColors.YELLOW}Invalid filepath provided, skipping resolution.{Style.RESET_ALL}")  # Report the invalid input in verbose mode.

            return filepath  # Return the original invalid value.

        filepath = os.path.expanduser(filepath)  # Expand a leading user-home marker.
        parts = filepath.split(os.sep)  # Split the path into components.

        if not parts:  # Verify that path components are available.

            return filepath  # Return the original path when no components exist.

        if filepath.startswith(os.sep):  # Handle absolute paths from the filesystem root.
            current_path = os.sep  # Initialize traversal at the filesystem root.
            parts = parts[1:]  # Remove the empty root component.
        else:  # Handle relative paths from their first component.
            current_path = parts[0] if parts[0] else os.getcwd()  # Initialize the relative traversal base.
            parts = parts[1:] if parts[0] else parts  # Remove the initialized base component.

        for part in parts:  # Traverse every remaining path component.
            if part == "":  # Verify whether the component is empty.
                continue  # Skip empty path components.

            try:  # Attempt to list the current traversal directory.
                entries = os.listdir(current_path) if os.path.isdir(current_path) else []  # Read directory entries when the base exists.
            except Exception:  # Preserve the original fallback when listing fails.
                verbose_output(true_string=f"{BackgroundColors.RED}Failed to list directory: {BackgroundColors.CYAN}{current_path}{Style.RESET_ALL}")  # Report the listing failure in verbose mode.

                return filepath  # Return the original path after a listing failure.

            stripped_part = part.strip()  # Normalize the current requested component.
            match_found = False  # Track whether a matching entry is resolved.

            for entry in entries:  # Compare every directory entry with the requested component.
                try:  # Preserve traversal when one entry comparison fails.
                    if entry.strip() == stripped_part:  # Verify a normalized component match.
                        current_path = resolve_entry_with_trailing_space(current_path, entry, stripped_part)  # Resolve the matching entry path.
                        match_found = True  # Record the successful component match.

                        break  # Stop searching after the first matching entry.
                except Exception:  # Preserve traversal after an entry-specific failure.
                    continue  # Continue with the next directory entry.

            if not match_found:  # Verify whether the current component was unresolved.
                verbose_output(true_string=f"{BackgroundColors.YELLOW}No match for segment: {BackgroundColors.CYAN}{part}{Style.RESET_ALL}")  # Report the unresolved component in verbose mode.

                return filepath  # Return the original path after an unresolved component.

        return current_path  # Return the fully resolved path.
    except Exception:  # Preserve the original path after an unexpected failure.
        verbose_output(true_string=f"{BackgroundColors.RED}Error resolving full path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}")  # Report the unexpected failure in verbose mode.

        return filepath  # Return the original path.


def verify_filepath_exists(filepath: str) -> bool:  # Verify whether a file or directory exists through configured resolution strategies.
    """
    Verify whether a file or directory exists at the specified path.

    :param filepath: Path to the file or directory.
    :return: True when a matching path exists, otherwise False.
    """

    try:  # Preserve the existing raised-error behavior for unexpected failures.
        verbose_output(
            f"{BackgroundColors.GREEN}Verifying if the file or folder exists at the path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}"
        )  # Report the existence verification in verbose mode.

        if not isinstance(filepath, str) or not filepath.strip():  # Verify that the input is a nonempty string.
            verbose_output(true_string=f"{BackgroundColors.YELLOW}Invalid filepath provided, skipping existence verification.{Style.RESET_ALL}")  # Report the invalid path in verbose mode.

            return False  # Reject invalid path input.

        if os.path.exists(filepath):  # Verify the original path before normalization.

            return True  # Return immediately when the original path exists.

        candidate = str(filepath).strip()  # Normalize surrounding whitespace from the path.

        if (candidate.startswith("'") and candidate.endswith("'")) or (
            candidate.startswith('"') and candidate.endswith('"')
        ):  # Verify whether configuration quotes surround the path.
            candidate = candidate[1:-1].strip()  # Remove wrapping quotes and surrounding whitespace.

        candidate = os.path.expanduser(candidate)  # Expand a leading user-home marker.
        candidate = os.path.normpath(candidate)  # Normalize separators and structural components.

        if os.path.exists(candidate):  # Verify the normalized candidate directly.

            return True  # Return when the normalized path exists.

        repo_dir = os.path.dirname(os.path.abspath(__file__))  # Resolve the script directory.
        cwd = os.getcwd()  # Capture the current working directory.
        alt = candidate.lstrip(os.sep) if candidate.startswith(os.sep) else candidate  # Prepare a relative-safe candidate.
        repo_candidate = os.path.join(repo_dir, alt)  # Build the script-relative candidate.
        cwd_candidate = os.path.join(cwd, alt)  # Build the working-directory-relative candidate.

        for path_variant in (repo_candidate, cwd_candidate):  # Traverse the alternative base paths.
            try:  # Preserve traversal when one normalization attempt fails.
                normalized_variant = os.path.normpath(path_variant)  # Normalize the alternative path.

                if os.path.exists(normalized_variant):  # Verify whether the alternative path exists.

                    return True  # Return when an alternative path exists.
            except Exception:  # Preserve traversal after an alternative-path failure.
                continue  # Continue with the next alternative path.

        try:  # Attempt absolute path resolution as a fallback.
            abs_candidate = os.path.abspath(candidate)  # Build the absolute candidate path.

            if os.path.exists(abs_candidate):  # Verify whether the absolute path exists.

                return True  # Return when the absolute path exists.
        except Exception:  # Preserve execution after absolute resolution fails.
            pass  # Continue to trailing-space resolution.

        for path_variant in (candidate, repo_candidate, cwd_candidate):  # Traverse candidates for trailing-space resolution.
            try:  # Attempt trailing-space resolution for the current candidate.
                resolved = resolve_full_trailing_space_path(path_variant)  # Resolve possible component mismatches.

                if resolved != path_variant and os.path.exists(resolved):  # Verify a changed path that now exists.
                    verbose_output(
                        f"{BackgroundColors.YELLOW}Resolved trailing space mismatch: {BackgroundColors.CYAN}{path_variant}{BackgroundColors.YELLOW} -> {BackgroundColors.CYAN}{resolved}{Style.RESET_ALL}"
                    )  # Report the resolved mismatch in verbose mode.

                    return True  # Return when the corrected path exists.
            except Exception:  # Preserve traversal after a candidate-specific failure.
                continue  # Continue with the next candidate path.

        return False  # Report that no path resolution strategy succeeded.
    except Exception as error:  # Preserve the original raised-error behavior.
        print(str(error))  # Output the failure for terminal diagnostics.

        raise  # Re-raise the original failure.


def to_seconds(obj: Any) -> Optional[float]:  # Convert supported time-like objects to seconds.
    """
    Convert a supported time-like object to seconds.

    :param obj: Numeric, timedelta-like, datetime-like, or unsupported object.
    :return: Converted seconds, or None when conversion is unavailable.
    """

    if obj is None:  # Verify whether no value was provided.

        return None  # Signal that conversion is unavailable.

    if isinstance(obj, (int, float)):  # Verify whether the value is already numeric.

        return float(obj)  # Return numeric seconds as a float.

    if hasattr(obj, "total_seconds"):  # Verify whether the object exposes duration conversion.
        try:  # Attempt duration conversion.

            return float(obj.total_seconds())  # Convert the duration to seconds.
        except Exception:  # Preserve fallback conversion behavior.
            pass  # Continue to timestamp conversion.

    if hasattr(obj, "timestamp"):  # Verify whether the object exposes timestamp conversion.
        try:  # Attempt timestamp conversion.

            return float(obj.timestamp())  # Convert the timestamp to seconds.
        except Exception:  # Preserve the unavailable-conversion result.
            pass  # Continue to the final result.

    return None  # Signal that conversion is unavailable.


def calculate_execution_time(start_time: Any, finish_time: Optional[Any] = None) -> str:  # Format an elapsed duration from one or two time values.
    """
    Calculate and format execution time from duration or boundary values.

    :param start_time: Duration value or execution start value.
    :param finish_time: Optional execution finish value.
    :return: Human-readable elapsed duration.
    """

    if finish_time is None:  # Select single-value duration conversion.
        total_seconds = to_seconds(start_time)  # Convert the provided duration value.

        if total_seconds is None:  # Verify whether direct conversion failed.
            try:  # Attempt numeric coercion as a fallback.
                total_seconds = float(start_time)  # Coerce the duration to numeric seconds.
            except Exception:  # Preserve the zero-duration fallback.
                total_seconds = 0.0  # Default an unsupported duration to zero.
    else:  # Select two-value boundary conversion.
        start_seconds = to_seconds(start_time)  # Convert the start boundary to seconds.
        finish_seconds = to_seconds(finish_time)  # Convert the finish boundary to seconds.

        if start_seconds is not None and finish_seconds is not None:  # Verify successful boundary conversions.
            total_seconds = finish_seconds - start_seconds  # Calculate elapsed numeric seconds.
        else:  # Use subtraction fallbacks for unsupported boundary objects.
            try:  # Attempt direct subtraction for datetime-like values.
                delta = finish_time - start_time  # Calculate the elapsed duration object.
                total_seconds = float(delta.total_seconds())  # Convert the elapsed duration to seconds.
            except Exception:  # Continue to numeric boundary coercion.
                try:  # Attempt final numeric boundary coercion.
                    total_seconds = float(finish_time) - float(start_time)  # Calculate coerced elapsed seconds.
                except Exception:  # Preserve the zero-duration fallback.
                    total_seconds = 0.0  # Default unsupported boundaries to zero.

    if total_seconds is None:  # Verify that a numeric duration is available.
        total_seconds = 0.0  # Default an unavailable duration to zero.

    if total_seconds < 0:  # Verify whether the duration is negative.
        total_seconds = abs(total_seconds)  # Normalize the duration to a positive value.

    days = int(total_seconds // 86400)  # Calculate complete elapsed days.
    hours = int((total_seconds % 86400) // 3600)  # Calculate remaining elapsed hours.
    minutes = int((total_seconds % 3600) // 60)  # Calculate remaining elapsed minutes.
    seconds = int(total_seconds % 60)  # Calculate remaining elapsed seconds.

    if days > 0:  # Verify whether the result includes complete days.

        return f"{days}d {hours}h {minutes}m {seconds}s"  # Return the day-level duration.

    if hours > 0:  # Verify whether the result includes complete hours.

        return f"{hours}h {minutes}m {seconds}s"  # Return the hour-level duration.

    if minutes > 0:  # Verify whether the result includes complete minutes.

        return f"{minutes}m {seconds}s"  # Return the minute-level duration.

    return f"{seconds}s"  # Return the second-level duration.


def play_sound() -> None:  # Play the configured completion sound on supported systems.
    """
    Play a sound when the program finishes outside Windows.

    :return: None.
    """

    current_os = platform.system()  # Identify the current operating system.

    if current_os == "Windows":  # Verify whether sound playback is disabled on Windows.

        return  # Skip sound playback on Windows.

    if verify_filepath_exists(SOUND_FILE):  # Verify whether the configured sound file exists.
        if current_os in SOUND_COMMANDS:  # Verify whether a sound command is configured.
            os.system(f"{SOUND_COMMANDS[current_os]} {SOUND_FILE}")  # Execute the configured sound command.
        else:  # Report an unsupported operating system.
            print(
                f"{BackgroundColors.RED}The {BackgroundColors.CYAN}{current_os}{BackgroundColors.RED} is not in the {BackgroundColors.CYAN}SOUND_COMMANDS dictionary{BackgroundColors.RED}. Please add it!{Style.RESET_ALL}"
            )  # Output the unsupported-system message.
    else:  # Report a missing completion sound file.
        print(
            f"{BackgroundColors.RED}Sound file {BackgroundColors.CYAN}{SOUND_FILE}{BackgroundColors.RED} not found. Make sure the file exists.{Style.RESET_ALL}"
        )  # Output the missing-sound message.


def resolve_url_source(script_directory: Path) -> Tuple[Path, bool]:  # Resolve the preferred URL source file and source-conflict state.
    """
    Resolve the URL source file using canonical directory precedence.

    :param script_directory: Directory containing the executing script.
    :return: Selected source path and whether both candidate files exist.
    """

    canonical_source = script_directory / "Inputs" / "urls.txt"  # Build the canonical source path.
    legacy_source = script_directory / "Input" / "urls.txt"  # Build the legacy source path.
    canonical_exists = canonical_source.is_file()  # Verify whether the canonical source file exists.
    legacy_exists = legacy_source.is_file()  # Verify whether the legacy source file exists.

    if canonical_exists:  # Prefer the canonical source whenever it exists.

        return canonical_source, legacy_exists  # Return the canonical source and conflict state.

    if legacy_exists:  # Use the legacy source when the canonical source is unavailable.

        return legacy_source, False  # Return the legacy source without a source conflict.

    raise FileNotFoundError(  # Raise a clear failure without creating output files.
        f'URL input file not found. Expected "{canonical_source}" or "{legacy_source}".'
    )  # Complete the missing-input failure.


def extract_valid_urls(source_path: Path) -> List[str]:  # Read and retain trimmed HTTP and HTTPS URL lines.
    """
    Read a source file and extract valid trimmed URL lines.

    :param source_path: Existing URL source file path.
    :return: Normalized URL lines that begin with HTTP or HTTPS after trimming.
    """

    source_content = source_path.read_text(encoding="utf-8")  # Read the complete source file as UTF-8 text.
    normalized_lines = [line.strip() for line in source_content.splitlines()]  # Trim surrounding whitespace from every line.
    urls = [line for line in normalized_lines if line.startswith(("https://", "http://"))]  # Retain only HTTP and HTTPS URL lines.
    urls = [urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")) for parsed in (urlsplit(url) for url in urls)]  # Remove query strings and fragments before duplicate detection.

    return urls  # Return retained normalized URLs.


def remove_duplicate_urls(urls: List[str]) -> Tuple[List[str], int]:  # Remove duplicate normalized URL entries while preserving first occurrence order.
    """
    Remove duplicate URLs after normalization.

    :param urls: Normalized URL entries.
    :return: Unique URLs and duplicate count removed.
    """

    unique_urls: List[str] = []  # Store first occurrences in source order.
    seen_urls = set()  # Track normalized URLs already retained.

    for url in urls:  # Traverse every normalized URL entry.
        if url in seen_urls:  # Detect a duplicate normalized URL.
            continue  # Skip duplicate occurrences.

        seen_urls.add(url)  # Record the first occurrence.
        unique_urls.append(url)  # Preserve the first occurrence for downstream sorting.

    duplicate_count = len(urls) - len(unique_urls)  # Calculate how many duplicate entries were removed.

    return unique_urls, duplicate_count  # Return unique URLs and removal count.


def detect_platform_domain(url: str) -> str:  # Detect the normalized domain/platform label from a URL.
    """
    Detect the platform domain from a URL.

    :param url: Normalized URL entry.
    :return: Lowercase hostname without a leading www. prefix, or unknown.
    """

    hostname = (urlsplit(url).hostname or "").lower().strip()  # Parse and normalize hostname from the URL.

    if hostname.startswith("www."):  # Normalize common presentation-only www prefix.
        hostname = hostname[4:]  # Remove the leading www prefix.

    return hostname or "unknown"  # Return a stable fallback when parsing produces no hostname.


def count_urls_by_platform(urls: List[str]) -> Counter:  # Count retained URLs by detected platform domain.
    """
    Count URLs per detected platform domain.

    :param urls: Unique normalized URL entries.
    :return: Counter keyed by detected platform domain.
    """

    platform_counts = Counter(detect_platform_domain(url) for url in urls)  # Dynamically count URLs per domain.

    return platform_counts  # Return platform counts for logging.


def group_urls_by_platform(urls: List[str]) -> Dict[str, List[str]]:  # Group URLs by detected platform domain without changing URL values.
    """
    Group URLs by detected platform domain.

    :param urls: Unique normalized URL entries.
    :return: Dictionary keyed by detected platform domain.
    """

    grouped_urls: Dict[str, List[str]] = {}  # Store URL lists by detected platform domain.

    for url in urls:  # Traverse every URL selected for weekly output.
        platform_domain = detect_platform_domain(url)  # Detect the platform domain consistently with platform counting.
        grouped_urls.setdefault(platform_domain, []).append(url)  # Append the unchanged URL to its platform group.

    return grouped_urls  # Return grouped URL entries.


def distribute_platform_urls_across_week(urls: List[str]) -> List[List[str]]:  # Distribute one sorted platform URL list across weekdays.
    """
    Distribute one platform's sorted URLs across the seven configured weekdays.

    :param urls: Sorted URLs for one platform.
    :return: Seven URL chunks in weekday order.
    """

    base_count = len(urls) // len(WEEKDAY_LABELS)  # Calculate the same base count for every weekday.
    remainder = len(urls) % len(WEEKDAY_LABELS)  # Calculate the remainder that must go entirely to Sunday.
    distributed_urls: List[List[str]] = []  # Store seven weekday chunks.
    cursor = 0  # Track the next URL index to consume.

    for weekday_index, _ in enumerate(WEEKDAY_LABELS):  # Build chunks in exact weekday order.
        day_count = base_count + (remainder if weekday_index == len(WEEKDAY_LABELS) - 1 else 0)  # Put all remainder URLs on Sunday.
        next_cursor = cursor + day_count  # Calculate the end index for this weekday chunk.
        distributed_urls.append(urls[cursor:next_cursor])  # Preserve sorted sequence inside the assigned chunk.
        cursor = next_cursor  # Advance to the next unassigned URL.

    assert sum(len(day_urls) for day_urls in distributed_urls) == len(urls)  # Ensure no platform URL is lost or duplicated.

    return distributed_urls  # Return seven weekday chunks for one platform.


def build_weekly_url_distribution(urls: List[str]) -> Tuple[List[List[str]], Dict[str, List[int]]]:  # Build the full weekly distribution across all platforms.
    """
    Build weekday URL lists by independently distributing each sorted platform.

    :param urls: Unique normalized URL entries selected for weekly output.
    :return: Weekday URL lists and per-platform weekday counts.
    """

    grouped_urls = group_urls_by_platform(urls)  # Group URLs by detected platform domain before sorting or distribution.
    weekly_urls: List[List[str]] = [[] for _ in WEEKDAY_LABELS]  # Store final weekday URL lists.
    platform_distributions: Dict[str, List[int]] = {}  # Store per-platform Monday-Sunday counts for reporting.

    for platform_domain in sorted(grouped_urls):  # Process platforms in deterministic alphabetical order.
        platform_urls = sort_urls(grouped_urls[platform_domain])  # Sort URLs within this platform only.
        distributed_platform_urls = distribute_platform_urls_across_week(platform_urls)  # Distribute this platform independently.
        platform_distributions[platform_domain] = [len(day_urls) for day_urls in distributed_platform_urls]  # Store weekday counts for this platform.

        for weekday_index, day_urls in enumerate(distributed_platform_urls):  # Merge platform chunks into the final weekday lists.
            weekly_urls[weekday_index].extend(day_urls)  # Preserve platform order inside each weekday without adding headings.

    source_url_count = len(urls)  # Store expected total URL count.
    output_url_count = sum(len(day_urls) for day_urls in weekly_urls)  # Count URLs assigned to the weekly output.
    assert output_url_count == source_url_count  # Ensure the complete weekly output contains every selected URL exactly once.
    assert len({url for day_urls in weekly_urls for url in day_urls}) == source_url_count  # Ensure distribution did not duplicate URLs.

    return weekly_urls, platform_distributions  # Return rendered distribution data and per-platform counts.


def build_weekly_urls_content(weekly_urls: List[List[str]]) -> str:  # Build the exact Google Keep note text.
    """
    Build the weekly URL output text using the required Google Keep structure.

    :param weekly_urls: Seven weekday URL lists in configured weekday order.
    :return: Complete UTF-8 text content ending with exactly one newline.
    """

    assert len(weekly_urls) == len(WEEKDAY_LABELS)  # Ensure a complete seven-day distribution is provided.
    lines: List[str] = ["- Links da Semana:"]  # Start with the exact required root heading.

    for weekday_index, weekday_label in enumerate(WEEKDAY_LABELS):  # Render every weekday section in exact order.
        lines.append(f"-- {weekday_label}:")  # Add the exact weekday heading.
        lines.extend(weekly_urls[weekday_index])  # Add one unchanged URL per line directly below the heading.

        if weekday_index != len(WEEKDAY_LABELS) - 1:  # Add exactly one blank line between weekday sections.
            lines.append("")  # Insert the required inter-section blank line.

    return "\n".join(lines) + "\n"  # Return content with exactly one final newline.


def resolve_weekly_urls_output_path(source_path: Path) -> Path:  # Resolve weekly output path beside the selected input file.
    """
    Resolve the weekly URL output path beside the selected input file.

    :param source_path: Selected source URL input file.
    :return: Weekly_Urls_Sorted.txt path in the same directory.
    """

    return source_path.parent / WEEKLY_URLS_FILENAME  # Return the required sibling output path.


def write_weekly_urls_file(output_path: Path, content: str) -> None:  # Write the weekly URL file safely using the existing staged replace helper.
    """
    Write the weekly URL output file as UTF-8 text.

    :param output_path: Destination path for Weekly_Urls_Sorted.txt.
    :param content: Complete weekly output text.
    :return: None.
    """

    expected_bytes = content.encode("utf-8")  # Encode the weekly note content as UTF-8.
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the selected input directory exists.
    staged_path = stage_file_content(output_path, expected_bytes)  # Stage content beside the final destination.

    try:  # Replace the weekly output file atomically.
        os.replace(staged_path, output_path)  # Publish the staged weekly output.
    except Exception:  # Clean up the staged file if replacement fails.
        if staged_path.exists():  # Verify whether the staged file still exists.
            staged_path.unlink()  # Remove the unpublished staged output.

        raise  # Preserve the original replacement failure.

    if output_path.read_bytes() != expected_bytes:  # Verify byte-for-byte weekly output content.
        raise RuntimeError(f'Weekly URL output verification failed for "{output_path}".')  # Reject corrupted weekly output writes.


def natural_sort_key(url: str) -> Tuple[Tuple[Tuple[int, Union[int, str]], ...], str, str]:  # Build a deterministic case-insensitive natural sorting key.
    """
    Build a deterministic case-insensitive natural sorting key for a URL.

    :param url: URL to convert into sortable components.
    :return: Natural components followed by deterministic secondary keys.
    """

    components = re.split(r"(\d+)", url)  # Split the URL around every numeric group.
    natural_components = tuple(
        (0, int(component)) if component.isdigit() else (1, component.casefold())
        for component in components
    )  # Convert numeric groups to integers and text groups to folded text.

    return natural_components, url.casefold(), url  # Return natural and deterministic secondary keys.


def sort_urls(urls: List[str]) -> List[str]:  # Sort URLs with deterministic case-insensitive natural ordering.
    """
    Sort URL occurrences using deterministic case-insensitive natural ordering.

    :param urls: Unique URL entries to sort.
    :return: New naturally sorted URL list.
    """

    sorted_urls = sorted(urls, key=natural_sort_key)  # Sort URL entries after duplicate removal.

    return sorted_urls  # Return the naturally sorted URL list.


def stage_file_content(output_path: Path, content: bytes) -> Path:  # Write complete bytes to a staged file beside its destination.
    """
    Write bytes to a synchronized staged file beside an output path.

    :param output_path: Final destination associated with the staged file.
    :param content: Complete byte content to stage.
    :return: Path to the fully written staged file.
    """

    temporary_path: Optional[Path] = None  # Track the staged path for failure cleanup.

    try:  # Remove an incomplete staged file after any write failure.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(output_path.parent),
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:  # Open a destination-local staged binary file.
            temporary_path = Path(temporary_file.name)  # Capture the staged file path.
            temporary_file.write(content)  # Write the complete staged content.
            temporary_file.flush()  # Flush Python's buffered text content.
            os.fsync(temporary_file.fileno())  # Synchronize staged content to storage.

        if temporary_path is None:  # Verify that the staged path was captured.
            raise RuntimeError(f'Unable to capture staged output path for "{output_path}".')  # Reject an unavailable staged path.

        return temporary_path  # Return the complete staged file path.
    except Exception:  # Remove any staged artifact before preserving the failure.
        if temporary_path is not None and temporary_path.exists():  # Verify whether a staged artifact requires cleanup.
            temporary_path.unlink()  # Remove the incomplete staged file.

        raise  # Re-raise the original staging failure.


def restore_output_file(output_path: Path, original_content: Optional[bytes]) -> None:  # Restore or remove one output after a failed multi-file replacement.
    """
    Restore one output file to its content before replacement.

    :param output_path: Output path requiring restoration.
    :param original_content: Previous byte content, or None when no file existed.
    :return: None.
    """

    if original_content is None:  # Verify whether the output was newly created.
        if output_path.exists():  # Verify whether the new output requires removal.
            output_path.unlink()  # Remove the newly created output.

        return  # Complete restoration for a previously absent output.

    staged_path = stage_file_content(output_path, original_content)  # Stage the previous output content.

    try:  # Replace the changed output with its previous content.
        os.replace(staged_path, output_path)  # Restore the previous output atomically.
    except Exception:  # Remove the restoration stage after a failed replacement.
        if staged_path.exists():  # Verify whether the restoration stage remains.
            staged_path.unlink()  # Remove the unused restoration stage.

        raise  # Re-raise the restoration failure.


def write_normalized_urls(output_paths: Tuple[Path, Path], urls: List[str]) -> None:  # Write identical normalized content to both required output files.
    """
    Write identical normalized URL content to both required output files.

    :param output_paths: Canonical and backup output paths.
    :param urls: Sorted URL occurrences to write.
    :return: None.
    """

    normalized_content = "\n".join(urls) + "\n"  # Build one URL per line with one final newline.
    expected_bytes = normalized_content.encode("utf-8")  # Encode the exact normalized output bytes.
    original_contents: Dict[Path, Optional[bytes]] = {}  # Store existing output bytes for rollback.
    staged_paths: Dict[Path, Path] = {}  # Store complete staged replacements.
    replaced_paths: List[Path] = []  # Track outputs replaced before a possible failure.

    try:  # Roll back every changed output after any write or verification failure.
        for output_path in output_paths:  # Prepare both outputs before replacing either destination.
            original_contents[output_path] = output_path.read_bytes() if output_path.is_file() else None  # Capture the previous output bytes.
            staged_paths[output_path] = stage_file_content(output_path, expected_bytes)  # Stage the complete normalized output.

        for output_path in output_paths:  # Replace each output only after both stages succeed.
            os.replace(staged_paths[output_path], output_path)  # Publish the staged output atomically.
            replaced_paths.append(output_path)  # Record the published output for rollback.

        for output_path in output_paths:  # Verify both published outputs before reporting success.
            if output_path.read_bytes() != expected_bytes:  # Verify byte-for-byte output content.
                raise RuntimeError(f'Normalized URL output verification failed for "{output_path}".')  # Reject incomplete or changed output content.
    except Exception as error:  # Restore prior outputs and preserve the original failure.
        rollback_failures: List[str] = []  # Collect any rollback failures for diagnostics.

        for staged_path in staged_paths.values():  # Remove every unpublished staged file.
            if staged_path.exists():  # Verify whether the staged file remains.
                staged_path.unlink()  # Remove the unpublished staged file.

        for output_path in reversed(replaced_paths):  # Restore published outputs in reverse order.
            try:  # Attempt to restore the previous output state.
                restore_output_file(output_path, original_contents[output_path])  # Restore or remove the changed output.
            except Exception as rollback_error:  # Preserve details for an incomplete rollback.
                rollback_failures.append(f'"{output_path}": {rollback_error}')  # Record the output-specific rollback failure.

        if rollback_failures:  # Verify whether rollback completed successfully.
            raise RuntimeError(  # Raise a clear combined persistence failure.
                f"URL output writing failed and rollback was incomplete: {'; '.join(rollback_failures)}"
            ) from error  # Preserve the original write failure as the cause.

        raise  # Re-raise the original write or verification failure.


def normalize_url_files() -> Tuple[Path, int, int, Counter, Dict[str, List[int]], Tuple[Path, Path], Path, bool]:  # Coordinate source resolution, normalization, sorting, and output writing.
    """
    Normalize the repository URL source into canonical and backup outputs.

    :return: Source path, retained count, duplicate count, platform counts, platform distributions, output paths, weekly output path, and source-conflict state.
    """

    script_directory = Path(__file__).resolve().parent  # Resolve paths from the executing script location.
    source_path, both_sources_exist = resolve_url_source(script_directory)  # Resolve the source with canonical precedence.
    urls = extract_valid_urls(source_path)  # Read and retain valid URL occurrences.

    if not urls:  # Verify whether the readable source contains any valid URLs.
        raise ValueError(f'URL input file "{source_path}" contains no HTTP or HTTPS URL lines.')  # Reject headings-only or URL-empty input.

    unique_urls, duplicate_count = remove_duplicate_urls(urls)  # Remove duplicate normalized URLs while preserving first occurrences.
    sorted_urls = sort_urls(unique_urls)  # Apply deterministic case-insensitive natural ordering.
    platform_counts = count_urls_by_platform(sorted_urls)  # Count retained URLs by detected platform domain.
    weekly_urls, platform_distributions = build_weekly_url_distribution(sorted_urls)  # Build the required independent weekly distribution.
    weekly_urls_content = build_weekly_urls_content(weekly_urls)  # Render the exact Google Keep note structure.
    weekly_urls_output_path = resolve_weekly_urls_output_path(source_path)  # Resolve weekly output beside the selected input file.
    output_directory = script_directory / "Inputs"  # Build the canonical output directory path.
    output_directory.mkdir(parents=True, exist_ok=True)  # Create the output directory only after successful source processing.
    output_paths = (output_directory / "urls.txt", output_directory / "urls-backup.txt")  # Build both required output paths.
    write_normalized_urls(output_paths, sorted_urls)  # Publish identical normalized content safely.
    write_weekly_urls_file(weekly_urls_output_path, weekly_urls_content)  # Publish the weekly URL output without platform headings.

    return source_path, len(sorted_urls), duplicate_count, platform_counts, platform_distributions, output_paths, weekly_urls_output_path, both_sources_exist  # Return the completed operation details.


def main() -> None:  # Execute URL normalization within the preserved template workflow.
    """
    Execute the URL normalization program workflow.

    :return: None.
    """

    print(
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}URL Input Normalizer{BackgroundColors.GREEN} Python program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the preserved welcome message.

    start_time = datetime.datetime.now()  # Capture the program start time.
    source_path, retained_count, duplicate_count, platform_counts, platform_distributions, output_paths, weekly_urls_output_path, both_sources_exist = normalize_url_files()  # Normalize and write the URL input files.

    if both_sources_exist:  # Verify whether both candidate source files were present.
        print(
            f"{BackgroundColors.YELLOW}Both URL input files exist. Using canonical source: {BackgroundColors.CYAN}{source_path}{Style.RESET_ALL}"
        )  # Report canonical source precedence.

    print(
        f"{BackgroundColors.GREEN}Input file read: {BackgroundColors.CYAN}{source_path}{Style.RESET_ALL}"
    )  # Report the selected source file.
    print(
        f"{BackgroundColors.GREEN}URL entries retained: {BackgroundColors.CYAN}{retained_count}{Style.RESET_ALL}"
    )  # Report the retained URL count.
    print(
        f"{BackgroundColors.GREEN}Duplicate URL entries removed: {BackgroundColors.CYAN}{duplicate_count}{Style.RESET_ALL}"
    )  # Report the duplicate removal count.
    print(
        f"{BackgroundColors.GREEN}URL entries per platform:{Style.RESET_ALL}"
    )  # Report the platform-count section header.

    for platform_domain, url_count in sorted(platform_counts.items()):  # Output platform counts deterministically.
        print(
            f"{BackgroundColors.GREEN}- {BackgroundColors.CYAN}{platform_domain}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{url_count}{Style.RESET_ALL}"
        )  # Report one detected platform/domain count.

    print(
        f"{BackgroundColors.GREEN}Weekly distribution per platform:{Style.RESET_ALL}"
    )  # Report the platform distribution section header.

    for platform_domain, weekday_counts in sorted(platform_distributions.items()):  # Output per-platform weekday counts deterministically.
        formatted_counts = ", ".join(f"{weekday}: {count}" for weekday, count in zip(WEEKDAY_LABELS, weekday_counts))  # Build the Monday-Sunday distribution summary.
        print(
            f"{BackgroundColors.GREEN}- {BackgroundColors.CYAN}{platform_domain}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{formatted_counts}{Style.RESET_ALL}"
        )  # Report one platform's weekly distribution.

    print(
        f"{BackgroundColors.GREEN}Output files written:\n{BackgroundColors.CYAN}{output_paths[0]}\n{output_paths[1]}{Style.RESET_ALL}"
    )  # Report both successfully written output files.
    print(
        f"{BackgroundColors.GREEN}Weekly URL output written: {BackgroundColors.CYAN}{weekly_urls_output_path}{Style.RESET_ALL}"
    )  # Report the weekly URL output path.

    finish_time = datetime.datetime.now()  # Capture the program finish time.

    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the preserved execution timing report.

    print(
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )  # Output the preserved completion message.

    (
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None
    )  # Preserve completion sound registration order and behavior.


if __name__ == "__main__":  # Execute the production entry point only when run as a script.
    main()  # Call the main function.
