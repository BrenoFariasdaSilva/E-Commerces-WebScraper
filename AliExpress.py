"""
================================================================================
AliExpress Web Scraper
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-02-11
Description :
    This script provides an AliExpress class for scraping product information
    from AliExpress product pages using authenticated browser sessions. It extracts
    comprehensive product details including name, prices, discount information,
    descriptions, specifications, gallery images, review media, and page assets
    from fully rendered pages.

	Key features include:
		- Authenticated browser session using existing Chrome profile
		- Automatic product URL extraction and validation
		- Full page rendering with JavaScript execution
		- Product name and description extraction
		- Price information (current and old prices with integer and decimal parts)
		- Discount percentage extraction
		- Product images download
		- Complete page snapshot capture (HTML + localized assets)
		- Product description file generation in marketing template format
		- Organized output in product-specific directories

Usage:
	1. Import the Shopee class in your main script.
	2. Create an instance with a product URL:
		scraper = Shopee("https://shopee.com.br/product-url")
	3. Call the scrape method to extract product information:
		product_data = scraper.scrape()
	4. Media files are saved in ./Outputs/{Product Name}/ directory.

Outputs:
    - Product data dictionary with all extracted information
    - Downloaded images in ./Outputs/{Product Name}/ directory
    - Complete page snapshot in ./Outputs/{Product Name}/page.html
    - Localized assets in ./Outputs/{Product Name}/assets/ directory
    - Product description .txt file with marketing template in ./Outputs/{Product Name}/ directory
    - Log files in ./Logs/ directory

TODOs:
    - Add support for multiple product variations
    - Implement retry mechanism for failed requests
    - Add data export to CSV/JSON formats
    - Optimize asset download concurrency

Dependencies:
    - Python >= 3.8
    - playwright
    - beautifulsoup4
    - lxml
    - colorama
    - pillow

Assumptions & Notes:
    - Requires stable internet connection
    - Requires existing authenticated Chrome profile
    - Website structure may change over time
    - Respects robots.txt and ethical scraping practices
    - Creates output directories automatically if they don't exist
"""

import atexit  # Register functions to execute at program termination
import datetime  # Handle date and time operations
import os  # Interact with operating system functionalities
import platform  # Access underlying platform information
import re  # Perform regular expression operations
import shutil  # For copying files (local HTML mode)
import subprocess  # For running external commands (ffmpeg)
import sys  # Access system-specific parameters and functions
import time  # Provide time-related functions for delays
from bs4 import BeautifulSoup, Tag  # Parse and navigate HTML documents
from colorama import Style  # Colorize terminal text output
from Logger import Logger  # Custom logging functionality for output redirection
from pathlib import Path  # Handle filesystem paths in object-oriented way
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError  # Browser automation framework with timeout handling
from product_utils import normalize_product_dir_name  # Centralized product dir name normalization
from typing import Optional, Dict, Any, List, Tuple, cast  # Type hinting support for better code clarity
from urllib.parse import urljoin, urlparse  # Parse and manipulate URLs for asset collection


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

# Affiliate URL detection pattern (short shopee redirect links)  # keep generic pattern for now
AFFILIATE_URL_PATTERN = r"https?://s\.shopee\.com(?:\.br)?/[A-Za-z0-9]+"  # Keep existing affiliate pattern as fallback

