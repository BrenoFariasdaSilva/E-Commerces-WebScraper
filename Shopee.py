"""
================================================================================
Shopee Web Scraper
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-02-11
Description :
	This script provides a Shopee class for scraping product information
	from Shopee product pages using authenticated browser sessions. It extracts
	comprehensive product details including name, prices, discount information,
	descriptions, and media assets from fully rendered pages.

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
import sys  # Access system-specific parameters and functions
import time  # Provide time-related functions for delays
from bs4 import BeautifulSoup, Tag  # Parse and navigate HTML documents
from colorama import Style  # Colorize terminal text output
from Logger import Logger  # Custom logging functionality for output redirection
from pathlib import Path  # Handle filesystem paths in object-oriented way
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError  # Browser automation framework with timeout handling
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

🛒 Encontre na Shopee:
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


class Shopee:
    """
    A web scraper class for extracting product information from Shopee using
    authenticated browser sessions.
    
    This class handles the extraction of product details including name, prices,
    discounts, descriptions, and media files from Shopee product pages using
    Playwright for full page rendering and authenticated access.
    """

    def __init__(self, url: str) -> None:
        """
        Initializes the Shopee scraper with a product URL.

        :param url: The URL of the Shopee product page to scrape
        :return: None
        """

        self.url: str = url  # Store the initial product URL for reference
        self.product_url: str = url  # Maintain separate copy of product URL for Shopee direct usage
        self.product_data: Dict[str, Any] = {}  # Initialize empty dictionary to store extracted product data
        self.playwright: Optional[Any] = None  # Placeholder for Playwright instance
        self.browser: Optional[Any] = None  # Placeholder for browser instance
        self.page: Optional[Any] = None  # Placeholder for page object

        verbose_output(  # Output initialization message to user
            f"{BackgroundColors.GREEN}Shopee scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
        )  # End of verbose output call


    def _launch_browser(self):
        """
        Launches an authenticated Chrome browser using existing profile.

        :return: None
        :raises Exception: If browser launch fails
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Launching authenticated Chrome browser...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt to launch browser with error handling
            self.playwright = sync_playwright().start()  # Start Playwright synchronous context manager
            playwright_obj = cast(Any, self.playwright)  # Cast Playwright instance to Any for static type checkers
            
            launch_options = {  # Configure browser launch options dictionary
                "headless": HEADLESS,  # Set headless mode from environment variable
                "args": [  # List of Chrome command-line arguments
                    "--disable-blink-features=AutomationControlled",  # Disable automation detection flag
                    "--disable-dev-shm-usage",  # Disable shared memory usage for stability
                    "--no-sandbox",  # Disable sandbox for compatibility
                ]  # End of args list
            }  # End of launch_options dictionary

            # Add Chrome profile path if provided
            if CHROME_PROFILE_PATH:  # Verify if custom Chrome profile path is provided
                launch_options["args"].append(f"--user-data-dir={CHROME_PROFILE_PATH}")  # Add user data directory to browser arguments
                verbose_output(  # Log profile path being used
                    f"{BackgroundColors.GREEN}Using Chrome profile: {BackgroundColors.CYAN}{CHROME_PROFILE_PATH}{Style.RESET_ALL}"
                )  # End of verbose output call

            # Add Chrome executable path if provided
            if CHROME_EXECUTABLE_PATH:  # Verify if custom Chrome executable path is provided
                launch_options["executable_path"] = CHROME_EXECUTABLE_PATH  # Set custom executable path in launch options
                verbose_output(  # Log executable path being used
                    f"{BackgroundColors.GREEN}Using Chrome executable: {BackgroundColors.CYAN}{CHROME_EXECUTABLE_PATH}{Style.RESET_ALL}"
                )  # End of verbose output call

            self.browser = playwright_obj.chromium.launch(**launch_options)  # Launch Chromium using cast object to avoid Optional member warning
            
            if self.browser is None:  # Verify browser instance was created successfully
                raise Exception("Failed to initialize browser")  # Raise exception if browser initialization failed
            
            self.page = self.browser.new_page()  # Create new browser page/tab
            
            if self.page is None:  # Verify page instance was created successfully
                raise Exception("Failed to create page")  # Raise exception if page creation failed
            
            # Set realistic viewport
            self.page.set_viewport_size({"width": 1920, "height": 1080})  # Set viewport dimensions to standard Full HD resolution
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Browser launched successfully.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during browser launch
            print(f"{BackgroundColors.RED}Failed to launch browser: {e}{Style.RESET_ALL}")  # Alert user about browser launch failure
            raise  # Re-raise exception for caller to handle


    def _close_browser(self):
        """
        Safely closes the browser and Playwright instances.

        :return: None
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Closing browser...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt to close browser resources with error handling
            if self.page:  # Verify if page instance exists before closing
                self.page.close()  # Close the browser page to release resources
            if self.browser:  # Verify if browser instance exists before closing
                self.browser.close()  # Close the browser to release resources
            if self.playwright:  # Verify if Playwright instance exists before stopping
                self.playwright.stop()  # Stop the Playwright instance
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Browser closed successfully.{Style.RESET_ALL}"
            )  # End of verbose output call
        except Exception as e:  # Catch any exceptions during browser close
            print(f"{BackgroundColors.YELLOW}Warning during browser close: {e}{Style.RESET_ALL}")  # Warn user about close issues without failing


    def _load_page(self) -> bool:
        """
        Loads the product page and waits for network idle.

        :return: True if successful, False otherwise
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Loading page: {BackgroundColors.CYAN}{self.product_url}{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate that page instance exists before attempting to load
            print(f"{BackgroundColors.RED}Page instance not initialized.{Style.RESET_ALL}")  # Alert user that page is not ready
            return False  # Return failure status if page is not initialized

        try:  # Attempt page loading with error handling
            # Navigate to the URL
            self.page.goto(self.product_url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")  # Navigate to product URL and wait for DOM to load
            
            # Wait for network to be idle
            self.page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)  # Wait for network to become idle indicating page is loaded
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Page loaded successfully.{Style.RESET_ALL}"
            )  # End of verbose output call
            return True  # Return success status after successful page load

        except PlaywrightTimeoutError:  # Handle timeout errors specifically
            print(f"{BackgroundColors.YELLOW}Page load timeout, continuing anyway...{Style.RESET_ALL}")  # Warn user about timeout but continue execution
            return True  # Return success despite timeout to allow scraping partial content
        except Exception as e:  # Catch any other exceptions during page loading
            print(f"{BackgroundColors.RED}Failed to load page: {e}{Style.RESET_ALL}")  # Alert user about page loading failure
            return False  # Return failure status for unhandled errors


    def _auto_scroll(self) -> None:
        """
        Automatically scrolls the page to trigger lazy-loaded content.

        :return: None
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Auto-scrolling to load lazy content...{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate that page instance exists before scrolling
            print(f"{BackgroundColors.YELLOW}Warning: Page not initialized, skipping scroll.{Style.RESET_ALL}")  # Warn user that scrolling will be skipped
            return  # Exit method early if page is not initialized

        try:  # Attempt auto-scrolling with error handling
            # Get the total page height
            previous_height = self.page.evaluate("document.body.scrollHeight")  # Get initial page height for comparison
            
            while True:  # Loop indefinitely until break condition is met
                # Scroll down by SCROLL_STEP pixels
                self.page.evaluate(f"window.scrollBy(0, {SCROLL_STEP})")  # Scroll down by configured step pixels
                time.sleep(SCROLL_PAUSE_TIME)  # Pause to allow lazy content to load
                
                # Get new height
                new_height = self.page.evaluate("document.body.scrollHeight")  # Get updated page height after scroll
                
                # Verify if we've reached the bottom
                scroll_position = self.page.evaluate("window.pageYOffset + window.innerHeight")  # Calculate current scroll position
                if scroll_position >= new_height:  # Verify if scrolled to bottom of page
                    break  # Exit loop when bottom is reached
                    
                # Verify if page height hasn't changed (no more content loading)
                if new_height == previous_height:  # Verify if page height stopped changing
                    break  # Exit loop when no new content is loaded
                    
                previous_height = new_height  # Update previous height for next iteration

            # Scroll back to top
            self.page.evaluate("window.scrollTo(0, 0)")  # Scroll back to top of page
            time.sleep(SCROLL_PAUSE_TIME)  # Pause briefly after scrolling to top
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Auto-scroll completed.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during auto-scroll
            print(f"{BackgroundColors.YELLOW}Warning during auto-scroll: {e}{Style.RESET_ALL}")  # Warn user about scroll issues without failing


    def _wait_full_render(self) -> None:
        """
        Waits for the page to be fully rendered with all dynamic content.

        :return: None
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Waiting for full page render...{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate that page instance exists before waiting
            print(f"{BackgroundColors.YELLOW}Warning: Page not initialized, skipping render wait.{Style.RESET_ALL}")  # Warn user that render wait will be skipped
            return  # Exit method early if page is not initialized

        try:  # Attempt waiting for render with error handling
            # Wait for specific Shopee elements
            selectors_to_wait = [  # Define list of Shopee-specific selectors to wait for
                "div[class*='product-name']",  # Shopee product name container selector
                "div[class*='price']",  # Shopee price container selector
                "img"  # Generic image tag selector
            ]  # End of selectors list
            
            for selector in selectors_to_wait:  # Iterate through each selector to ensure visibility
                try:  # Attempt to wait for selector with nested error handling
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")  # Wait for selector to become visible
                except:  # Silently handle timeout if selector not found
                    pass  # Continue to next selector even if current one fails

            # Additional wait for JavaScript execution
            time.sleep(2)  # Additional wait time to ensure all dynamic content is rendered
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Page fully rendered.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during render wait
            print(f"{BackgroundColors.YELLOW}Warning during render wait: {e}{Style.RESET_ALL}")  # Warn user about render wait issues without failing


    def _get_rendered_html(self) -> Optional[str]:
        """
        Gets the fully rendered HTML content after JavaScript execution.

        :return: Rendered HTML string or None if failed
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Extracting rendered HTML...{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate that page instance exists before extracting HTML
            print(f"{BackgroundColors.RED}Page instance not initialized.{Style.RESET_ALL}")  # Alert user that page is not ready
            return None  # Return None to indicate extraction failed

        try:  # Attempt HTML extraction with error handling
            html = self.page.content()  # Extract fully rendered HTML content from page
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Rendered HTML extracted successfully.{Style.RESET_ALL}"
            )  # End of verbose output call
            return html  # Return extracted HTML content
        except Exception as e:  # Catch any exceptions during HTML extraction
            print(f"{BackgroundColors.RED}Failed to extract HTML: {e}{Style.RESET_ALL}")  # Alert user about extraction failure
            return None  # Return None to indicate extraction failed


    def extract_product_name(self, soup: BeautifulSoup) -> str:
        """
        Extracts the product name from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product name string or "Unknown Product" if not found
        """
        
        # Try multiple selectors for Shopee product name
        selectors = [  # Define list of CSS selectors to find product name in priority order
            ("div", {"class": re.compile(r".*product.*name.*", re.IGNORECASE)}),  # Shopee product name container with regex pattern
            ("span", {"class": re.compile(r".*product.*title.*", re.IGNORECASE)}),  # Alternative product title span with regex pattern
            ("h1", {}),  # Generic H1 heading as fallback
        ]  # End of selectors list
        
        for tag, attrs in selectors:  # Iterate through each selector combination
            name_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if name_element:  # Verify if matching element was found
                product_name = name_element.get_text(strip=True)  # Extract and clean text content from element
                if product_name and product_name != "":  # Validate that extracted name is not empty
                    verbose_output(  # Log successfully extracted product name
                        f"{BackgroundColors.GREEN}Product name: {BackgroundColors.CYAN}{product_name}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return product_name  # Return the product name immediately when found
        
        verbose_output(  # Warn that product name could not be extracted
            f"{BackgroundColors.YELLOW}Product name not found, using default.{Style.RESET_ALL}"
        )  # End of verbose output call
        return "Unknown Product"  # Return default placeholder when name extraction failsdef verbose_output(true_string="", false_string=""):
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
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Shopee Scraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n",  # End with newline
    )  # End of print statement
    start_time = datetime.datetime.now()  # Record program start time

    test_url = "https://shopee.com.br/product-example"  # Test URL  # Define test URL for scraping demonstration
    
    verbose_output(  # Log test URL being used
        f"{BackgroundColors.GREEN}Testing Shopee scraper with URL: {BackgroundColors.CYAN}{test_url}{Style.RESET_ALL}\n"
    )  # End of verbose output call
    
    try:  # Attempt scraping process with error handling
        scraper = Shopee(test_url)  # Create Shopee scraper instance with test URL
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
