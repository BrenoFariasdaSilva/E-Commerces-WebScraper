"""
================================================================================
Weekly Posts Distribution
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-06-18
Description :
    Merge timestamped output directories into a weekly distribution structure
    grouped by platform and spread across weekday directories.

    Key features include:
        - Timestamp directory detection using the existing output naming format
        - Duplicate directory resolution by structure, file count, and size
        - Platform and title directory normalization before distribution
        - Weekday distribution with remaining items assigned to Sunday
        - Two-digit indexing for child directories inside each weekday folder

Usage:
    1. Keep the default output path configured in the constants below.
    2. Execute the script directly with Python.
        $ python weekly_posts.py
    3. Review distributed folders in the configured Outputs directory.

Outputs:
    - Outputs/To-Distribute
    - Outputs/Next-Week or Outputs/Next-Week-N
    - Outputs/<weekday name> (<post count>)

TODOs:
    - None.

Dependencies:
    - Python >= 3.10
    - colorama

Assumptions & Notes:
    - The default Outputs directory is the canonical target for this project.
    - Files and directories not matched by the workflow remain untouched unless
      the existing merge rules move them from timestamp directories.
"""


from __future__ import annotations  # Enable postponed annotation evaluation.

import atexit  # Register a finish action.
import datetime  # Capture program timing.
import os  # Run operating system commands.
import platform  # Detect the operating system.
import re  # Match directory naming patterns.
import shutil  # Move and remove directories.
import sys  # Redirect standard streams.
from collections import defaultdict  # Group post directories by platform.
from pathlib import Path  # Handle filesystem paths.
from typing import Any  # Import Any for flexible timing values.
from colorama import Style  # Reset terminal colors
from Logger import Logger  # Log output to terminal and file.


class BackgroundColors:  # Define terminal color constants.
    CYAN = "\033[96m"  # Set cyan color.
    GREEN = "\033[92m"  # Set green color.
    YELLOW = "\033[93m"  # Set yellow color.
    RED = "\033[91m"  # Set red color.
    BOLD = "\033[1m"  # Set bold style.
    UNDERLINE = "\033[4m"  # Set underline style.
    CLEAR_TERMINAL = "\033[H\033[J"  # Clear the terminal.


VERBOSE = False  # Set verbose output off by default.

logger = Logger(f"./Logs/{Path(__file__).stem}.log", clean=True)  # Create a Logger instance.
sys.stdout = logger  # Redirect stdout to the logger.
sys.stderr = logger  # Redirect stderr to the logger.

SOUND_COMMANDS = {  # Define sound commands by operating system.
    "Darwin": "afplay",  # Set macOS sound command.
    "Linux": "aplay",  # Set Linux sound command.
    "Windows": "start",  # Set Windows sound command.
}  # Close sound command mapping.
SOUND_FILE = "./.assets/Sounds/NotificationSound.wav"  # Set the notification sound path.

RUN_FUNCTIONS = {  # Configure optional finish actions.
    "Play Sound": True,  # Enable finish sound registration.
}  # Close optional finish actions.

OUTPUTS_DIR = Path(r"D:\Backup\GitHub\Public\E-Commerces-WebScraper\Outputs")  # Set the default outputs directory.
TO_DISTRIBUTE_DIR = OUTPUTS_DIR / "To-Distribute"  # Set the staging distribution directory.
TIMESTAMP_DIR_PATTERN = re.compile(r"^\d+\.\s\d{4}-\d{2}-\d{2}\s-\s\d{2}h\d{2}m\d{2}s$")  # Match timestamp directory names.
POST_DIR_PATTERN = re.compile(r"^(\d+)\.\s(.+?)\s-\s(.+)$")  # Match indexed post directory names.
CHILD_INDEX_PATTERN = re.compile(r"^\d+\.\s(.+)$")  # Match indexed weekday child directory names.
TEMP_INDEX_PREFIX = ".weekly-posts-indexing-"  # Set temporary indexing prefix.
WEEKDAYS = [  # Define weekday directory names.
    "1. Monday",  # Set Monday directory name.
    "2. Tuesday",  # Set Tuesday directory name.
    "3. Wednesday",  # Set Wednesday directory name.
    "4. Thursday",  # Set Thursday directory name.
    "5. Friday",  # Set Friday directory name.
    "6. Saturday",  # Set Saturday directory name.
    "7. Sunday",  # Set Sunday directory name.
]  # Close weekday directory names.


# Functions Definitions:


def resolve_entry_with_trailing_space(current_path: str, entry: str, stripped_part: str) -> str:  # Resolve one path segment.
    """
    Resolve and optionally rename a directory entry with trailing spaces.

    :param current_path: Current directory path.
    :param entry: Directory entry name.
    :param stripped_part: Normalized target name without surrounding spaces.
    :return: Resolved path after optional rename.
    """

    try:  # Wrap resolution to keep sound lookup stable.
        resolved = os.path.join(current_path, entry)  # Build resolved path.

        if entry != stripped_part:  # Detect surrounding spaces in the entry.
            corrected = os.path.join(current_path, stripped_part)  # Build corrected path.
            try:  # Attempt entry rename.
                os.rename(resolved, corrected)  # Rename entry to stripped version.
                verbose_output(true_string=f"{BackgroundColors.GREEN}Renamed: {BackgroundColors.CYAN}{resolved}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{corrected}{Style.RESET_ALL}")  # Log rename.
                resolved = corrected  # Update resolved path after rename.
            except Exception:  # Handle rename failure.
                verbose_output(true_string=f"{BackgroundColors.RED}Failed to rename: {BackgroundColors.CYAN}{resolved}{Style.RESET_ALL}")  # Log failure.

        return resolved  # Return resolved path.
    except Exception:  # Handle unexpected resolution errors.
        return os.path.join(current_path, entry)  # Return fallback path.


def resolve_full_trailing_space_path(filepath: str) -> str:  # Resolve trailing spaces across a path.
    """
    Resolve trailing space issues across all path components.

    :param filepath: Path to resolve potential trailing space mismatches.
    :return: Corrected full path if matches are found, otherwise original filepath.
    """

    try:  # Wrap full path resolution to keep callers stable.
        verbose_output(true_string=f"{BackgroundColors.GREEN}Resolving full trailing space path for: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}")  # Log resolution start.

        if not isinstance(filepath, str) or not filepath:  # Validate filepath input.
            verbose_output(true_string=f"{BackgroundColors.YELLOW}Invalid filepath provided, skipping existence verification.{Style.RESET_ALL}")  # Log invalid input.
            return filepath  # Return original input.

        filepath = os.path.expanduser(filepath)  # Expand user directory marker.
        parts = filepath.split(os.sep)  # Split path into components.

        if not parts:  # Detect empty path components.
            return filepath  # Return original input.

        if filepath.startswith(os.sep):  # Handle absolute path input.
            current_path = os.sep  # Start from filesystem root.
            parts = parts[1:]  # Remove the root placeholder.
        else:  # Handle relative path input.
            current_path = parts[0] if parts[0] else os.getcwd()  # Initialize base path.
            parts = parts[1:] if parts[0] else parts  # Adjust remaining parts.

        for part in parts:  # Iterate over path components.
            if part == "":  # Skip empty components.
                continue  # Continue to the next component.

            try:  # Attempt to list the current directory.
                entries = os.listdir(current_path) if os.path.isdir(current_path) else []  # Read current directory entries.
            except Exception:  # Handle listing failure.
                verbose_output(true_string=f"{BackgroundColors.RED}Failed to list directory: {BackgroundColors.CYAN}{current_path}{Style.RESET_ALL}")  # Log listing failure.
                return filepath  # Return original input.

            stripped_part = part.strip()  # Normalize current component.
            match_found = False  # Track whether a matching entry was found.

            for entry in entries:  # Iterate over current entries.
                try:  # Attempt safe comparison.
                    if entry.strip() == stripped_part:  # Compare normalized names.
                        current_path = resolve_entry_with_trailing_space(current_path, entry, stripped_part)  # Resolve matched entry.
                        match_found = True  # Mark the segment as found.
                        break  # Stop searching current entries.
                except Exception:  # Handle comparison errors.
                    continue  # Continue to the next entry.

            if not match_found:  # Detect missing segment match.
                verbose_output(true_string=f"{BackgroundColors.YELLOW}No match for segment: {BackgroundColors.CYAN}{part}{Style.RESET_ALL}")  # Log missing segment.
                return filepath  # Return original input.

        return current_path  # Return resolved path.
    except Exception:  # Handle unexpected path resolution errors.
        verbose_output(true_string=f"{BackgroundColors.RED}Error resolving full path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}")  # Log resolution error.
        return filepath  # Return original input.