# HTML Selectors Dictionary:
HTML_SELECTORS = {
    "product_name": [  # List of CSS selectors for product name in priority order
        ("h1", {"data-pl": "product-title"}),  # AliExpress product name using data-pl attribute
        ("h1", {}),  # Generic H1 heading as fallback
        ("div", {"class": re.compile(r".*product.*title.*", re.IGNORECASE)}),  # Generic product title fallback
    ],
    "current_price": [  # List of CSS selectors for current price in priority order
        ("div", {"class": "price-default--currentWrap--A_MNgCG"}),  # AliExpress current price wrapper class
        ("span", {"class": "price-default--current--F8OlYIo"}),  # AliExpress current price inner span class
        ("span", {"class": re.compile(r".*price.*", re.IGNORECASE)}),  # Generic price span fallback
    ],
    "old_price": [  # List of CSS selectors for old price in priority order
        ("span", {"class": "price-default--original--CWcHOit"}),  # AliExpress old price span class
        ("div", {"class": re.compile(r".*price.*original.*", re.IGNORECASE)}),  # Generic original price pattern fallback
        ("span", {"class": re.compile(r".*old.*price.*", re.IGNORECASE)}),  # Generic old price span fallback
    ],
    "discount": [],  # AliExpress does not provide explicit discount element, compute from prices instead
    "description": [  # List of CSS selectors for product description in priority order
        ("div", {"id": "product-description"}),  # AliExpress main product description container by id
        ("div", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Generic description fallback
    ],
    "gallery": {"class": "slider--wrap--dfLgmYD"},  # CSS selector for AliExpress product gallery container
    "detail_label": {"class": "specification--title--SfH3sA8"},  # CSS selector for specification titles used for extraction
    "specs_container": {"class": "specification--list--GZuXzRX"},  # CSS selector for specifications table container
    "specs_row": {"class": "specification--line--IXeRJI7"},  # CSS selector for each specification row
    "specs_title": {"class": "specification--title--SfH3sA8"},  # CSS selector for specification title cell
    "specs_value": {"class": "specification--desc--Dxx6W0W"},  # CSS selector for specification value cell
    "review_images_container": {"class": "filter--bottom--12yws12"},  # CSS selector for review images container
    "shipping_options": {"class": "vat-installment--item--Fgco36c"},  # CSS selector for shipping/tax notice
}  # Dictionary containing all HTML selectors used for scraping product information

# Output Directory Constants:
OUTPUT_DIRECTORY = "./Outputs/"  # Base directory for storing scraped data and media files

# Browser Constants:
CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH", "")  # Chrome user profile path from environment variable
CHROME_EXECUTABLE_PATH = os.getenv("CHROME_EXECUTABLE_PATH", "")  # Chrome executable path from environment variable
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"  # Run browser in headless mode flag from environment
PAGE_LOAD_TIMEOUT = 30000  # Maximum time in milliseconds to wait for page load
NETWORK_IDLE_TIMEOUT = 5000  # Maximum time in milliseconds to wait for network idle state
SCROLL_PAUSE_TIME = 0.5  # Pause duration in seconds between scroll steps
SCROLL_STEP = 300  # Number of pixels to scroll per step for lazy loading

# Template Constants:
PRODUCT_DESCRIPTION_TEMPLATE = """Product Name: {product_name}

Price: From R${current_price} to R${old_price} ({discount})

Description: {description}

🛒 Encontre no AliExpress:
👉 {url}"""  # Template for product description text file with placeholders for formatting

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

# Classes Definitions:


class AliExpress:  # AliExpress scraper class preserving structure and methods
    """
    A web scraper class for extracting product information from AliExpress using
    authenticated browser sessions.
    
    This class handles the extraction of product details including name, prices,
    discounts, descriptions, specifications, gallery images, and media from
    AliExpress product pages using Playwright for full page rendering and
    authenticated access.
    """


    def __init__(self, url: str, local_html_path: Optional[str] = None, prefix: str = "", output_directory: str = OUTPUT_DIRECTORY) -> None:
        """
        Initializes the Shopee scraper with a product URL and optional local HTML file path.

        :param url: The URL of the Shopee product page to scrape
        :param local_html_path: Optional path to a local HTML file for offline scraping
        :param prefix: Optional platform prefix for output directory naming (e.g., "Shopee")
        :param output_directory: Output directory path for storing scraped data (defaults to OUTPUT_DIRECTORY constant)
        :return: None
        """

        self.url: str = url  # Store the initial product URL for reference
        self.product_url: str = url  # Maintain separate copy of product URL for Shopee direct usage
        self.local_html_path: Optional[str] = local_html_path  # Store path to local HTML file for offline scraping
        self.html_content: Optional[str] = None  # Store HTML content for reuse (from browser or local file)
        self.product_data: Dict[str, Any] = {}  # Initialize empty dictionary to store extracted product data
        self.prefix: str = prefix  # Store the platform prefix for directory naming
        self.output_directory: str = output_directory  # Store the output directory path for this scraping session
        self.playwright: Optional[Any] = None  # Placeholder for Playwright instance
        self.browser: Optional[Any] = None  # Placeholder for browser instance
        self.page: Optional[Any] = None  # Placeholder for page object

        verbose_output(  # Output initialization message to user
            f"{BackgroundColors.GREEN}AliExpress scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
        )  # End of verbose output call
        if local_html_path:  # If local HTML file path is provided
            verbose_output(  # Output offline mode message
                f"{BackgroundColors.GREEN}Offline mode enabled. Will read from: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}"
            )  # End of verbose output call


    def download_media(self) -> List[str]:
        """
        Downloads product media and creates snapshot.
        Works for both online (browser) and offline (local HTML) modes.

        :return: List of downloaded file paths
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Processing product media...{Style.RESET_ALL}"
        )  # End of verbose output call

        downloaded_files: List[str] = []  # Initialize empty list to track downloaded file paths
        
        try:  # Attempt media download with error handling
            if not self.product_data or not self.product_data.get("name"):  # Validate that product data with name exists
                print(f"{BackgroundColors.RED}No product data available for media download.{Style.RESET_ALL}")  # Alert user that required data is missing
                return downloaded_files  # Return empty list when data is unavailable
            
            html_content = self.html_content  # Use stored HTML content
            if not html_content:  # Verify if HTML content is unavailable
                print(f"{BackgroundColors.RED}No HTML content available.{Style.RESET_ALL}")  # Alert user about HTML unavailability
                return downloaded_files  # Return empty list when HTML is unavailable
            
            soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object
            
            product_name = self.product_data.get("name", "Unknown Product")  # Get product name or use default
            is_international = self.detect_international(soup)
            if is_international and not product_name.startswith("International"):
                product_name = f"International - {product_name}"
                self.product_data["name"] = product_name  # Update product data with prefixed name
                verbose_output(f"{BackgroundColors.YELLOW}Product name prefixed with 'International'.{Style.RESET_ALL}")
            
            output_dir = self.create_output_directory(product_name)  # Create output directory for product
            
            image_files = self.download_product_images(soup, output_dir)  # Download all product images
            downloaded_files.extend(image_files)  # Add image files to downloaded list
            
            video_files = self.download_product_videos(soup, output_dir)  # Download all product videos
            downloaded_files.extend(video_files)  # Add video files to downloaded list
            
            if not self.local_html_path:  # Only collect assets and save snapshot when not using a provided local HTML
                asset_map = self.collect_assets(html_content, output_dir)  # Download and collect all page assets
                
                snapshot_path = self.save_snapshot(html_content, output_dir, asset_map)  # Save HTML snapshot with localized assets
                if snapshot_path:  # Verify if snapshot was saved successfully
                    downloaded_files.append(snapshot_path)  # Add snapshot path to downloaded files list
            
            description_file = self.create_product_description_file(  # Create product description text file
                self.product_data, output_dir, product_name, self.product_url  # Pass all required parameters
            )  # End of method call
            if description_file:  # Verify if description file was created successfully
                downloaded_files.append(description_file)  # Add description file path to downloaded files list
            
            verbose_output(  # Output success message with file count
                f"{BackgroundColors.GREEN}Media processing completed. {len(downloaded_files)} files saved.{Style.RESET_ALL}"
            )  # End of verbose output call
            
        except Exception as e:  # Catch any exceptions during media download
            print(f"{BackgroundColors.RED}Error during media download: {e}{Style.RESET_ALL}")  # Alert user about media download error
        
        return downloaded_files  # Return list of all downloaded file paths


    def scrape(self, verbose: bool = VERBOSE) -> Optional[Dict[str, Any]]:
        """
        Main scraping method that orchestrates the entire scraping process.
        Supports both online scraping (via browser) and offline scraping (from local HTML file).

        :param verbose: Boolean flag to enable verbose output
        :return: Dictionary containing all scraped data and downloaded file paths
        """

        verbose_output(  # Display scraping start message (verbose)
            f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Starting {BackgroundColors.CYAN}AliExpress{BackgroundColors.GREEN} Scraping process...{Style.RESET_ALL}"
        )  # End of verbose_output call
        
        try:  # Attempt scraping process with error handling
            if self.local_html_path:  # If local HTML file path is provided
                verbose_output(  # Display offline mode message (verbose)
                    f"{BackgroundColors.GREEN}Using offline mode with local HTML file{Style.RESET_ALL}"
                )  # End of verbose_output call
                
                html_content = self.read_local_html()  # Read HTML content from local file
                if not html_content:  # Verify if HTML reading failed
                    return None  # Return None if HTML is unavailable
                
                self.html_content = html_content  # Store HTML content for later use
                
            else:  # Online scraping mode
                verbose_output(  # Display online mode message (verbose)
                    f"{BackgroundColors.GREEN}Using online mode with browser automation{Style.RESET_ALL}"
                )  # End of verbose_output call
                
                self.launch_browser()  # Initialize and launch browser instance
                
                if not self.load_page():  # Attempt to load product page
                    return None  # Return None if page loading failed
                
                self.wait_full_render()  # Wait for page to fully render with dynamic content
                self.auto_scroll()  # Scroll page to trigger lazy-loaded content
                
                html_content = self.get_rendered_html()  # Extract fully rendered HTML content
                if not html_content:  # Verify if HTML extraction failed
                    return None  # Return None if HTML is unavailable
                
                self.html_content = html_content  # Store HTML content for later use
            
            product_info = self.scrape_product_info(html_content)  # Parse and extract product information
            if not product_info:  # Verify if product info extraction failed
                return None  # Return None if extraction failed
            
            downloaded_files = self.download_media()  # Download product media and create snapshot
            product_info["downloaded_files"] = downloaded_files  # Add downloaded files to product info dictionary
            
            verbose_output(  # Display success message to user
                f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}AliExpress scraping completed successfully!{Style.RESET_ALL}"
            )  # End of verbose_output call
            
            return product_info  # Return complete product information with downloaded files
            
        except Exception as e:  # Catch any exceptions during scraping process
            print(f"{BackgroundColors.RED}Scraping failed: {e}{Style.RESET_ALL}")  # Alert user about scraping failure
            return None  # Return None to indicate scraping failed
        finally:  # Always execute cleanup regardless of success or failure
            if not self.local_html_path:  # Only close browser in online mode
                self.close_browser()  # Close browser and release resources


# Functions Definitions


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


def output_result(result):
    """
    Outputs the result to the terminal.

    :param result: The result to be outputted
    :return: None
    """

    if result:  # Verify if result dictionary is not None or empty
        print(  # Display formatted success message with product data
            f"{BackgroundColors.GREEN}Scraping successful! Product data:{Style.RESET_ALL}\n"
            f"  {BackgroundColors.CYAN}Name:{Style.RESET_ALL} {result.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Price:{Style.RESET_ALL} R${result.get('current_price_integer', 'N/A')},{result.get('current_price_decimal', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Files:{Style.RESET_ALL} {len(result.get('downloaded_files', []))} downloaded"
        )  # End of print statement
    else:  # Handle case when result is None or empty
        print(  # Display failure message
            f"{BackgroundColors.RED}Scraping failed. No data returned.{Style.RESET_ALL}"
        )  # End of print statement


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

    env_path = Path(__file__).parent / ".env"  # Path to the .env file
    
    if not verify_filepath_exists(env_path):  # If the .env file does not exist
        print(f"{BackgroundColors.CYAN}.env{BackgroundColors.YELLOW} file not found at {BackgroundColors.CYAN}{env_path}{BackgroundColors.YELLOW}.{Style.RESET_ALL}")
        return False  # Return False

    return True  # Return True if the .env file exists


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

    print(  # Clear terminal and display welcome message
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}AliExpress Scraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n",  # End with newline
    )  # End of print statement
    start_time = datetime.datetime.now()  # Record program start time
    test_url = "https://pt.aliexpress.com/item/1005008724358345.html"  # Test URL  # Define test URL for scraping demonstration
    
    verbose_output(  # Log test URL being used
        f"{BackgroundColors.GREEN}Testing AliExpress scraper with URL: {BackgroundColors.CYAN}{test_url}{Style.RESET_ALL}\n"
    )  # End of verbose output call
    
    try:  # Attempt scraping process with error handling
        scraper = AliExpress(test_url)  # Create AliExpress scraper instance with test URL
        result = scraper.scrape()  # Execute scraping process
        output_result(result)  # Display scraping results to user
    except Exception as e:  # Catch any exceptions during test execution
        print(f"{BackgroundColors.RED}Error during test: {e}{Style.RESET_ALL}")  # Alert user about test error

    finish_time = datetime.datetime.now()  # Record program finish time
    print(  # Display execution time statistics
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # End of print statement
    print(  # Display program completion message
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )  # End of print statement
    
    (  # Register sound playback function if enabled using ternary expression
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None  # Register play_sound to run at exit if enabled
    )  # End of ternary expression


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
