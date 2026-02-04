"""
================================================================================
E-Commerces WebScraper
================================================================================
Author      : Breno Farias da Silva
Created     : <2026-03-04>
Description :
    This script is an E-Commerces WebScraper designed to scrape product information
    from popular e-commerce websites such as AliExpress, Mercado Livre, Shein, and Shopee.
    It automates the process of collecting data like product names, prices, descriptions,
    and other relevant details for analysis or monitoring purposes.

    Key features include:
        - Web scraping from multiple e-commerce platforms
        - Data extraction and preprocessing
        - Configurable input for URLs or search terms
        - Output to structured files (e.g., CSV, JSON)
        - Logging and error handling for robust operation
        - Integration with AI tools for data analysis (e.g., Gemini)

Usage:
    1. Configure the .env file with necessary API keys (e.g., GEMINI_API_KEY).
    2. Prepare input files with URLs or search terms in the ./Inputs/ directory.
    3. Run the script via Makefile or Python:
            $ make run   or   $ python main.py
    4. Check outputs in the ./Outputs/ directory for scraped data.

Outputs:
    - Scraped data files (e.g., products.csv, output.txt)
    - Logs in ./Logs/ for execution details
    - Optional AI analysis results

TODOs:
    - Implement scraping for additional websites
    - Add proxy support for rate limiting
    - Enhance data validation and cleaning
    - Integrate with databases for data storage
    - Add CLI argument parsing for flexibility

Dependencies:
    - Python >= 3.8
    - requests, beautifulsoup4 for web scraping
    - pandas for data handling
    - colorama for terminal coloring
    - python-dotenv for environment variables
    - google-generativeai for AI integration

Assumptions & Notes:
    - Websites' structures may change; updates may be needed for scraping logic
    - Respect robots.txt and terms of service for ethical scraping
    - API keys are required for AI features
    - Sound notifications are disabled on Windows
    - Outputs are reusable for further analysis
"""

import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import sys  # For system-specific parameters and functions
# from AliExpress import AliExpress  # Import the AliExpress class
from colorama import Style  # For coloring the terminal
from dotenv import load_dotenv  # For loading environment variables
from Gemini import Gemini  # Import the Gemini class
from Logger import Logger  # For logging output to both terminal and file
from MercadoLivre import MercadoLivre  # Import the MercadoLivre class
# from Shein import Shein  # Import the Shein class
# from Shopee import Shopee  # Import the Shopee class
from pathlib import Path  # For handling file paths


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

TEST_URLs = ["https://mercadolivre.com/sec/2XY9zrA"]  # Test URLs for scraping

PLATFORMS_MAP = {
    "AliExpress": "aliexpress",
    "MercadoLivre": "mercadolivre",
    "Shein": "shein",
    "Shopee": "shopee",
}  # Mapping of platform names to identifiers
    

# File Path Constants:
INPUT_DIRECTORY = "./Inputs/"  # The path to the input directory
INPUT_FILE = f"{INPUT_DIRECTORY}urls.txt"  # The path to the input file
OUTPUT_DIRECTORY = "./Outputs/"  # The path to the output directory
OUTPUT_FILE = f"{OUTPUT_DIRECTORY}output.txt"  # The path to the output file

# Environment Variables:
ENV_PATH = "./.env"  # The path to the .env file
ENV_VARIABLES = {
    "GEMINI": "GEMINI_API_KEY"
}  # The environment variables to load from the .env file


# Logger Setup:
logger = Logger(f"./Logs/{Path(__file__).stem}.log", clean=True)  # Create a Logger instance
sys.stdout = logger  # Redirect stdout to the logger
sys.stderr = logger  # Redirect stderr to the logger

# Sound Constants:
SOUND_COMMANDS = {
    "Darwin": "afplay",
    "Linux": "aplay",
    "Windows": "start",
}  # The commands to play a sound for each operating system
SOUND_FILE = "./.assets/Sounds/NotificationSound.wav"  # The path to the sound file

# RUN_FUNCTIONS:
RUN_FUNCTIONS = {
    "Play Sound": True,  # Set to True to play a sound when the program finishes
}

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