def verify_filepath_exists(filepath: str) -> bool:  # Verify file or folder existence.
    """
    Verify whether a file or folder exists at the specified path.

    :param filepath: Path to the file or folder.
    :return: True if the file or folder exists, otherwise False.
    """

    try:  # Wrap existence verification for stable monitoring.
        verbose_output(f"{BackgroundColors.GREEN}Verifying if the file or folder exists at the path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}")  # Log verification start.

        if not isinstance(filepath, str) or not filepath.strip():  # Validate filepath input.
            verbose_output(true_string=f"{BackgroundColors.YELLOW}Invalid filepath provided, skipping existence verification.{Style.RESET_ALL}")  # Log invalid input.
            return False  # Return False for invalid input.

        if os.path.exists(filepath):  # Detect original path existence.
            return True  # Return True immediately.

        candidate = str(filepath).strip()  # Normalize input to string.

        if (candidate.startswith("'") and candidate.endswith("'")) or (candidate.startswith('"') and candidate.endswith('"')):  # Detect quoted paths.
            candidate = candidate[1:-1].strip()  # Remove wrapping quotes.

        candidate = os.path.expanduser(candidate)  # Expand user directory marker.
        candidate = os.path.normpath(candidate)  # Normalize path structure.

        if os.path.exists(candidate):  # Detect normalized path existence.
            return True  # Return True for normalized path.

        repo_dir = os.path.dirname(os.path.abspath(__file__))  # Resolve repository directory.
        cwd = os.getcwd()  # Capture current working directory.
        alt = candidate.lstrip(os.sep) if candidate.startswith(os.sep) else candidate  # Prepare relative-safe path.
        repo_candidate = os.path.join(repo_dir, alt)  # Build repository-relative candidate.
        cwd_candidate = os.path.join(cwd, alt)  # Build cwd-relative candidate.

        for path_variant in (repo_candidate, cwd_candidate):  # Iterate candidate paths.
            try:  # Attempt candidate normalization.
                normalized_variant = os.path.normpath(path_variant)  # Normalize candidate path.
                if os.path.exists(normalized_variant):  # Detect candidate path existence.
                    return True  # Return True for located path.
            except Exception:  # Handle candidate errors.
                continue  # Continue to the next candidate.

        try:  # Attempt absolute path fallback.
            abs_candidate = os.path.abspath(candidate)  # Build absolute candidate.
            if os.path.exists(abs_candidate):  # Detect absolute path existence.
                return True  # Return True for absolute path.
        except Exception:  # Handle absolute path errors.
            pass  # Continue to trailing-space resolution.

        for path_variant in (candidate, repo_candidate, cwd_candidate):  # Iterate trailing-space candidates.
            try:  # Attempt trailing-space resolution.
                resolved = resolve_full_trailing_space_path(path_variant)  # Resolve trailing-space path.
                if resolved != path_variant and os.path.exists(resolved):  # Detect resolved path existence.
                    verbose_output(f"{BackgroundColors.YELLOW}Resolved trailing space mismatch: {BackgroundColors.CYAN}{path_variant}{BackgroundColors.YELLOW} -> {BackgroundColors.CYAN}{resolved}{Style.RESET_ALL}")  # Log resolved path.
                    return True  # Return True for resolved path.
            except Exception:  # Handle trailing-space resolution errors.
                continue  # Continue to the next candidate.

        return False  # Return False when no path exists.
    except Exception as error:  # Report unexpected errors.
        print(str(error))  # Print error to terminal logs.
        raise  # Preserve original failure semantics.


def get_weekday_directory_with_count(weekday_path: Path) -> Path:  # Build counted weekday path.
    """
    Return the weekday directory path with its child directory count.

    :param weekday_path: Weekday directory path.
    :return: Weekday directory path with count suffix.
    """

    total_posts = sum(1 for child in weekday_path.iterdir() if child.is_dir())  # Count child directories.
    counted_path = weekday_path.parent / f"{weekday_path.name} ({total_posts})"  # Build counted path.
    return counted_path  # Return counted path.


def is_timestamp_dir(path: Path) -> bool:  # Detect timestamp directory names.
    """
    Return whether a path matches the timestamp directory format.

    :param path: Path to inspect.
    :return: True when the path is a timestamp directory.
    """

    return path.is_dir() and bool(TIMESTAMP_DIR_PATTERN.fullmatch(path.name))  # Return timestamp directory result.


def create_to_distribute_directory() -> None:  # Create staging directory.
    """
    Create the To-Distribute directory if it is missing.

    :param: None
    :return: None
    """

    TO_DISTRIBUTE_DIR.mkdir(exist_ok=True)  # Create staging directory.


