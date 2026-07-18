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

Dependencies:
    - Python
    - colorama

Assumptions & Notes:
    - Input is read from Inputs/urls.txt before Input/urls.txt.
    - Only trimmed HTTP and HTTPS URL lines are retained.
    - Duplicate URL occurrences are preserved.
"""

import atexit  # Register the optional completion sound.
import datetime  # Capture program start and finish times.
import os  # Access operating-system and file replacement operations.
import platform  # Identify the current operating system.
import re  # Split URLs into numeric and nonnumeric sorting components.
import tempfile  # Create staged files for atomic replacement.
from pathlib import Path  # Resolve repository-relative input and output paths.
from typing import Any, Dict, List, Optional, Tuple, Union  # Define compatible type annotations.

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
    :return: URL lines that begin with HTTP or HTTPS after trimming.
    """

    source_content = source_path.read_text(encoding="utf-8")  # Read the complete source file as UTF-8 text.
    normalized_lines = [line.strip() for line in source_content.splitlines()]  # Trim surrounding whitespace from every line.
    urls = [line for line in normalized_lines if line.startswith(("https://", "http://"))]  # Retain only HTTP and HTTPS URL lines.

    return urls  # Return retained URLs with duplicates preserved.


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

    :param urls: URL occurrences to sort.
    :return: New naturally sorted URL list.
    """

    sorted_urls = sorted(urls, key=natural_sort_key)  # Sort without removing duplicate occurrences.

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


def normalize_url_files() -> Tuple[Path, int, Tuple[Path, Path], bool]:  # Coordinate source resolution, normalization, sorting, and output writing.
    """
    Normalize the repository URL source into canonical and backup outputs.

    :return: Source path, retained count, output paths, and source-conflict state.
    """

    script_directory = Path(__file__).resolve().parent  # Resolve paths from the executing script location.
    source_path, both_sources_exist = resolve_url_source(script_directory)  # Resolve the source with canonical precedence.
    urls = extract_valid_urls(source_path)  # Read and retain valid URL occurrences.

    if not urls:  # Verify whether the readable source contains any valid URLs.
        raise ValueError(f'URL input file "{source_path}" contains no HTTP or HTTPS URL lines.')  # Reject headings-only or URL-empty input.

    sorted_urls = sort_urls(urls)  # Apply deterministic case-insensitive natural ordering.
    output_directory = script_directory / "Inputs"  # Build the canonical output directory path.
    output_directory.mkdir(parents=True, exist_ok=True)  # Create the output directory only after successful source processing.
    output_paths = (output_directory / "urls.txt", output_directory / "urls-backup.txt")  # Build both required output paths.
    write_normalized_urls(output_paths, sorted_urls)  # Publish identical normalized content safely.

    return source_path, len(sorted_urls), output_paths, both_sources_exist  # Return the completed operation details.


def main() -> None:  # Execute URL normalization within the preserved template workflow.
    """
    Execute the URL normalization program workflow.

    :return: None.
    """

    print(
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Main Template Python{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the preserved welcome message.

    start_time = datetime.datetime.now()  # Capture the program start time.
    source_path, retained_count, output_paths, both_sources_exist = normalize_url_files()  # Normalize and write the URL input files.

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
        f"{BackgroundColors.GREEN}Output files written:\n{BackgroundColors.CYAN}{output_paths[0]}\n{output_paths[1]}{Style.RESET_ALL}"
    )  # Report both successfully written output files.

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