def verify_filepath_exists(filepath):
    """
    Verify if a file or folder exists at the specified path.

    :param filepath: Path to the file or folder
    :return: True if the file or folder exists, False otherwise
    """

    verbose_output(
        f"{BackgroundColors.GREEN}Verifying if the file or folder exists at the path: {BackgroundColors.CYAN}{filepath}{Style.RESET_ALL}"
    )  # Output the verbose message

    return os.path.exists(filepath)  # Return True if the file or folder exists, False otherwise


def verify_dot_env_file():
    """
    Verifies if the .env file exists in the current directory.

    :return: True if the .env file exists, False otherwise
    """
    
    verbose_output(
        f"{BackgroundColors.GREEN}Verifying if the {BackgroundColors.CYAN}.env{BackgroundColors.GREEN} file exists...{Style.RESET_ALL}"
    )  # Output the verbose message

    env_path = Path(__file__).parent / ".env"  # Path to the .env file
    
    if not verify_filepath_exists(env_path):  # If the .env file does not exist
        print(f"{BackgroundColors.CYAN}.env{BackgroundColors.YELLOW} file not found at {BackgroundColors.CYAN}{env_path}{BackgroundColors.YELLOW}.{Style.RESET_ALL}")
        return False  # Return False

    return True  # Return True if the .env file exists


def verify_env_variables():
    """
    Verifies if the required environment variables are set in the .env file.

    :return: True if all required environment variables are set, False otherwise
    """

    missing_variables = []  # List to store missing environment variables

    for ref_name, env_var in ENV_VARIABLES.items():  # ENV_VARIABLES = {"REFERENCE_NAME": "ENV_VAR_NAME"}
        if os.getenv(env_var) is None:  # If the environment variable is not set
            missing_variables.append(f"{ref_name} ({env_var})")  # Add the missing variable to the list

    if missing_variables:  # If there are any missing variables
        print(
            f"{BackgroundColors.YELLOW}The following environment variables are missing from the .env file: "
            f"{BackgroundColors.CYAN}{', '.join(missing_variables)}{Style.RESET_ALL}"
        )
        return False  # Return False if any required environment variable is missing

    return True  # Return True if all required environment variables are set


def create_directory(full_directory_name, relative_directory_name):
    """
    Creates a directory.

    :param full_directory_name: Name of the directory to be created.
    :param relative_directory_name: Relative name of the directory to be created that will be shown in the terminal.
    :return: None
    """

    verbose_output(
        true_string=f"{BackgroundColors.GREEN}Creating the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory...{Style.RESET_ALL}"
    )

    if os.path.isdir(full_directory_name):  # Verify if the directory already exists
        return  # Return if the directory already exists
    try:  # Try to create the directory
        os.makedirs(full_directory_name)  # Create the directory
    except OSError:  # If the directory cannot be created
        print(
            f"{BackgroundColors.GREEN}The creation of the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory failed.{Style.RESET_ALL}"
        )


def sanitize_filename(filename):
    """
    Sanitizes a filename by removing invalid characters for filesystem compatibility.
    
    :param filename: The filename string to sanitize
    :return: Sanitized filename string containing only alphanumeric characters, spaces, hyphens, and underscores
    """
    
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in filename).strip()  # Remove invalid characters


def to_seconds(obj):
    """
    Converts various time-like objects to seconds.
    
    :param obj: The object to convert (can be int, float, timedelta, datetime, etc.)
    :return: The equivalent time in seconds as a float, or None if conversion fails
    """
    
    if obj is None:  # None can't be converted
        return None  # Signal failure to convert
    if isinstance(obj, (int, float)):  # Already numeric (seconds or timestamp)
        return float(obj)  # Return as float seconds
    if hasattr(obj, "total_seconds"):  # Timedelta-like objects
        try:  # Attempt to call total_seconds()
            return float(obj.total_seconds())  # Use the total_seconds() method
        except Exception:
            pass  # Fallthrough on error
    if hasattr(obj, "timestamp"):  # Datetime-like objects
        try:  # Attempt to call timestamp()
            return float(obj.timestamp())  # Use timestamp() to get seconds since epoch
        except Exception:
            pass  # Fallthrough on error
    return None  # Couldn't convert