def get_directory_stats(path: Path) -> tuple[int, int]:  # Calculate directory stats.
    """
    Return file count and total byte size for a directory.

    :param path: Directory path.
    :return: Tuple containing file count and total byte size.
    """

    file_count = 0  # Initialize file count.
    total_size = 0  # Initialize total size.

    for item in path.rglob("*"):  # Iterate recursively through directory contents.
        if item.is_file():  # Detect file entry.
            file_count += 1  # Increment file count.
            total_size += item.stat().st_size  # Add file size.

    return file_count, total_size  # Return directory stats.


def build_directory_signature(root: Path) -> list[tuple[str, int]]:  # Build comparable directory signature.
    """
    Build a directory signature from relative names and file sizes.

    :param root: Directory root path.
    :return: Directory signature list.
    """

    signature: list[tuple[str, int]] = []  # Initialize signature list.

    for item in sorted(root.rglob("*"), key=lambda path: str(path.relative_to(root)).lower()):  # Iterate sorted directory entries.
        relative = str(item.relative_to(root))  # Build relative path.

        if item.is_dir():  # Detect directory entry.
            signature.append((f"D:{relative}", 0))  # Add directory signature item.
        else:  # Handle file entry.
            signature.append((f"F:{relative}", item.stat().st_size))  # Add file signature item.

    return signature  # Return signature list.


def directories_are_equivalent(dir_a: Path, dir_b: Path) -> bool:  # Compare two directories.
    """
    Compare directory structure, file names, and file sizes.

    :param dir_a: First directory path.
    :param dir_b: Second directory path.
    :return: True when directories are equivalent.
    """

    return build_directory_signature(dir_a) == build_directory_signature(dir_b)  # Return comparison result.


def resolve_duplicate_directory(source: Path, destination: Path) -> None:  # Resolve duplicate directory names.
    """
    Resolve duplicate directories by equivalence, file count, and size.

    :param source: Source directory path.
    :param destination: Destination directory path.
    :return: None
    """

    if directories_are_equivalent(source, destination):  # Detect equivalent directories.
        shutil.rmtree(source)  # Remove duplicate source directory.
        return  # Stop duplicate resolution.

    source_files, source_size = get_directory_stats(source)  # Read source stats.
    dest_files, dest_size = get_directory_stats(destination)  # Read destination stats.
    keep_source = source_files > dest_files or (source_files == dest_files and source_size > dest_size)  # Determine stronger directory.

    if keep_source:  # Detect source as stronger directory.
        shutil.rmtree(destination)  # Remove destination directory.
        source.rename(destination)  # Rename source to destination.
    else:  # Keep destination directory.
        shutil.rmtree(source)  # Remove source directory.


def move_timestamp_directories() -> None:  # Move timestamp directories into staging.
    """
    Move all timestamp directories into To-Distribute and delete originals.

    :param: None
    :return: None
    """

    create_to_distribute_directory()  # Ensure staging directory exists.
    timestamp_dirs = [path for path in OUTPUTS_DIR.iterdir() if is_timestamp_dir(path)]  # Collect timestamp directories.

    for timestamp_dir in sorted(timestamp_dirs):  # Iterate timestamp directories in sorted order.
        for child in timestamp_dir.iterdir():  # Iterate timestamp directory children.
            destination = TO_DISTRIBUTE_DIR / child.name  # Build destination path.

            if destination.exists():  # Detect duplicate destination.
                resolve_duplicate_directory(source=child, destination=destination)  # Resolve duplicate destination.
            else:  # Handle new destination.
                shutil.move(str(child), str(destination))  # Move child into staging.

        shutil.rmtree(timestamp_dir)  # Remove empty timestamp directory.


def get_next_week_directory() -> Path:  # Find next available Next-Week path.
    """
    Return the first available Next-Week directory path.

    :param: None
    :return: Available Next-Week directory path.
    """

    candidate = OUTPUTS_DIR / "Next-Week"  # Build first candidate.

    if not candidate.exists():  # Detect available first candidate.
        return candidate  # Return first candidate.

    counter = 2  # Initialize suffix counter.

    while True:  # Iterate until an available candidate is found.
        candidate = OUTPUTS_DIR / f"Next-Week-{counter}"  # Build suffixed candidate.

        if not candidate.exists():  # Detect available suffixed candidate.
            return candidate  # Return suffixed candidate.

        counter += 1  # Increment suffix counter.


