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


    def launch_browser(self):
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

            if CHROME_PROFILE_PATH:  # Verify if custom Chrome profile path is provided
                launch_options["args"].append(f"--user-data-dir={CHROME_PROFILE_PATH}")  # Add user data directory to browser arguments
                verbose_output(  # Log profile path being used
                    f"{BackgroundColors.GREEN}Using Chrome profile: {BackgroundColors.CYAN}{CHROME_PROFILE_PATH}{Style.RESET_ALL}"
                )  # End of verbose output call

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
            
            self.page.set_viewport_size({"width": 1920, "height": 1080})  # Set viewport dimensions to standard Full HD resolution
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Browser launched successfully.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during browser launch
            print(f"{BackgroundColors.RED}Failed to launch browser: {e}{Style.RESET_ALL}")  # Alert user about browser launch failure
            raise  # Re-raise exception for caller to handle


    def close_browser(self):
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


    def load_page(self) -> bool:
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
            self.page.goto(self.product_url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")  # Navigate to product URL and wait for DOM to load
            
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


    def auto_scroll(self) -> None:
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
            previous_height = self.page.evaluate("document.body.scrollHeight")  # Get initial page height for comparison
            
            while True:  # Loop indefinitely until break condition is met
                self.page.evaluate(f"window.scrollBy(0, {SCROLL_STEP})")  # Scroll down by configured step pixels
                time.sleep(SCROLL_PAUSE_TIME)  # Pause to allow lazy content to load
                
                new_height = self.page.evaluate("document.body.scrollHeight")  # Get updated page height after scroll
                
                scroll_position = self.page.evaluate("window.pageYOffset + window.innerHeight")  # Calculate current scroll position
                if scroll_position >= new_height:  # Verify if scrolled to bottom of page
                    break  # Exit loop when bottom is reached
                    
                if new_height == previous_height:  # Verify if page height stopped changing
                    break  # Exit loop when no new content is loaded
                    
                previous_height = new_height  # Update previous height for next iteration

            self.page.evaluate("window.scrollTo(0, 0)")  # Scroll back to top of page
            time.sleep(SCROLL_PAUSE_TIME)  # Pause briefly after scrolling to top
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Auto-scroll completed.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during auto-scroll
            print(f"{BackgroundColors.YELLOW}Warning during auto-scroll: {e}{Style.RESET_ALL}")  # Warn user about scroll issues without failing


    def wait_full_render(self) -> None:
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
            selectors_to_wait = [  # Define list of AliExpress-specific selectors to wait for
                "h1[data-pl='product-title']",  # AliExpress product title selector
                "div[class*='price-default']",  # AliExpress price container selector
                "img"  # Generic image tag selector
            ]  # End of selectors list
            
            for selector in selectors_to_wait:  # Iterate through each selector to ensure visibility
                try:  # Attempt to wait for selector with nested error handling
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")  # Wait for selector to become visible
                except:  # Silently handle timeout if selector not found
                    pass  # Continue to next selector even if current one fails

            time.sleep(2)  # Additional wait time to ensure all dynamic content is rendered
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Page fully rendered.{Style.RESET_ALL}"
            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during render wait
            print(f"{BackgroundColors.YELLOW}Warning during render wait: {e}{Style.RESET_ALL}")  # Warn user about render wait issues without failing


    def get_rendered_html(self) -> Optional[str]:
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


    def read_local_html(self) -> Optional[str]:
        """
        Reads HTML content from a local file for offline scraping.

        :return: HTML content string or None if failed
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Reading local HTML file: {BackgroundColors.CYAN}{self.local_html_path}{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt to read file with error handling
            if not self.local_html_path:  # Verify if local HTML path is not set
                print(f"{BackgroundColors.RED}No local HTML path provided.{Style.RESET_ALL}")  # Alert user that path is missing
                return None  # Return None if path doesn't exist
            
            if not os.path.exists(self.local_html_path):  # Verify if file doesn't exist
                print(f"{BackgroundColors.RED}\nLocal HTML file not found: {BackgroundColors.CYAN}{self.local_html_path}{Style.RESET_ALL}")  # Alert user that file is missing
                return None  # Return None if file doesn't exist
            
            with open(self.local_html_path, "r", encoding="utf-8") as file:  # Open file with UTF-8 encoding
                html_content = file.read()  # Read entire file content
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Local HTML content loaded successfully.{Style.RESET_ALL}"
            )  # End of verbose output call
            return html_content  # Return the HTML content string
            
        except Exception as e:  # Catch any exceptions during file reading
            print(f"{BackgroundColors.RED}Error reading local HTML file: {e}{Style.RESET_ALL}")  # Alert user about file reading error
            return None  # Return None to indicate reading failed


    def extract_product_name(self, soup: BeautifulSoup) -> str:
        """
        Extracts the product name from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product name string or "Unknown Product" if not found
        """
        
        for tag, attrs in HTML_SELECTORS["product_name"]:  # Iterate through each selector combination from centralized dictionary
            name_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if name_element:  # Verify if matching element was found
                    raw_product_name = name_element.get_text(separator=" ", strip=True)  # Extract raw text, preserve single spaces between parts
                    product_name = normalize_product_dir_name(raw_product_name, replace_with="_", title_case=True)  # Normalize name for directory usage
                    if product_name and product_name != "":  # Validate that extracted name is not empty
                        verbose_output(  # Log successfully extracted product name
                            f"{BackgroundColors.GREEN}Product name: {BackgroundColors.CYAN}{product_name}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        return product_name  # Return the sanitized product name immediately when found
        
        verbose_output(  # Warn that product name could not be extracted
            f"{BackgroundColors.YELLOW}Product name not found, using default.{Style.RESET_ALL}"
        )  # End of verbose output call
        return "Unknown Product"  # Return default placeholder when name extraction fails


    def detect_international(self, soup: BeautifulSoup) -> bool:
        """
        Detects if the product is international by checking for the international import declaration text.
        Looks for "Produto International objeto de declaração de importação e sujeito a impostos estaduais e federais"
        in elements with class="NzLZHV", or falls back to checking "País de Origem" (Country of Origin) field.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: True if product is international, False otherwise
        """
        
        verbose_output(  # Log detection attempt
            f"{BackgroundColors.GREEN}Checking if product is international...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt to detect international status with error handling
            international_elements = soup.find_all("span", class_="NzLZHV")
            
            for element in international_elements:  # Iterate through each element
                if not isinstance(element, Tag):  # Ensure element is a BeautifulSoup Tag
                    continue  # Skip non-Tag elements
                
                element_text = element.get_text(strip=True)  # Extract and clean element text
                
                if "Produto International objeto de declaração de importação" in element_text:
                    verbose_output(  # Log international detection
                        f"{BackgroundColors.YELLOW}Product is INTERNATIONAL (import declaration found){Style.RESET_ALL}"
                    )  # End of verbose output call
                    return True  # Return True for international product
            
            detail_labels = soup.find_all("h3", HTML_SELECTORS["detail_label"])
            
            for label in detail_labels:  # Iterate through each detail label
                if not isinstance(label, Tag):  # Ensure element is a BeautifulSoup Tag
                    continue  # Skip non-Tag elements
                
                label_text = label.get_text(strip=True)  # Extract and clean label text
                
                if "País de Origem" in label_text or "Country of Origin" in label_text:
                    parent = label.parent  # Get parent container
                    if parent and isinstance(parent, Tag):  # Ensure parent is a Tag
                        value_element = parent.find("div")  # Get first div in parent (contains the value)
                        if value_element and isinstance(value_element, Tag):
                            country_value = value_element.get_text(strip=True)  # Extract country value
                            
                            verbose_output(  # Log detected country
                                f"{BackgroundColors.GREEN}Country of Origin: {BackgroundColors.CYAN}{country_value}{Style.RESET_ALL}"
                            )  # End of verbose output call
                            
                            if country_value.lower() not in ["brasil", "brazil"]:
                                verbose_output(  # Log international detection
                                    f"{BackgroundColors.YELLOW}Product is INTERNATIONAL (from {country_value}){Style.RESET_ALL}"
                                )  # End of verbose output call
                                return True  # Return True for international product
                            else:
                                verbose_output(  # Log domestic product
                                    f"{BackgroundColors.GREEN}Product is domestic (from Brazil){Style.RESET_ALL}"
                                )  # End of verbose output call
                                return False  # Return False for domestic product
            
            verbose_output(  # Log country field not found
                f"{BackgroundColors.YELLOW}International indicators not found, assuming domestic.{Style.RESET_ALL}"
            )  # End of verbose output call
            return False  # Default to domestic if no indicators found
            
        except Exception as e:  # Catch any exceptions during detection
            print(f"{BackgroundColors.YELLOW}Warning: Error detecting international status: {e}{Style.RESET_ALL}")  # Warn user about detection error
            return False  # Default to domestic on error


    def prefix_international_name(self, product_name: str) -> str:
        """
        Adds "International - " prefix to product name if not already present.
        
        :param product_name: Original product name
        :return: Product name with International prefix
        """
        
        if not product_name.upper().startswith("International"):  # Check if prefix not already present
            product_name = f"International - {product_name}"  # Add International prefix
            # Normalize whitespace after prefix insertion to avoid accidental double spaces
            product_name = product_name.replace("\u00A0", " ")  # Replace NBSP with normal space
            product_name = re.sub(r"\s+", " ", product_name).strip()  # Collapse multiple whitespace to single spaces
            verbose_output(  # Log name modification
                f"{BackgroundColors.GREEN}Updated product name: {BackgroundColors.CYAN}{product_name}{Style.RESET_ALL}"
            )  # End of verbose output call

        return product_name  # Return modified and normalized product name


    def extract_current_price(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """
        Extracts the current price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for current price
        """
        
        for tag, attrs in HTML_SELECTORS["current_price"]:  # Iterate through each selector combination from centralized dictionary
            price_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+[\.\d]*)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = re.sub(r"[^0-9]", "", match.group(1))  # Extract integer part and remove non-digits
                    decimal_part = match.group(2)  # Extract decimal part of price
                    verbose_output(  # Log successfully extracted current price
                        f"{BackgroundColors.GREEN}Current price: R${integer_part},{decimal_part}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return integer_part, decimal_part  # Return price components as tuple
        
        verbose_output(  # Warn that current price could not be extracted
            f"{BackgroundColors.YELLOW}Current price not found, using default.{Style.RESET_ALL}"
        )  # End of verbose output call
        return "0", "00"  # Return default zero price when extraction fails


    def extract_old_price(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """
        Extracts the old price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for old price
        """
        
        for tag, attrs in HTML_SELECTORS["old_price"]:  # Iterate through each selector combination from centralized dictionary
            price_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+[\.\d]*)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = re.sub(r"[^0-9]", "", match.group(1))  # Extract integer part and remove non-digits
                    decimal_part = match.group(2)  # Extract decimal part of price
                    verbose_output(  # Log successfully extracted old price
                        f"{BackgroundColors.GREEN}Old price: R${integer_part},{decimal_part}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return integer_part, decimal_part  # Return price components as tuple
        
        verbose_output(  # Warn that old price could not be extracted
            f"{BackgroundColors.YELLOW}Old price not found.{Style.RESET_ALL}"
        )  # End of verbose output call
        return "N/A", "N/A"  # Return N/A when old price is not available


    def extract_discount_percentage(self, soup: BeautifulSoup) -> str:
        """
        Extracts the discount percentage from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Discount percentage string or "N/A" if not found
        """
        
        try:  # Compute discount from current and old prices when possible
            old_int, old_dec = self.extract_old_price(soup)  # Get old price components
            curr_int, curr_dec = self.extract_current_price(soup)  # Get current price components
            if old_int and old_int != "N/A" and curr_int:  # Ensure we have valid numeric parts
                old_value = float(f"{old_int}.{old_dec}")  # Compose old price float value
                curr_value = float(f"{curr_int}.{curr_dec}")  # Compose current price float value
                if old_value > 0:  # Avoid division by zero
                    discount = ((old_value - curr_value) / old_value) * 100.0  # Compute discount percentage
                    discount_int = int(round(discount))  # Round to nearest integer percent
                    verbose_output(  # Log computed discount percentage
                        f"{BackgroundColors.GREEN}Computed discount: {discount_int}%{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return f"{discount_int}%"  # Return formatted percentage string
        except Exception:  # Fail silently and return N/A on any error
            pass  # Continue to fallback

        return "N/A"  # Return N/A when discount cannot be computed


    def extract_product_description(self, soup: BeautifulSoup) -> str:
        """
        Extracts the product description from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product description string or "No description available" if not found
        """
        
        for tag, attrs in HTML_SELECTORS["description"]:  # Iterate through each selector combination from centralized dictionary
            description_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if description_element and isinstance(description_element, Tag):  # Verify if matching element was found and is a Tag
                # Extract textual content while preserving some line breaks for readability  # preserve line breaks
                texts = []  # Collect pieces of text
                for child in description_element.find_all(["p", "span", "h1", "h2", "h3", "li", "div"]):  # Iterate child tags
                    if isinstance(child, Tag):  # Ensure child is Tag
                        piece = child.get_text(separator=" ", strip=True)  # Extract piece text
                        if piece:  # If piece has content
                            texts.append(piece)  # Append piece to texts list
                description = "\n".join(texts).strip()  # Join pieces with newline separators
                description = self.to_sentence_case(description)  # Convert extracted description to sentence case
                if description and len(description) > 10:  # Validate that description has substantial content
                    verbose_output(  # Log successfully extracted description with character count
                        f"{BackgroundColors.GREEN}Description found ({len(description)} chars).{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return description  # Return the formatted product description

        return "No description available"  # Return default message when description is not found


    def extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:  # Extract specifications table into dict
        """
        Extracts the product specification table into a dictionary when present.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Dictionary of specification key->value pairs or empty dict
        """

        specs: Dict[str, str] = {}  # Initialize empty dict for specifications
        try:  # Attempt to locate specifications container with error handling
            container = soup.find("div", HTML_SELECTORS.get("specs_container"))  # type: ignore[arg-type]  # Find specs container
            if container and isinstance(container, Tag):  # Verify container exists and is a Tag
                rows = container.find_all("div", HTML_SELECTORS.get("specs_row"))  # type: ignore[arg-type]  # Find specification rows
                for row in rows:  # Iterate through each specification row
                    if not isinstance(row, Tag):  # Ensure row is a Tag
                        continue  # Skip non-Tag nodes
                    title_el = row.find("div", HTML_SELECTORS.get("specs_title"))  # type: ignore[arg-type]  # Find title element
                    value_el = row.find("div", HTML_SELECTORS.get("specs_value"))  # type: ignore[arg-type]  # Find value element
                    if title_el and value_el and isinstance(title_el, Tag) and isinstance(value_el, Tag):  # Validate elements
                        key = title_el.get_text(strip=True)  # Extract key text
                        val = value_el.get_text(strip=True)  # Extract value text
                        if key:  # Only add non-empty keys
                            specs[key] = val  # Store spec pair in dict
        except Exception as e:  # Catch any exceptions during spec extraction
            verbose_output(  # Log warning about specs extraction failure
                f"{BackgroundColors.YELLOW}Warning extracting specifications: {e}{Style.RESET_ALL}"
            )  # End of verbose output call

        return specs  # Return specification dictionary (possibly empty)


    def find_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Finds all image URLs from the product gallery (class="airUhU").
        Extracts full-size images from thumbnail containers (class="UBG7wZ").
        Removes resize parameters (@resize_w82_nl, @resize_w164_nl) to get original images.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of image URLs
        """
        
        image_urls: List[str] = []  # Initialize empty list to store image URLs
        seen_urls: set = set()  # Track URLs to avoid duplicates
        
        verbose_output(  # Log image extraction attempt
            f"{BackgroundColors.GREEN}Extracting image URLs from gallery...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt to find images with error handling
            gallery = soup.find("div", HTML_SELECTORS.get("gallery"))  # type: ignore[arg-type]  # Find AliExpress gallery container
            if gallery and isinstance(gallery, Tag):  # Verify gallery container was found
                imgs = gallery.find_all("img")  # Find all image tags inside gallery
                verbose_output(  # Log number of images found in gallery
                    f"{BackgroundColors.GREEN}Gallery images found: {BackgroundColors.CYAN}{len(imgs)}{BackgroundColors.GREEN}{Style.RESET_ALL}"
                )  # End of verbose output call
                for img in imgs:  # Iterate through each image tag
                    if not isinstance(img, Tag):  # Ensure element is a BeautifulSoup Tag
                        continue  # Skip non-Tag elements
                    src = img.get("src") or img.get("data-src") or img.get("data-original")  # Get possible source attributes
                    if not src or not isinstance(src, str):  # Skip if src missing or invalid
                        continue  # Continue to next image
                    # Prefer higher resolution images by replacing common size fragments  # try to upgrade to larger image
                    src_high = re.sub(r"_\d{2,4}x\d{2,4}(q\d+)?(\.jpg|\.png|\.avif)?", "_960x960q75.jpg", src)  # Attempt to create high-res URL
                    final_url = src_high if src_high else src  # Choose final URL
                    if final_url.startswith("//"):  # Fix protocol-relative URLs
                        final_url = "https:" + final_url  # Prepend https scheme
                    if final_url not in seen_urls and "placeholder" not in final_url.lower():  # Avoid duplicates and placeholders
                        image_urls.append(final_url)  # Add to image list
                        seen_urls.add(final_url)  # Track seen URL
                        verbose_output(  # Log found image URL
                            f"{BackgroundColors.GREEN}Found image: {BackgroundColors.CYAN}{final_url[:100]}{Style.RESET_ALL}"
                        )  # End of verbose output call

            # Search for user review images in reviews section if available  # also collect review images
            review_container = soup.find("div", HTML_SELECTORS.get("review_images_container"))  # type: ignore[arg-type]  # Find review images container
            if review_container and isinstance(review_container, Tag):  # Verify review container exists
                review_imgs = review_container.find_all("img")  # Find images inside reviews
                for img in review_imgs:  # Iterate review images
                    if not isinstance(img, Tag):  # Ensure Tag
                        continue  # Skip non-Tag
                    src = img.get("src") or img.get("data-src")  # Get source
                    if src and isinstance(src, str) and src.endswith(('.jpg_.avif', '.png_.avif', '.jpg', '.png')):  # Heuristic for review images
                        if src.startswith("//"):  # Fix protocol-relative
                            src = "https:" + src  # Prepend https
                        if src not in seen_urls:  # Avoid duplicates
                            image_urls.append(src)  # Add review image
                            seen_urls.add(src)  # Track seen
                            verbose_output(  # Log review image found
                                f"{BackgroundColors.GREEN}Found review image: {BackgroundColors.CYAN}{src[:100]}{Style.RESET_ALL}"
                            )  # End of verbose output call

        except Exception as e:  # Catch any exceptions during image extraction
            print(f"{BackgroundColors.RED}Error finding images: {e}{Style.RESET_ALL}")  # Alert user about error

        verbose_output(  # Log total number of images found
            f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(image_urls)}{BackgroundColors.GREEN} images.{Style.RESET_ALL}"
        )  # End of verbose output call

        return image_urls  # Return list of image URLs


    def find_video_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Finds all video URLs from the product page.
        Searches entire page for video elements with classes "tpgcVs" and extracts src attribute.
        Videos can be inside or outside the gallery container (class="airUhU").
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of video URLs
        """
        
        video_urls: List[str] = []  # Initialize empty list to store video URLs
        seen_urls: set = set()  # Track URLs to avoid duplicates
        
        verbose_output(  # Log video extraction attempt
            f"{BackgroundColors.GREEN}Extracting video URLs from page...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt to find videos with error handling
            # Search for video tags anywhere on the page  # AliExpress may include videos in gallery or reviews
            video_tags = soup.find_all("video")  # Find all video tags
            verbose_output(  # Log number of raw video tags found
                f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(video_tags)}{BackgroundColors.GREEN} video elements.{Style.RESET_ALL}"
            )  # End of verbose output call
            for video in video_tags:  # Iterate through each video tag
                if not isinstance(video, Tag):  # Ensure element is a BeautifulSoup Tag
                    continue  # Skip non-Tag elements
                video_url = video.get("src") or video.get("data-src")  # Try common attributes
                if video_url and isinstance(video_url, str) and (video_url.endswith('.mp4') or video_url.endswith('.webm') or 'm3u8' in video_url):  # Check for common video formats
                    if video_url not in seen_urls:  # Avoid duplicates
                        video_urls.append(video_url)  # Add video URL
                        seen_urls.add(video_url)  # Mark seen
                        verbose_output(  # Log found video URL
                            f"{BackgroundColors.GREEN}Found video: {BackgroundColors.CYAN}{video_url[:100]}{Style.RESET_ALL}"
                        )  # End of verbose output call
                # Also consider <source> tags inside <video>
                source_tags = video.find_all("source")  # Find source tags inside video
                for source in source_tags:  # Iterate source tags
                    if not isinstance(source, Tag):  # Ensure Tag
                        continue  # Skip non-Tag
                    src = source.get("src") or source.get("data-src")  # Get src
                    if src and isinstance(src, str) and (src.endswith('.mp4') or src.endswith('.webm') or 'm3u8' in src):  # Check format
                        if src not in seen_urls:  # Avoid duplicates
                            video_urls.append(src)  # Add to list
                            seen_urls.add(src)  # Track seen
                            verbose_output(  # Log found video source URL
                                f"{BackgroundColors.GREEN}Found video (source): {BackgroundColors.CYAN}{src[:100]}{Style.RESET_ALL}"
                            )  # End of verbose output call

            # Also search for direct links to video files in the page (heuristic)  # catch videos embedded via JS
            for ext in ('.mp4', '.webm', '.m3u8'):  # Check common extensions
                for tag in soup.find_all(string=re.compile(re.escape(ext))):  # Find strings containing extension
                    try:  # Attempt to extract URL-like text
                        text = str(tag)  # Convert to string
                        m = re.search(r"https?://[\w\-./%?=,&]+\"?", text)  # Attempt to find full URL pattern
                        if m:  # If match found
                            url = m.group(0).strip('"')  # Clean up
                            if url not in seen_urls:  # Avoid duplicates
                                video_urls.append(url)  # Add URL
                                seen_urls.add(url)  # Track seen
                    except Exception:  # Ignore extraction errors silently
                        pass  # Continue loop on error

        except Exception as e:  # Catch any exceptions during video extraction
            print(f"{BackgroundColors.RED}Error finding videos: {e}{Style.RESET_ALL}")  # Alert user about error

        verbose_output(  # Log total number of videos found
            f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(video_urls)}{BackgroundColors.GREEN} videos.{Style.RESET_ALL}"
        )  # End of verbose output call

        return video_urls  # Return list of video URLs


    def print_product_info(self, product_data: Dict[str, Any]) -> None:
        """
        Prints the extracted product information in a formatted manner.
        
        :param product_data: Dictionary containing the scraped product data
        :return: None
        """
        
        if not product_data:  # Verify if product data dictionary is empty or None
            print(f"{BackgroundColors.RED}No product data to display.{Style.RESET_ALL}")  # Alert user that no data is available
            return  # Exit method early when no data to print
        
        verbose_output(  # Display formatted product information to user (verbose)
            f"{BackgroundColors.GREEN}Product information extracted successfully:{BackgroundColors.GREEN}\n"
            f"  {BackgroundColors.CYAN}Name:{BackgroundColors.GREEN} {product_data.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Old Price:{BackgroundColors.GREEN} R${product_data.get('old_price_integer', 'N/A')},{product_data.get('old_price_decimal', 'N/A') if product_data.get('old_price_integer', 'N/A') != 'N/A' else 'N/A'}\n"
            f"  {BackgroundColors.CYAN}Current Price:{BackgroundColors.GREEN} R${product_data.get('current_price_integer', 'N/A')},{product_data.get('current_price_decimal', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Discount:{BackgroundColors.GREEN} {product_data.get('discount_percentage', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Description:{BackgroundColors.GREEN} {product_data.get('description', 'N/A')[:100]}...{Style.RESET_ALL}"
        )  # End of verbose_output call


    def scrape_product_info(self, html_content: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes product information from rendered HTML content.

        :param html_content: Rendered HTML string
        :return: Dictionary containing the scraped product data
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Parsing product information...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt to parse product information with error handling
            soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object
            
            product_name = self.extract_product_name(soup)  # Extract product name from parsed HTML
            
            is_international = self.detect_international(soup)  # Detect if product is international
            if is_international:  # If product is international
                product_name = self.prefix_international_name(product_name)  # Add International prefix to name
            
            current_price_int, current_price_dec = self.extract_current_price(soup)  # Extract current price integer and decimal parts
            old_price_int, old_price_dec = self.extract_old_price(soup)  # Extract old price integer and decimal parts
            discount_percentage = self.extract_discount_percentage(soup)  # Extract discount percentage value
            description = self.extract_product_description(soup)  # Extract product description text
            
            self.product_data = {  # Store all extracted data in dictionary
                "name": product_name,  # Product name string (with International prefix if applicable)
                "is_international": is_international,  # Boolean indicating if product is international
                "current_price_integer": current_price_int,  # Current price integer part
                "current_price_decimal": current_price_dec,  # Current price decimal part
                "old_price_integer": old_price_int,  # Old price integer part
                "old_price_decimal": old_price_dec,  # Old price decimal part
                "discount_percentage": discount_percentage,  # Discount percentage string
                "description": description,  # Product description text
                "url": self.product_url  # Original product URL
            }  # End of product_data dictionary
            
            self.print_product_info(self.product_data)  # Display extracted product information to user
            return self.product_data  # Return complete product data dictionary
            
        except Exception as e:  # Catch any exceptions during parsing
            print(f"{BackgroundColors.RED}Error parsing product info: {e}{Style.RESET_ALL}")  # Alert user about parsing error
            return None  # Return None to indicate parsing failed


    def create_directory(self, full_directory_name, relative_directory_name):
        """
        Creates a directory.

        :param full_directory_name: Name of the directory to be created.
        :param relative_directory_name: Relative name of the directory to be created that will be shown in the terminal.
        :return: None
        """

        verbose_output(  # Output status message to user if verbose enabled
            true_string=f"{BackgroundColors.GREEN}Creating the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory...{Style.RESET_ALL}"
        )  # End of verbose output call

        if os.path.isdir(full_directory_name):  # Verify if directory already exists
            return  # Exit early if directory exists to avoid redundant creation
        try:  # Attempt directory creation with error handling
            os.makedirs(full_directory_name)  # Create directory including all intermediate directories
        except OSError:  # Catch OS-level errors during directory creation
            print(  # Alert user about directory creation failure
                f"{BackgroundColors.GREEN}The creation of the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory failed.{Style.RESET_ALL}"
            )  # End of print statement


    def create_output_directory(self, product_name_safe):
        """
        Creates the output directory for storing downloaded media files.
        
        :param product_name_safe: Safe product name for directory naming
        :return: Path to the created output directory
        """
        
        directory_name = f"{self.prefix} - {product_name_safe}" if self.prefix else product_name_safe  # Construct directory name with platform prefix if available
        output_dir = os.path.join(self.output_directory, directory_name)  # Construct full path for product output directory using instance output directory
        self.create_directory(os.path.abspath(output_dir), output_dir.replace(".", ""))  # Create directory with absolute path and cleaned relative name
        
        return output_dir  # Return the created output directory path


    def collect_assets(self, html_content: str, output_dir: str) -> Dict[str, str]:
        """
        Collects and downloads all assets (images, CSS, JS) from the page.

        :param html_content: Rendered HTML string
        :param output_dir: Directory to save assets
        :return: Dictionary mapping original URLs to local paths
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Collecting page assets...{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate that page instance exists before collecting assets
            return {}  # Return empty dictionary when page is not available

        assets_dir = os.path.join(output_dir, "assets")  # Construct path for assets subdirectory
        self.create_directory(assets_dir, "assets")  # Create assets subdirectory
        
        asset_map: Dict[str, str] = {}  # Maps original URL to local path  # Initialize empty dictionary to map original URLs to local paths
        soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object

        img_tags = soup.find_all("img", src=True)  # Find all image tags with src attribute
        for idx, img in enumerate(img_tags, 1):  # Iterate through each image tag with index starting from 1
            if not isinstance(img, Tag):  # Ensure the element is a BeautifulSoup Tag before accessing attributes
                continue  # Skip non-Tag elements (e.g., NavigableString) to avoid attribute errors
            src_attr = img.get("src")  # Get the src attribute value from image tag
            if src_attr and isinstance(src_attr, str):  # Validate that src is a non-empty string
                src = str(src_attr)  # Ensure it's a string  # Cast src to string for consistency
                absolute_url = urljoin(self.product_url, src)  # Convert relative URL to absolute URL
                try:  # Attempt to download image with error handling
                    response = self.page.goto(absolute_url, timeout=10000)  # Navigate to image URL to download it
                    if response and response.ok:  # Verify if response is successful
                        parsed_url = urlparse(absolute_url)  # Parse URL to extract components
                        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"  # Extract file extension or use default .jpg
                        filename = f"image_{idx}{ext}"  # Generate filename with index and extension
                        filepath = os.path.join(assets_dir, filename)  # Construct full file path for saving
                        
                        with open(filepath, "wb") as f:  # Open file in binary write mode
                            f.write(response.body())  # Write response body to file
                        
                        asset_map[src] = f"assets/{filename}"  # Map original URL to local relative path
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded: {filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                except Exception as e:  # Catch any exceptions during download
                    verbose_output(  # Log download failure with error
                        f"{BackgroundColors.YELLOW}Failed to download {src}: {e}{Style.RESET_ALL}"
                    )  # End of verbose output call

        verbose_output(  # Log total number of assets collected
            f"{BackgroundColors.GREEN}Collected {len(asset_map)} assets.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return asset_map  # Return dictionary mapping URLs to local paths


    def save_snapshot(self, html_content: str, output_dir: str, asset_map: Dict[str, str]) -> Optional[str]:
        """
        Saves the complete page snapshot with localized asset references.

        :param html_content: Rendered HTML string
        :param output_dir: Directory to save the snapshot
        :param asset_map: Dictionary mapping original URLs to local paths
        :return: Path to saved HTML file or None if failed
        """

        verbose_output(  # Output status message to user
            f"{BackgroundColors.GREEN}Saving page snapshot...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt to save snapshot with error handling
            modified_html = html_content  # Create copy of HTML content for modification
            for original_url, local_path in asset_map.items():  # Iterate through each URL to local path mapping
                modified_html = modified_html.replace(original_url, local_path)  # Replace original URL with local path in HTML
            
            snapshot_path = os.path.join(output_dir, "page.html")  # Construct path for snapshot HTML file
            with open(snapshot_path, "w", encoding="utf-8") as f:  # Open file in write mode with UTF-8 encoding
                f.write(modified_html)  # Write modified HTML content to file
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Snapshot saved: {snapshot_path}{Style.RESET_ALL}"
            )  # End of verbose output call
            
            return snapshot_path  # Return path to saved snapshot file
            
        except Exception as e:  # Catch any exceptions during snapshot saving
            print(f"{BackgroundColors.RED}Failed to save snapshot: {e}{Style.RESET_ALL}")  # Alert user about snapshot saving failure
            return None  # Return None to indicate save operation failed


    def create_product_description_file(self, product_data: Dict[str, Any], output_dir: str, product_name_safe: str, url: str) -> Optional[str]:
        """
        Creates a text file with product description and details.
        
        :param product_data: Dictionary with product information
        :param output_dir: Directory to save the file
        :param product_name_safe: Safe product name for filename
        :param url: Original product URL
        :return: Path to the created description file or None if failed
        """
        
        try:  # Attempt to create description file with error handling
            description_file_path = os.path.join(output_dir, f"{product_name_safe}_description.txt")  # Construct path for description text file
            
            current_price = f"{product_data.get('current_price_integer', '0')},{product_data.get('current_price_decimal', '00')}"  # Format current price from dictionary values
            old_price_int = product_data.get('old_price_integer', 'N/A')  # Get old price integer part or default
            old_price_dec = product_data.get('old_price_decimal', 'N/A')  # Get old price decimal part or default
            
            if old_price_int != 'N/A' and old_price_dec != 'N/A':  # Verify if old price components are available
                old_price = f"{old_price_int},{old_price_dec}"  # Format old price from components
            else:  # Handle case when old price is not available
                old_price = "N/A"  # Use N/A as old price placeholder
            
            discount = product_data.get('discount_percentage', 'N/A')  # Get discount percentage or default
            
            description_text = product_data.get('description', 'No description available')  # Product description with fallback
            try:  # Attempt to convert description to sentence case with error handling
                description_text = self.to_sentence_case(description_text)  # Convert description to sentence case for better readability
            except Exception:  # Catch any exceptions during sentence case conversion
                pass  # If conversion fails, use original description text without modification

            content = PRODUCT_DESCRIPTION_TEMPLATE.format(  # Format template with product data
                product_name=product_data.get('name', 'Unknown Product'),  # Product name with fallback
                current_price=current_price,  # Formatted current price
                old_price=old_price,  # Formatted old price or N/A
                discount=discount,  # Discount percentage or N/A
                description=description_text,  # Sentence-cased product description
                url=url  # Original product URL
            )  # End of format method call
            
            with open(description_file_path, "w", encoding="utf-8") as f:  # Open file in write mode with UTF-8 encoding
                f.write(content)  # Write formatted content to file
            
            verbose_output(  # Output success message to user
                f"{BackgroundColors.GREEN}Description file created: {description_file_path}{Style.RESET_ALL}"
            )  # End of verbose output call
            
            return description_file_path  # Return path to created description file
            
        except Exception as e:  # Catch any exceptions during file creation
            print(f"{BackgroundColors.RED}Failed to create description file: {e}{Style.RESET_ALL}")  # Alert user about file creation failure
            return None  # Return None to indicate creation failed


    def to_sentence_case(self, text: str) -> str:
        """
        Converts text to sentence case (first letter of each sentence uppercase).

        :param text: The text to convert
        :return: Text in sentence case
        """

        if not text:  # Validate that text is not empty before processing
            return text  # Return original text if it's empty or None

        sentences = re.split(r"([.!?]\s*)", text)  # Keep the delimiters

        result = []  # Initialize list to hold processed sentences
        for i, sentence in enumerate(sentences):  # Iterate through each sentence with index
            if sentence.strip():  # Process only non-empty sentences
                if i % 2 == 0:  # Even indices are the actual sentence content
                    sentence = sentence.strip()  # Remove leading/trailing whitespace
                    if sentence:  # Ensure sentence is not empty after stripping
                        sentence = sentence[0].upper() + sentence[1:].lower()  # Capitalize first letter and lowercase the rest
                result.append(sentence)  # Append processed sentence or delimiter to result list

        return "".join(result)  # Join all sentences and delimiters back into a single string


    def download_single_image(self, img_url: str, output_dir: str, image_count: int) -> Optional[str]:
        """
        Downloads or copies a single image to the specified output directory.
        Supports HTTP downloads and local file copying for offline mode.
        
        :param img_url: URL of the image to download (HTTP URL or local path)
        :param output_dir: Directory to save the image
        :param image_count: Counter for generating unique filenames
        :return: Path to downloaded image file or None if download failed
        """
        
        try:  # Attempt to download or copy the image with error handling
            if self.local_html_path and (img_url.startswith("./") or img_url.startswith("../") or img_url.startswith("/file/") or not img_url.startswith(("http://", "https://"))):
                html_dir = os.path.dirname(os.path.abspath(self.local_html_path))  # Get directory of local HTML file
                
                if img_url.startswith("/file/"):  # Shopee local file format
                    img_url = "." + img_url  # Convert to relative path
                
                local_img_path = os.path.normpath(os.path.join(html_dir, img_url))  # Resolve local image path
                
                if not os.path.exists(local_img_path):  # Check if local image file exists
                    verbose_output(  # Log warning about missing file
                        f"{BackgroundColors.YELLOW}Local image file not found: {local_img_path}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return None  # Return None if file not found
                
                ext = os.path.splitext(local_img_path)[1]  # Get file extension
                if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:  # If extension is missing or not common image format
                    ext = ".jpg"  # Default to jpg
                
                filename = f"image_{image_count:03d}{ext}"  # Generate filename with index and extension
                filepath = os.path.join(output_dir, filename)  # Create full path for image file
                
                shutil.copy2(local_img_path, filepath)  # Copy local image to output directory
                
                verbose_output(  # Log successful copy
                    f"{BackgroundColors.GREEN}Copied image: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return filepath  # Return file path
                
            else:  # HTTP download mode
                if not img_url.startswith(("http://", "https://")):
                    img_url = "https:" + img_url if img_url.startswith("//") else "https://down-br.img.susercontent.com" + img_url
                
                if self.page:  # If browser is available
                    response = self.page.goto(img_url, timeout=10000)  # Navigate to image URL
                    if response and response.ok:  # Verify response is successful
                        parsed_url = urlparse(img_url)  # Parse URL
                        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"  # Get extension or default
                        filename = f"image_{image_count:03d}{ext}"  # Generate filename
                        filepath = os.path.join(output_dir, filename)  # Create full path
                        
                        with open(filepath, "wb") as f:  # Open file in binary write mode
                            f.write(response.body())  # Write response body to file
                        
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded image: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        return filepath  # Return file path
                else:  # Browser not available, use requests (for offline mode edge cases)
                    import requests  # Import requests for fallback
                    response = requests.get(img_url, timeout=10)  # Download image
                    if response.status_code == 200:  # Verify success
                        parsed_url = urlparse(img_url)  # Parse URL
                        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"  # Get extension
                        filename = f"image_{image_count:03d}{ext}"  # Generate filename
                        filepath = os.path.join(output_dir, filename)  # Create full path
                        
                        with open(filepath, "wb") as f:  # Open file in binary write mode
                            f.write(response.content)  # Write content to file
                        
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded image: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        return filepath  # Return file path
        
        except Exception as e:  # Catch any exceptions during download
            verbose_output(  # Log error
                f"{BackgroundColors.RED}Error downloading/copying image: {e}{Style.RESET_ALL}"
            )  # End of verbose output call
            return None  # Return None on failure


    def download_single_video(self, video_url: str, output_dir: str, video_count: int) -> Optional[str]:
        """
        Downloads or copies a single video to the specified output directory.
        Supports HLS (.m3u8) downloads using ffmpeg, HTTP downloads, and local file copying.
        
        :param video_url: URL of the video to download (HLS .m3u8, HTTP URL, or local path)
        :param output_dir: Directory to save the video
        :param video_count: Counter for generating unique filenames
        :return: Path to downloaded video file or None if download failed
        """
        
        video_path = None  # Initialize video path variable
        is_hls = video_url.endswith(".m3u8")  # Check if video URL is HLS stream
        
        try:  # Attempt to download or copy the video with error handling
            if self.local_html_path and (video_url.startswith("./") or video_url.startswith("../") or not video_url.startswith(("http://", "https://"))):
                html_dir = os.path.dirname(os.path.abspath(self.local_html_path))  # Get directory of local HTML file
                local_video_path = os.path.normpath(os.path.join(html_dir, video_url))  # Resolve local video path
                
                if not os.path.exists(local_video_path):  # Check if local video file exists
                    verbose_output(  # Log warning about missing file
                        f"{BackgroundColors.YELLOW}Local video file not found: {local_video_path}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return None  # Return None if file not found
                
                ext = os.path.splitext(local_video_path)[1]  # Get file extension
                if not ext or ext not in [".mp4", ".webm", ".mov", ".avi"]:  # If extension is missing or not common video format
                    ext = ".mp4"  # Default to mp4
                
                filename = f"video_{video_count:03d}{ext}"  # Generate filename with index and extension
                video_path = os.path.join(output_dir, filename)  # Create full path for video file
                
                shutil.copy2(local_video_path, video_path)  # Copy local video to output directory
                
                verbose_output(  # Log successful copy
                    f"{BackgroundColors.GREEN}Copied video: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return video_path  # Return file path
            
            if self.local_html_path and video_url.startswith(("http://", "https://")):
                html_dir = os.path.dirname(os.path.abspath(self.local_html_path))  # Get directory of local HTML file
                images_dir = os.path.join(html_dir, "images")  # Get images subdirectory path
                
                video_filename = os.path.basename(urlparse(video_url).path)  # Extract filename from URL
                if video_filename:  # If filename was extracted
                    local_video_in_images = os.path.join(images_dir, video_filename)  # Check in images directory
                    
                    if os.path.exists(local_video_in_images):  # Check if video exists in images directory
                        verbose_output(  # Log found in images directory
                            f"{BackgroundColors.GREEN}Found video in images/ subdirectory: {video_filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        ext = os.path.splitext(local_video_in_images)[1]  # Get file extension
                        if not ext or ext not in [".mp4", ".webm", ".mov", ".avi"]:  # If extension is missing or not common video format
                            ext = ".mp4"  # Default to mp4
                        
                        filename = f"video_{video_count:03d}{ext}"  # Generate filename with index and extension
                        video_path = os.path.join(output_dir, filename)  # Create full path for video file
                        
                        shutil.copy2(local_video_in_images, video_path)  # Copy local video to output directory
                        
                        verbose_output(  # Log successful copy
                            f"{BackgroundColors.GREEN}Copied video from images/: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        return video_path  # Return file path
            
            if is_hls:  # HLS streaming format - requires ffmpeg
                verbose_output(  # Log HLS detection
                    f"{BackgroundColors.CYAN}Detected HLS stream (.m3u8), using ffmpeg...{Style.RESET_ALL}"
                )  # End of verbose output call
                
                try:  # Try to download HLS stream with ffmpeg
                    filename = f"video_{video_count:03d}.mp4"  # Output filename (mp4 container)
                    video_path = os.path.join(output_dir, filename)  # Create full path
                    
                    ffmpeg_cmd = [  # Construct ffmpeg command
                        "ffmpeg",
                        "-i", video_url,  # Input HLS URL
                        "-c", "copy",  # Copy codec (no re-encoding)
                        "-bsf:a", "aac_adtstoasc",  # AAC bitstream filter
                        "-y",  # Overwrite output file if exists
                        video_path  # Output file path
                    ]
                    
                    result = subprocess.run(  # Run ffmpeg command
                        ffmpeg_cmd,  # Command to execute
                        capture_output=True,  # Capture stdout and stderr
                        text=True,  # Decode output as text
                        timeout=300  # 5 minute timeout
                    )
                    
                    if result.returncode == 0:  # Check if command succeeded
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded HLS video: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        return video_path  # Return file path
                    else:  # ffmpeg command failed
                        print(f"{BackgroundColors.RED}ffmpeg failed: {result.stderr}{Style.RESET_ALL}")  # Log error
                        return None  # Return None on failure
                        
                except FileNotFoundError:  # ffmpeg not installed
                    print(f"{BackgroundColors.RED}ffmpeg not found. Please install ffmpeg to download HLS videos.{Style.RESET_ALL}")  # Alert user
                    return None  # Return None on failure
                except subprocess.TimeoutExpired:  # ffmpeg timeout
                    print(f"{BackgroundColors.RED}ffmpeg timeout after 5 minutes.{Style.RESET_ALL}")  # Alert user
                    return None  # Return None on failure
                    
            else:  # Regular HTTP video download
                if not video_url.startswith(("http://", "https://")):
                    video_url = "https:" + video_url if video_url.startswith("//") else "https:" + video_url
                
                if self.page:  # If browser is available
                    response = self.page.goto(video_url, timeout=30000)  # Navigate to video URL
                    if response and response.ok:  # Verify response is successful
                        ext = os.path.splitext(urlparse(video_url).path)[1] or ".mp4"  # Get extension
                        filename = f"video_{video_count:03d}{ext}"  # Generate filename
                        video_path = os.path.join(output_dir, filename)  # Create full path
                        
                        with open(video_path, "wb") as f:  # Open file in binary write mode
                            f.write(response.body())  # Write response body to file
                        
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded video: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        return video_path  # Return file path
                else:  # Browser not available, use requests
                    import requests  # Import requests for fallback
                    response = requests.get(video_url, timeout=30)  # Download video
                    if response.status_code == 200:  # Verify success
                        ext = os.path.splitext(urlparse(video_url).path)[1] or ".mp4"  # Get extension
                        filename = f"video_{video_count:03d}{ext}"  # Generate filename
                        video_path = os.path.join(output_dir, filename)  # Create full path
                        
                        with open(video_path, "wb") as f:  # Open file in binary write mode
                            f.write(response.content)  # Write content to file
                        
                        verbose_output(  # Log successful download
                            f"{BackgroundColors.GREEN}Downloaded video: {BackgroundColors.CYAN}{filename}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        
                        return video_path  # Return file path
        
        except Exception as e:  # Catch any exceptions during download
            verbose_output(  # Log error
                f"{BackgroundColors.RED}Error downloading/copying video: {e}{Style.RESET_ALL}"
            )  # End of verbose output call
            return None  # Return None on failure


    def download_product_images(self, soup: BeautifulSoup, output_dir: str) -> List[str]:
        """
        Downloads all product images from the gallery.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :param output_dir: Directory to save images
        :return: List of downloaded image file paths
        """
        
        downloaded_images: List[str] = []  # Initialize list to track downloaded images
        
        verbose_output(  # Log download start
            f"{BackgroundColors.GREEN}Downloading product images...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        image_urls = self.find_image_urls(soup)  # Get all image URLs from gallery
        
        for idx, img_url in enumerate(image_urls, 1):  # Iterate through each image URL
            filepath = self.download_single_image(img_url, output_dir, idx)  # Download image
            if filepath:  # If download successful
                downloaded_images.append(filepath)  # Add to downloaded list
        
        verbose_output(  # Log download summary
            f"{BackgroundColors.GREEN}Downloaded {BackgroundColors.CYAN}{len(downloaded_images)}{BackgroundColors.GREEN} images.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return downloaded_images  # Return list of downloaded image paths


    def download_product_videos(self, soup: BeautifulSoup, output_dir: str) -> List[str]:
        """
        Downloads all product videos from the gallery.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :param output_dir: Directory to save videos
        :return: List of downloaded video file paths
        """
        
        downloaded_videos: List[str] = []  # Initialize list to track downloaded videos
        
        verbose_output(  # Log download start
            f"{BackgroundColors.GREEN}Downloading product videos...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        video_urls = self.find_video_urls(soup)  # Get all video URLs from gallery
        
        for idx, video_url in enumerate(video_urls, 1):  # Iterate through each video URL
            filepath = self.download_single_video(video_url, output_dir, idx)  # Download video
            if filepath:  # If download successful
                downloaded_videos.append(filepath)  # Add to downloaded list
        
        verbose_output(  # Log download summary
            f"{BackgroundColors.GREEN}Downloaded {BackgroundColors.CYAN}{len(downloaded_videos)}{BackgroundColors.GREEN} videos.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return downloaded_videos  # Return list of downloaded video paths


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