def calculate_execution_time(start_time, finish_time=None):
    """
    Calculates the execution time and returns a human-readable string.

    Accepts either:
    - Two datetimes/timedeltas: `calculate_execution_time(start, finish)`
    - A single timedelta or numeric seconds: `calculate_execution_time(delta)`
    - Two numeric timestamps (seconds): `calculate_execution_time(start_s, finish_s)`

    Returns a string like "1h 2m 3s".
    """

    if finish_time is None:  # Single-argument mode: start_time already represents duration or seconds
        total_seconds = to_seconds(start_time)  # Try to convert provided value to seconds
        if total_seconds is None:  # Conversion failed
            try:  # Attempt numeric coercion
                total_seconds = float(start_time)  # Attempt numeric coercion
            except Exception:
                total_seconds = 0.0  # Fallback to zero
    else:  # Two-argument mode: Compute difference finish_time - start_time
        st = to_seconds(start_time)  # Convert start to seconds if possible
        ft = to_seconds(finish_time)  # Convert finish to seconds if possible
        if st is not None and ft is not None:  # Both converted successfully
            total_seconds = ft - st  # Direct numeric subtraction
        else:  # Fallback to other methods
            try:  # Attempt to subtract (works for datetimes/timedeltas)
                delta = finish_time - start_time  # Try subtracting (works for datetimes/timedeltas)
                total_seconds = float(delta.total_seconds())  # Get seconds from the resulting timedelta
            except Exception:  # Subtraction failed
                try:  # Final attempt: Numeric coercion
                    total_seconds = float(finish_time) - float(start_time)  # Final numeric coercion attempt
                except Exception:  # Numeric coercion failed
                    total_seconds = 0.0  # Fallback to zero on failure

    if total_seconds is None:  # Ensure a numeric value
        total_seconds = 0.0  # Default to zero
    if total_seconds < 0:  # Normalize negative durations
        total_seconds = abs(total_seconds)  # Use absolute value

    days = int(total_seconds // 86400)  # Compute full days
    hours = int((total_seconds % 86400) // 3600)  # Compute remaining hours
    minutes = int((total_seconds % 3600) // 60)  # Compute remaining minutes
    seconds = int(total_seconds % 60)  # Compute remaining seconds

    if days > 0:  # Include days when present
        return f"{days}d {hours}h {minutes}m {seconds}s"  # Return formatted days+hours+minutes+seconds
    if hours > 0:  # Include hours when present
        return f"{hours}h {minutes}m {seconds}s"  # Return formatted hours+minutes+seconds
    if minutes > 0:  # Include minutes when present
        return f"{minutes}m {seconds}s"  # Return formatted minutes+seconds
    return f"{seconds}s"  # Fallback: only seconds


def play_sound():
    """
    Plays a sound when the program finishes and skips if the operating system is Windows.

    :param: None
    :return: None
    """

    current_os = platform.system()  # Get the current operating system
    if current_os == "Windows":  # If the current operating system is Windows
        return  # Do nothing

    if verify_filepath_exists(SOUND_FILE):  # If the sound file exists
        if current_os in SOUND_COMMANDS:  # If the platform.system() is in the SOUND_COMMANDS dictionary
            os.system(f"{SOUND_COMMANDS[current_os]} {SOUND_FILE}")  # Play the sound
        else:  # If the platform.system() is not in the SOUND_COMMANDS dictionary
            print(
                f"{BackgroundColors.RED}The {BackgroundColors.CYAN}{current_os}{BackgroundColors.RED} is not in the {BackgroundColors.CYAN}SOUND_COMMANDS dictionary{BackgroundColors.RED}. Please add it!{Style.RESET_ALL}"
            )
    else:  # If the sound file does not exist
        print(
            f"{BackgroundColors.RED}Sound file {BackgroundColors.CYAN}{SOUND_FILE}{BackgroundColors.RED} not found. Make sure the file exists.{Style.RESET_ALL}"
        )


def main():
    """
    Main function.

    :param: None
    :return: None
    """

    print(
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}E-Commerces WebScraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program
    
    verify_dot_env_file()  # Verify if the .env file exists
    
    create_directory(
        os.path.abspath(INPUT_DIRECTORY), INPUT_DIRECTORY.replace(".", "")
    )  # Create the input directory
    
    create_directory(
        os.path.abspath(OUTPUT_DIRECTORY), OUTPUT_DIRECTORY.replace(".", "")
    )  # Create the output directory
    
    verify_filepath_exists(INPUT_FILE)  # Verify if the input file exists

    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the start and finish times
    print(
        f"\n{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )  # Output the end of the program message

    (
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None
    )  # Register the play_sound function to be called when the program finishes


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