def remove_indexes_from_post_directories() -> None:  # Normalize post directory names.
    """
    Remove leading indexes from post directories inside To-Distribute.

    :param: None
    :return: None
    """

    for path in list(TO_DISTRIBUTE_DIR.iterdir()):  # Iterate staged entries.
        if not path.is_dir():  # Skip non-directory entries.
            continue  # Continue to next entry.

        match = POST_DIR_PATTERN.fullmatch(path.name)  # Match indexed post directory name.

        if not match:  # Skip names outside the post pattern.
            continue  # Continue to next entry.

        platform_name = match.group(2)  # Extract platform name.
        title = match.group(3)  # Extract title.
        new_name = f"{platform_name} - {title}"  # Build normalized name.
        destination = TO_DISTRIBUTE_DIR / new_name  # Build normalized destination.

        if destination.exists():  # Detect duplicate normalized destination.
            resolve_duplicate_directory(source=path, destination=destination)  # Resolve duplicate destination.
        else:  # Handle available normalized destination.
            path.rename(destination)  # Rename post directory.


def get_platform_name(directory_name: str) -> str:  # Extract platform name.
    """
    Extract the platform name from a post directory name.

    :param directory_name: Post directory name.
    :return: Platform name or an empty string.
    """

    if " - " not in directory_name:  # Detect missing platform separator.
        return ""  # Return empty platform name.

    return directory_name.split(" - ", 1)[0]  # Return platform name before separator.


def create_weekday_directories() -> dict[str, Path]:  # Create weekday directories.
    """
    Create weekday directories inside To-Distribute.

    :param: None
    :return: Mapping of weekday names to paths.
    """

    weekday_paths: dict[str, Path] = {}  # Initialize weekday path mapping.

    for weekday in WEEKDAYS:  # Iterate weekday names.
        path = TO_DISTRIBUTE_DIR / weekday  # Build weekday path.
        path.mkdir(exist_ok=True)  # Create weekday directory.
        weekday_paths[weekday] = path  # Store weekday path.

    return weekday_paths  # Return weekday paths.


def get_child_directory_name_without_index(directory_name: str) -> str:  # Remove existing child index.
    """
    Return a weekday child directory name without a leading index.

    :param directory_name: Weekday child directory name.
    :return: Directory name without a leading index.
    """

    match = CHILD_INDEX_PATTERN.fullmatch(directory_name)  # Match existing child index.

    if match:  # Detect indexed child directory name.
        return match.group(1)  # Return name without index.

    return directory_name  # Return original name.


def get_ordered_weekday_child_directories(weekday_path: Path) -> list[Path]:  # Order weekday child directories.
    """
    Return weekday child directories in deterministic normalized name order.

    :param weekday_path: Weekday directory path.
    :return: Ordered child directory paths.
    """

    child_dirs = [path for path in weekday_path.iterdir() if path.is_dir()]  # Collect child directories only.
    child_dirs.sort(key=lambda path: (get_child_directory_name_without_index(path.name).lower(), path.name.lower()))  # Sort by normalized name.
    return child_dirs  # Return ordered child directories.


def build_weekday_child_targets(child_dirs: list[Path]) -> dict[Path, Path]:  # Build final indexed targets.
    """
    Build target paths for indexed weekday child directories.

    :param child_dirs: Ordered child directory paths.
    :return: Mapping of source paths to target paths.
    """

    targets: dict[Path, Path] = {}  # Initialize target mapping.

    for index, child_dir in enumerate(child_dirs, start=1):  # Iterate child directories with one-based index.
        clean_name = get_child_directory_name_without_index(child_dir.name)  # Remove existing index from name.
        target = child_dir.parent / f"{index:02d}. {clean_name}"  # Build indexed target path.
        targets[child_dir] = target  # Store target path.

    return targets  # Return target mapping.


def verify_weekday_child_targets_available(targets: dict[Path, Path]) -> None:  # Verify indexed target availability.
    """
    Verify that indexed weekday child targets can be safely created.

    :param targets: Mapping of source paths to target paths.
    :return: None
    """

    source_paths = set(targets.keys())  # Capture source paths.
    target_paths = set(targets.values())  # Capture target paths.

    if len(target_paths) != len(targets):  # Detect duplicate target paths.
        raise FileExistsError("Duplicate target paths were generated for weekday indexing.")  # Raise duplicate target error.

    for target_path in target_paths:  # Iterate target paths.
        if target_path.exists() and target_path not in source_paths:  # Detect external path collision.
            raise FileExistsError(f"Cannot index weekday directory because target exists: {target_path}")  # Raise collision error.


def get_temporary_weekday_child_path(child_dir: Path, index: int) -> Path:  # Build temporary child path.
    """
    Return an available temporary path for a weekday child directory.

    :param child_dir: Weekday child directory path.
    :param index: Temporary index number.
    :return: Available temporary path.
    """

    attempt = 1  # Initialize attempt counter.
    temp_path = child_dir.parent / f"{TEMP_INDEX_PREFIX}{index:02d}-{child_dir.name}"  # Build first temporary path.

    while temp_path.exists():  # Detect temporary path collision.
        attempt += 1  # Increment attempt counter.
        temp_path = child_dir.parent / f"{TEMP_INDEX_PREFIX}{index:02d}-{attempt}-{child_dir.name}"  # Build next temporary path.

    return temp_path  # Return available temporary path.


def move_weekday_children_to_temporary_paths(targets: dict[Path, Path]) -> dict[Path, Path]:  # Move children to temporary paths.
    """
    Move weekday child directories to temporary paths before final indexing.

    :param targets: Mapping of source paths to target paths.
    :return: Mapping of temporary paths to final target paths.
    """

    temporary_paths: dict[Path, Path] = {}  # Initialize temporary mapping.

    for index, source_path in enumerate(targets, start=1):  # Iterate source paths.
        temporary_path = get_temporary_weekday_child_path(source_path, index)  # Build temporary path.
        source_path.rename(temporary_path)  # Rename source to temporary path.
        temporary_paths[temporary_path] = targets[source_path]  # Store final target path.

    return temporary_paths  # Return temporary mapping.


def rename_temporary_weekday_children(temporary_paths: dict[Path, Path]) -> None:  # Rename temporary children to final paths.
    """
    Rename temporary weekday child directories to final indexed paths.

    :param temporary_paths: Mapping of temporary paths to final target paths.
    :return: None
    """

    for temporary_path, target_path in temporary_paths.items():  # Iterate temporary paths.
        temporary_path.rename(target_path)  # Rename temporary path to final target.


def index_weekday_child_directories(weekday_path: Path) -> None:  # Index child directories inside one weekday.
    """
    Index child directories inside a weekday directory with two digits.

    :param weekday_path: Weekday directory path.
    :return: None
    """

    child_dirs = get_ordered_weekday_child_directories(weekday_path)  # Get ordered child directories.

    if not child_dirs:  # Detect empty weekday directory.
        return  # Stop indexing for this weekday.

    targets = build_weekday_child_targets(child_dirs)  # Build indexed targets.

    if all(source_path == target_path for source_path, target_path in targets.items()):  # Detect already normalized names.
        return  # Stop when no rename is needed.

    verify_weekday_child_targets_available(targets)  # Verify target availability.
    temporary_paths = move_weekday_children_to_temporary_paths(targets)  # Move children to temporary paths.
    rename_temporary_weekday_children(temporary_paths)  # Rename temporary paths to indexed targets.


def index_all_weekday_child_directories() -> None:  # Index children inside all weekdays.
    """
    Index child directories inside every staged weekday directory.

    :param: None
    :return: None
    """

    for weekday in WEEKDAYS:  # Iterate weekday names.
        weekday_path = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday path.

        if weekday_path.is_dir():  # Detect staged weekday directory.
            index_weekday_child_directories(weekday_path)  # Index child directories.


def distribute_platform_directories() -> None:  # Distribute post directories across weekdays.
    """
    Distribute platform directories evenly across weekdays.

    :param: None
    :return: None
    """

    weekday_paths = create_weekday_directories()  # Create weekday directories.
    platform_map: defaultdict[str, list[Path]] = defaultdict(list)  # Initialize platform mapping.
    post_dirs = [path for path in TO_DISTRIBUTE_DIR.iterdir() if path.is_dir() and path.name not in WEEKDAYS]  # Collect post directories.
    post_dirs.sort(key=lambda path: path.name.lower())  # Sort post directories case-insensitively.

    for post_dir in post_dirs:  # Iterate post directories.
        platform = get_platform_name(post_dir.name)  # Extract platform name.

        if platform:  # Detect valid platform name.
            platform_map[platform].append(post_dir)  # Store post directory by platform.

    for platform_dirs in platform_map.values():  # Iterate platform directory groups.
        total = len(platform_dirs)  # Count platform directories.
        base_amount = total // 7  # Calculate base weekday amount.
        remainder = total % 7  # Calculate Sunday remainder.
        index = 0  # Initialize platform directory index.

        for weekday_index, weekday in enumerate(WEEKDAYS):  # Iterate weekdays in configured order.
            amount = base_amount  # Set base amount for weekday.

            if weekday_index == 6:  # Detect Sunday.
                amount += remainder  # Assign remainder to Sunday.

            for _ in range(amount):  # Move configured amount for weekday.
                source = platform_dirs[index]  # Get source post directory.
                destination = weekday_paths[weekday] / source.name  # Build weekday destination.
                shutil.move(str(source), str(destination))  # Move post directory to weekday.
                index += 1  # Advance platform directory index.


def outputs_already_has_weekdays() -> bool:  # Detect existing weekday directories in Outputs.
    """
    Return whether Outputs already contains weekday directories.

    :param: None
    :return: True when Outputs contains an uncounted weekday directory.
    """

    return any((OUTPUTS_DIR / weekday).exists() for weekday in WEEKDAYS)  # Return existing weekday result.


def rename_weekday_with_count(weekday_path: Path) -> None:  # Rename weekday with child count.
    """
    Rename a weekday directory with its child directory count.

    :param weekday_path: Weekday directory path.
    :return: None
    """

    weekday_path.rename(get_weekday_directory_with_count(weekday_path))  # Rename weekday path with count.


def finalize_distribution() -> None:  # Finalize staged distribution.
    """
    Move weekday directories to Outputs unless they already exist.

    :param: None
    :return: None
    """

    index_all_weekday_child_directories()  # Index child directories inside staged weekdays.

    if outputs_already_has_weekdays():  # Detect existing weekday directories.
        target_dir = get_next_week_directory()  # Get Next-Week target directory.

        for weekday in WEEKDAYS:  # Iterate weekday names.
            weekday_path = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday path.

            if weekday_path.exists():  # Detect staged weekday path.
                rename_weekday_with_count(weekday_path)  # Rename weekday with count.

        TO_DISTRIBUTE_DIR.rename(target_dir)  # Rename staging directory to Next-Week target.
        return  # Stop finalization.

    for weekday in WEEKDAYS:  # Iterate weekday names.
        source = TO_DISTRIBUTE_DIR / weekday  # Build staged weekday source.

        if not source.exists():  # Skip missing weekday source.
            continue  # Continue to next weekday.

        rename_weekday_with_count(source)  # Rename weekday with count.

    for source in TO_DISTRIBUTE_DIR.iterdir():  # Iterate remaining staged entries.
        if not source.is_dir():  # Skip non-directory entries.
            continue  # Continue to next entry.

        destination = OUTPUTS_DIR / source.name  # Build final destination path.
        shutil.move(str(source), str(destination))  # Move directory to Outputs.

    shutil.rmtree(TO_DISTRIBUTE_DIR)  # Remove staging directory.


def run_weekly_posts_distribution() -> None:  # Run weekly post distribution workflow.
    """
    Run the weekly post distribution workflow.

    :param: None
    :return: None
    """

    move_timestamp_directories()  # Move timestamp directories into staging.

    if not TO_DISTRIBUTE_DIR.exists():  # Detect missing staging directory.
        return  # Stop workflow when staging is absent.

    remove_indexes_from_post_directories()  # Normalize post directory names.
    distribute_platform_directories()  # Distribute post directories by weekday.
    finalize_distribution()  # Finalize distribution output.


def to_seconds(obj: Any) -> float | None:  # Convert time-like values.
    """
    Convert various time-like objects to seconds.

    :param obj: Object to convert.
    :return: Equivalent time in seconds, or None when conversion fails.
    """

    if obj is None:  # Detect missing value.
        return None  # Return no conversion.

    if isinstance(obj, (int, float)):  # Detect numeric value.
        return float(obj)  # Return numeric seconds.

    if hasattr(obj, "total_seconds"):  # Detect timedelta-like object.
        try:  # Attempt timedelta conversion.
            return float(obj.total_seconds())  # Return total seconds.
        except Exception:  # Handle conversion failure.
            pass  # Continue to other conversions.

    if hasattr(obj, "timestamp"):  # Detect datetime-like object.
        try:  # Attempt timestamp conversion.
            return float(obj.timestamp())  # Return timestamp seconds.
        except Exception:  # Handle conversion failure.
            pass  # Continue to fallback.

    return None  # Return no conversion.


def calculate_execution_time(start_time: Any, finish_time: Any | None = None) -> str:  # Calculate readable duration.
    """
    Calculate execution time and return a human-readable string.

    :param start_time: Start time, duration, or numeric seconds.
    :param finish_time: Finish time or numeric seconds.
    :return: Formatted execution time.
    """

    if finish_time is None:  # Use single-argument duration mode.
        total_seconds = to_seconds(start_time)  # Convert provided duration.
        if total_seconds is None:  # Detect conversion failure.
            try:  # Attempt numeric conversion.
                total_seconds = float(start_time)  # Convert value to float.
            except Exception:  # Handle numeric conversion failure.
                total_seconds = 0.0  # Use zero fallback.
    else:  # Use start and finish mode.
        st = to_seconds(start_time)  # Convert start time.
        ft = to_seconds(finish_time)  # Convert finish time.
        if st is not None and ft is not None:  # Detect successful conversions.
            total_seconds = ft - st  # Calculate numeric difference.
        else:  # Use subtraction fallback.
            try:  # Attempt direct subtraction.
                delta = finish_time - start_time  # Calculate time delta.
                total_seconds = float(delta.total_seconds())  # Convert delta to seconds.
            except Exception:  # Handle subtraction failure.
                try:  # Attempt numeric fallback.
                    total_seconds = float(finish_time) - float(start_time)  # Calculate numeric difference.
                except Exception:  # Handle numeric fallback failure.
                    total_seconds = 0.0  # Use zero fallback.

    if total_seconds is None:  # Detect missing total seconds.
        total_seconds = 0.0  # Use zero fallback.

    if total_seconds < 0:  # Detect negative duration.
        total_seconds = abs(total_seconds)  # Normalize to positive duration.

    days = int(total_seconds // 86400)  # Calculate full days.
    hours = int((total_seconds % 86400) // 3600)  # Calculate remaining hours.
    minutes = int((total_seconds % 3600) // 60)  # Calculate remaining minutes.
    seconds = int(total_seconds % 60)  # Calculate remaining seconds.

    if days > 0:  # Detect day-level duration.
        return f"{days}d {hours}h {minutes}m {seconds}s"  # Return days format.

    if hours > 0:  # Detect hour-level duration.
        return f"{hours}h {minutes}m {seconds}s"  # Return hours format.

    if minutes > 0:  # Detect minute-level duration.
        return f"{minutes}m {seconds}s"  # Return minutes format.

    return f"{seconds}s"  # Return seconds format.


def play_sound() -> None:  # Play finish sound when available.
    """
    Play a sound when the program finishes and skip Windows.

    :param: None
    :return: None
    """

    current_os = platform.system()  # Get the current operating system.

    if current_os == "Windows":  # Detect Windows platform.
        return  # Skip sound on Windows.

    if verify_filepath_exists(SOUND_FILE):  # Verify sound file existence.
        if current_os in SOUND_COMMANDS:  # Detect supported operating system.
            os.system(f"{SOUND_COMMANDS[current_os]} {SOUND_FILE}")  # Play notification sound.
        else:  # Handle unsupported operating system.
            print(f"{BackgroundColors.RED}The {BackgroundColors.CYAN}{current_os}{BackgroundColors.RED} is not in the {BackgroundColors.CYAN}SOUND_COMMANDS dictionary{BackgroundColors.RED}. Please add it!{Style.RESET_ALL}")  # Log unsupported platform.
    else:  # Handle missing sound file.
        print(f"{BackgroundColors.RED}Sound file {BackgroundColors.CYAN}{SOUND_FILE}{BackgroundColors.RED} not found. Make sure the file exists.{Style.RESET_ALL}")  # Log missing sound file.


def main() -> None:  # Run program entrypoint.
    """
    Main function.

    :param: None
    :return: None
    """

    print(f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Weekly Posts Distribution{BackgroundColors.GREEN} program!{Style.RESET_ALL}", end="\n\n")  # Output welcome message.
    
    start_time = datetime.datetime.now()  # Get program start time.
    
    run_weekly_posts_distribution()  # Run weekly post distribution workflow.
    
    finish_time = datetime.datetime.now()  # Get program finish time.
    
    print(f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}")  # Output timing summary.
    
    print(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}")  # Output finish message.
    
    (atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None)  # Register finish sound action.


if __name__ == "__main__":  # Run script entrypoint.
    """
    This is the standard boilerplate that calls the main function.

    :return: None
    """

    main()  # Call main function.
