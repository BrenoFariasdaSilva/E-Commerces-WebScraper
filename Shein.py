"""
================================================================================
Shein Web Scraper
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-02-11
Description :
    This script provides a Shein class for scraping product information
    from Shein product pages using authenticated browser sessions. It extracts
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
    1. Import the Shein class in your main script.
    2. Create an instance with a product URL:
            scraper = Shein("https://br.shein.com/product-url")
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

import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import json  # For parsing JSON data from script tags
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import re  # For regular expressions
import requests  # For downloading images and videos from URLs
import shutil  # For copying local files
import subprocess  # For running ffmpeg commands
import sys  # For system-specific parameters and functions
import time  # For delays during page rendering
from bs4 import BeautifulSoup, Tag  # For parsing HTML content
from colorama import Style  # For coloring the terminal
from Logger import Logger  # For logging output to both terminal and file
from pathlib import Path  # For handling file paths
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError  # For browser automation
from product_utils import normalize_product_dir_name  # Centralized product dir name normalization
from typing import Optional, Dict, Any, List, Tuple, cast  # For type hints
from urllib.parse import urljoin, urlparse  # For URL manipulation

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

# Affiliate URL detection pattern (onelink short affiliate links)
AFFILIATE_URL_PATTERN = r"https?://onelink\.shein\.com/[A-Za-z0-9/]+"

# HTML Selectors Dictionary:
HTML_SELECTORS = {
    "product_name": [  # List of CSS selectors for product name in priority order
        ("span", {"class": "fsp-element"}),  # Shein product name span with specific class
        ("h1", {"class": "fsp-element"}),  # Shein product name heading with specific class (fallback)
        ("h1", {"class": re.compile(r".*product.*title.*", re.IGNORECASE)}),  # Generic product title pattern fallback
        ("h1", {}),  # Generic H1 heading as last resort fallback
    ],
    "current_price": [  # List of CSS selectors for current price in priority order
        ("div", {"id": "productMainPriceId"}),  # Shein current price container with specific ID
        ("div", {"class": "productPrice__main"}),  # Shein current price container with specific class (fallback)
        ("span", {"class": re.compile(r".*price.*current.*", re.IGNORECASE)}),  # Generic current price pattern fallback
        ("div", {"class": re.compile(r".*price.*", re.IGNORECASE)}),  # Generic price div as last resort fallback
    ],
    "old_price": [  # List of CSS selectors for old price in priority order
        ("p", {"class": "productEstimatedTagNewRetail__retail"}),  # Shein old price paragraph with specific class
        ("div", {"class": "productDiscountInfo__retail"}),  # Shein old price container with specific class (fallback)
        ("span", {"class": re.compile(r".*price.*original.*", re.IGNORECASE)}),  # Generic original price pattern fallback
        ("del", {}),  # Deleted text element for old price as last resort fallback
    ],
    "discount": [  # List of CSS selectors for discount percentage in priority order
        ("div", {"class": "productEstimatedTagNew__percent"}),  # Shein discount percentage div with specific class
        ("div", {"class": "productDiscountPercent"}),  # Shein discount percentage container with specific class (fallback)
        ("span", {"class": re.compile(r".*discount.*", re.IGNORECASE)}),  # Generic discount span fallback
        ("span", {"class": re.compile(r".*percent.*", re.IGNORECASE)}),  # Percentage span as last resort fallback
    ],
    "description": [  # List of CSS selectors for product description in priority order
        ("div", {"class": "product-intro__attr-list-text"}),  # Shein description container with specific class
        ("div", {"class": "product-intro__attr-des"}),  # Shein description container with attr-des class
        ("div", {"class": "product-intro__attr-list-text product-intro__attr-list-textMargin"}),  # Shein description container with attr-des class
        ("div", {"class": "product-intro__attr-wrap"}),  # Shein description container with attr-des class
        ("div", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Generic description pattern fallback
        ("p", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Paragraph element containing description as last resort fallback
    ],
    "gallery_images": [  # List of CSS selectors for product gallery images in priority order
        ("ul", {"class": re.compile(r"thumbs-picture.*one-picture__thumbs")}),  # Shein gallery thumbnails container with combined classes
        ("ul", {"class": "thumbs-picture"}),  # Shein gallery thumbnails container as fallback
        ("div", {"class": "darkreader darkreader--sync"}),  # DarkReader wrapper (when HTML saved with extension enabled)
        ("div", {"class": re.compile(r".*gallery.*", re.IGNORECASE)}),  # Generic gallery pattern as last resort fallback
    ],
    "shipping_options": [  # List of CSS selectors for shipping options in priority order
        ("div", {"class": "product-intro__size-radio"}),  # Shein shipping option radio buttons container
        ("div", {"class": re.compile(r".*shipping.*radio.*", re.IGNORECASE)}),  # Generic shipping radio pattern fallback
        ("div", {"class": re.compile(r".*envio.*", re.IGNORECASE)}),  # Portuguese "envio" (shipping) pattern as last resort fallback
    ],
}  # Dictionary containing all HTML selectors used for scraping product information

# Output Directory Constants:
OUTPUT_DIRECTORY = "./Outputs/"  # The base path to the output directory

# Browser Constants:
CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH", "")  # Path to Chrome profile
CHROME_EXECUTABLE_PATH = os.getenv("CHROME_EXECUTABLE_PATH", "")  # Path to Chrome executable
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"  # Headless mode flag
PAGE_LOAD_TIMEOUT = 30000  # 30 seconds timeout for page load
NETWORK_IDLE_TIMEOUT = 5000  # 5 seconds of network idle
SCROLL_PAUSE_TIME = 0.5  # Seconds to pause between scrolls
SCROLL_STEP = 300  # Pixels to scroll per step

# Template Constants:
PRODUCT_DESCRIPTION_TEMPLATE = """Product Name: {product_name}

Price: From R${current_price} to R${old_price} ({discount})

Description: {description}

🛒 Encontre na Shein:
👉 {url}"""  # Template for product description text file with placeholders

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

class Shein:
    """
    Web scraper class for extracting product information from Shein using authenticated browser sessions.

    :return: None
    """


    def __init__(self, url="", local_html_path=None, prefix="", output_directory=OUTPUT_DIRECTORY):
        """
        Initializes the Shein scraper with a product URL and optional local HTML file path.

        :param url: The URL of the Shein product page to scrape
        :param local_html_path: Optional path to a local HTML file for offline scraping
        :param prefix: Optional platform prefix for output directory naming (e.g., "Shein")
        :param output_directory: Output directory path for storing scraped data (defaults to OUTPUT_DIRECTORY constant)
        :return: None
        """

        self.url = url  # Store the URL of the product page to be scraped
        self.product_url = url  # Maintain separate copy of product URL for reference
        self.local_html_path = local_html_path  # Store path to local HTML file for offline scraping
        self.html_content = None  # Store HTML content for reuse (from browser or local file)
        self.product_data = {}  # Initialize empty dictionary to store extracted product data
        self.prefix = prefix  # Store the platform prefix for directory naming
        self.output_directory = output_directory  # Store the output directory path for this scraping session
        self.playwright = None  # Placeholder for Playwright instance
        self.browser = None  # Placeholder for browser instance
        self.page = None  # Placeholder for page object
        verbose_output(f"{BackgroundColors.GREEN}Shein scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}")
        if local_html_path:  # If local HTML file path is provided
            verbose_output(f"{BackgroundColors.GREEN}Offline mode enabled. Will read from: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}")


    def launch_browser(self):
        """
        Launches an authenticated Chrome browser using existing profile.

        :return: None
        """

        verbose_output(f"{BackgroundColors.GREEN}Launching authenticated Chrome browser...{Style.RESET_ALL}")
        try:  # Attempt to launch browser with error handling
            self.playwright = sync_playwright().start()  # Start Playwright synchronous context manager
            launch_options = {"headless": HEADLESS, "args": ["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage", "--no-sandbox"]}  # Configure browser launch options with anti-detection flags
            if CHROME_PROFILE_PATH:  # Verify if custom Chrome profile path is provided
                launch_options["args"].append(f"--user-data-dir={CHROME_PROFILE_PATH}")  # Add user data directory to browser arguments
                verbose_output(f"{BackgroundColors.GREEN}Using Chrome profile: {BackgroundColors.CYAN}{CHROME_PROFILE_PATH}{Style.RESET_ALL}")  # Log profile path being used
            if CHROME_EXECUTABLE_PATH:  # Verify if custom Chrome executable path is provided
                launch_options["executable_path"] = CHROME_EXECUTABLE_PATH  # Set custom executable path in launch options
                verbose_output(f"{BackgroundColors.GREEN}Using Chrome executable: {BackgroundColors.CYAN}{CHROME_EXECUTABLE_PATH}{Style.RESET_ALL}")  # Log executable path being used
            self.browser = self.playwright.chromium.launch(**launch_options)  # Launch Chromium browser with configured options
            if self.browser is None:  # Verify browser instance was created successfully
                raise Exception("Failed to initialize browser")  # Raise exception if browser initialization failed
            self.page = self.browser.new_page()  # Create new browser page/tab
            if self.page is None:  # Verify page instance was created successfully
                raise Exception("Failed to create page")  # Raise exception if page creation failed
            self.page.set_viewport_size({"width": 1920, "height": 1080})  # Set viewport dimensions to standard Full HD resolution
            verbose_output(f"{BackgroundColors.GREEN}Browser launched successfully.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{BackgroundColors.RED}Failed to launch browser: {e}{Style.RESET_ALL}")
            raise


    def close_browser(self):
        """
        Safely closes the browser and Playwright instances.

        :return: None
        """

        verbose_output(f"{BackgroundColors.GREEN}Closing browser...{Style.RESET_ALL}")
        try:  # Attempt to close browser resources with error handling
            if self.page:  # Verify if page instance exists before closing
                self.page.close()  # Close the browser page to release resources
            if self.browser:  # Verify if browser instance exists before closing
                self.browser.close()  # Close the browser to release resources
            if self.playwright:  # Verify if Playwright instance exists before stopping
                self.playwright.stop()  # Stop the Playwright instance
            verbose_output(f"{BackgroundColors.GREEN}Browser closed successfully.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{BackgroundColors.YELLOW}Warning during browser close: {e}{Style.RESET_ALL}")


    def load_page(self):
        """
        Loads the product page and waits for network idle.

        :return: True if successful, False otherwise
        """

        verbose_output(f"{BackgroundColors.GREEN}Loading page: {BackgroundColors.CYAN}{self.product_url}{Style.RESET_ALL}")
        if self.page is None:  # Validate that page instance exists before attempting to load
            print(f"{BackgroundColors.RED}Page instance not initialized.{Style.RESET_ALL}")  # Alert user that page is not ready
            return False  # Return failure status if page is not initialized
        try:  # Attempt page loading with error handling
            self.page.goto(self.product_url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")  # Navigate to product URL and wait for DOM to load
            self.page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)  # Wait for network to become idle indicating page is loaded
            verbose_output(f"{BackgroundColors.GREEN}Page loaded successfully.{Style.RESET_ALL}")
            return True  # Return success status after successful page load
        except PlaywrightTimeoutError:  # Handle timeout errors specifically
            print(f"{BackgroundColors.YELLOW}Page load timeout, continuing anyway...{Style.RESET_ALL}")  # Warn user about timeout but continue execution
            return True  # Return success despite timeout to allow scraping partial content
        except Exception as e:  # Catch any other exceptions during page loading
            print(f"{BackgroundColors.RED}Failed to load page: {e}{Style.RESET_ALL}")  # Alert user about page loading failure
            return False  # Return failure status for unhandled errors


    def auto_scroll(self):
        """
        Automatically scrolls the page to trigger lazy-loaded content.

        :return: None
        """

        verbose_output(f"{BackgroundColors.GREEN}Auto-scrolling to load lazy content...{Style.RESET_ALL}")
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
            verbose_output(f"{BackgroundColors.GREEN}Auto-scroll completed.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{BackgroundColors.YELLOW}Warning during auto-scroll: {e}{Style.RESET_ALL}")


    def wait_full_render(self):
        """
        Waits for the page to be fully rendered with all dynamic content.

        :return: None
        """

        verbose_output(f"{BackgroundColors.GREEN}Waiting for full page render...{Style.RESET_ALL}")
        if self.page is None:  # Validate that page instance exists before waiting
            print(f"{BackgroundColors.YELLOW}Warning: Page not initialized, skipping render wait.{Style.RESET_ALL}")  # Warn user that render wait will be skipped
            return  # Exit method early if page is not initialized
        try:  # Attempt waiting for render with error handling
            selectors_to_wait = ["h1", "div[class*='price']", "img"]  # Define list of key selectors to wait for
            for selector in selectors_to_wait:  # Iterate through each selector to ensure visibility
                try:  # Attempt to wait for selector with nested error handling
                    self.page.wait_for_selector(selector, timeout=5000, state="visible")  # Wait for selector to become visible
                except:  # Silently handle timeout if selector not found
                    pass  # Continue to next selector even if current one fails
            time.sleep(2)  # Additional wait time to ensure all dynamic content is rendered
            verbose_output(f"{BackgroundColors.GREEN}Page fully rendered.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{BackgroundColors.YELLOW}Warning during render wait: {e}{Style.RESET_ALL}")


    def get_rendered_html(self):
        """
        Gets the fully rendered HTML content after JavaScript execution.

        :return: Rendered HTML string or None if failed
        """

        verbose_output(f"{BackgroundColors.GREEN}Extracting rendered HTML...{Style.RESET_ALL}")
        if self.page is None:  # Validate that page instance exists before extracting HTML
            print(f"{BackgroundColors.RED}Page instance not initialized.{Style.RESET_ALL}")  # Alert user that page is not ready
            return None  # Return None to indicate extraction failed
        try:  # Attempt HTML extraction with error handling
            html = self.page.content()  # Extract fully rendered HTML content from page
            verbose_output(f"{BackgroundColors.GREEN}Rendered HTML extracted successfully.{Style.RESET_ALL}")
            return html  # Return extracted HTML content
        except Exception as e:  # Catch any exceptions during HTML extraction
            print(f"{BackgroundColors.RED}Failed to extract HTML: {e}{Style.RESET_ALL}")  # Alert user about extraction failure
            return None  # Return None to indicate extraction failed


    def read_local_html(self):
        """
        Reads HTML content from a local file for offline scraping.

        :return: HTML content string or None if failed
        """

        verbose_output(f"{BackgroundColors.GREEN}Reading local HTML file: {BackgroundColors.CYAN}{self.local_html_path}{Style.RESET_ALL}")
        try:  # Attempt to read file with error handling
            if not self.local_html_path:  # Verify if local HTML path is not set
                print(f"{BackgroundColors.RED}No local HTML path provided.{Style.RESET_ALL}")  # Alert user that path is missing
                return None  # Return None if path doesn't exist
            if not os.path.exists(self.local_html_path):  # Verify if file doesn't exist
                print(f"{BackgroundColors.RED}\nLocal HTML file not found: {BackgroundColors.CYAN}{self.local_html_path}{Style.RESET_ALL}")  # Alert user that file is missing
                return None  # Return None if file doesn't exist
            with open(self.local_html_path, "r", encoding="utf-8") as file:  # Open file with UTF-8 encoding
                html_content = file.read()  # Read entire file content
            verbose_output(f"{BackgroundColors.GREEN}Local HTML content loaded successfully.{Style.RESET_ALL}")
            return html_content  # Return the HTML content string
        except Exception as e:  # Catch any exceptions during file reading
            print(f"{BackgroundColors.RED}Error reading local HTML file: {e}{Style.RESET_ALL}")  # Alert user about file reading error
            return None  # Return None to indicate reading failed


    def extract_product_name(self, soup=None):
        """
        Extracts the product name from the parsed HTML soup.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product name string or "Unknown Product" if not found
        """

        if soup is None:  # Guard against None to satisfy static checkers and avoid attribute access on None
            return "Unknown Product"  # Return default when no soup provided
        for tag, attrs in HTML_SELECTORS["product_name"]:  # Iterate through each selector combination from centralized dictionary
            name_element = soup.find(tag, attrs if attrs else None)  # Search for element matching current selector
            if name_element:  # Verify if matching element was found
                    raw_product_name = name_element.get_text(separator=" ", strip=True)  # Extract raw text, preserve single spaces between parts
                    product_name = normalize_product_dir_name(raw_name=raw_product_name)  # Normalize name for directory usage
                    if product_name and product_name != "":  # Validate that extracted name is not empty
                        verbose_output(f"{BackgroundColors.GREEN}Product name: {BackgroundColors.CYAN}{product_name}{Style.RESET_ALL}")  # Log successfully extracted (formatted) product name
                        return product_name  # Return the sanitized, title-cased product name immediately when found
        verbose_output(f"{BackgroundColors.YELLOW}Product name not found, using default.{Style.RESET_ALL}")  # Warn that product name could not be extracted
        return "Unknown Product"  # Return default placeholder when name extraction fails


    def extract_current_price(self, soup=None):
        """
        Extracts the current price from the parsed HTML soup.
        PRIMARY: JSON promotionInfoPrice.amountWithSymbol extraction
        FALLBACK: HTML extraction

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for current price
        """

        if soup is None:  # Guard against None to avoid attribute access on None
            return "0", "00"  # Default price when no soup provided
        
        verbose_output(f"{BackgroundColors.GREEN}Trying JSON extraction for current price...{Style.RESET_ALL}")
        
        try:
            script_tags = soup.find_all("script", {"type": "application/json"})
            for script_tag in script_tags:
                try:
                    if not script_tag.string:  # Skip if no content
                        continue
                    
                    json_data = json.loads(script_tag.string)  # Parse JSON data
                    
                    if isinstance(json_data, dict):
                        promo_price = json_data.get("promotionInfoPrice", {})
                        if not promo_price and "detail" in json_data:
                            promo_price = json_data.get("detail", {}).get("promotionInfoPrice", {})
                        
                        amount_with_symbol = promo_price.get("amountWithSymbol", "")
                        
                        if amount_with_symbol and isinstance(amount_with_symbol, str):
                            match = re.search(r"(\d+)[,.](\d{2})", amount_with_symbol)
                            if match:
                                integer_part = match.group(1)
                                decimal_part = match.group(2)
                                verbose_output(f"{BackgroundColors.GREEN}Current price from JSON: R${integer_part},{decimal_part}{Style.RESET_ALL}")
                                return integer_part, decimal_part
                
                except (json.JSONDecodeError, AttributeError, TypeError, KeyError):
                    continue  # Skip invalid or incompatible JSON
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.YELLOW}Error extracting current price from JSON: {e}{Style.RESET_ALL}")
        
        verbose_output(f"{BackgroundColors.YELLOW}JSON current price not found, trying HTML extraction...{Style.RESET_ALL}")
        
        for tag, attrs in HTML_SELECTORS["current_price"]:  # Iterate through each selector combination from centralized dictionary
            price_element = soup.find(tag, attrs if attrs else None)  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = match.group(1)  # Extract integer part of price
                    decimal_part = match.group(2)  # Extract decimal part of price
                    verbose_output(f"{BackgroundColors.GREEN}Current price from HTML: R${integer_part},{decimal_part}{Style.RESET_ALL}")  # Log successfully extracted current price
                    return integer_part, decimal_part  # Return price components as tuple
        
        verbose_output(f"{BackgroundColors.YELLOW}Current price not found, using default.{Style.RESET_ALL}")  # Warn that current price could not be extracted
        return "0", "00"  # Return default zero price when extraction fails


    def extract_old_price(self, soup=None, current_price_int="0", current_price_dec="00", discount_percentage="N/A"):
        """
        Extracts the old price from the parsed HTML soup.
        PRIMARY: JSON originalPrice.amountWithSymbol extraction (with optimized recursive search)
        FALLBACK 1: HTML extraction
        FALLBACK 2: Compute from current price and discount (if available)

        :param soup: BeautifulSoup object containing the parsed HTML
        :param current_price_int: Current price integer part (for computational fallback)
        :param current_price_dec: Current price decimal part (for computational fallback)
        :param discount_percentage: Discount percentage string (for computational fallback)
        :return: Tuple of (integer_part, decimal_part) for old price
        """

        if soup is None:  # Guard against None to avoid attribute access on None
            return "N/A", "N/A"  # Default old price when no soup provided
        
        verbose_output(f"{BackgroundColors.GREEN}Trying JSON extraction for old price...{Style.RESET_ALL}")
        
        try:
            script_tags = soup.find_all("script", {"type": "application/json"})
            for script_tag in script_tags:
                try:
                    if not script_tag.string:  # Skip if no content
                        continue
                    
                    if "originalPrice" not in script_tag.string:
                        continue  # Skip this script tag if it doesn't contain originalPrice
                    
                    verbose_output(f"{BackgroundColors.GREEN}Found JSON with 'originalPrice', parsing...{Style.RESET_ALL}")
                    json_data = json.loads(script_tag.string)  # Parse JSON data


                    def find_original_price(obj, depth=0, max_depth=15):
                        """Recursively search for originalPrice in nested structures"""
                        if depth > max_depth:  # Prevent infinite recursion
                            return None
                        
                        if isinstance(obj, dict):
                            if "originalPrice" in obj:
                                original_price = obj["originalPrice"]
                                if isinstance(original_price, dict):
                                    amount_with_symbol = original_price.get("amountWithSymbol", "")
                                    if amount_with_symbol and isinstance(amount_with_symbol, str):
                                        verbose_output(f"{BackgroundColors.GREEN}Found originalPrice.amountWithSymbol: {amount_with_symbol}{Style.RESET_ALL}")
                                        return amount_with_symbol
                            
                            for value in obj.values():
                                result = find_original_price(value, depth + 1, max_depth)
                                if result:
                                    return result
                        
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_original_price(item, depth + 1, max_depth)
                                if result:
                                    return result
                        
                        return None
                    
                    amount_with_symbol = find_original_price(json_data)
                    
                    if amount_with_symbol:
                        match = re.search(r"(\d+)[,.](\d{2})", amount_with_symbol)
                        if match:
                            integer_part = match.group(1)
                            decimal_part = match.group(2)
                            verbose_output(f"{BackgroundColors.GREEN}Old price from JSON: R${integer_part},{decimal_part}{Style.RESET_ALL}")
                            return integer_part, decimal_part
                
                except (json.JSONDecodeError, AttributeError, TypeError, KeyError) as e:
                    verbose_output(f"{BackgroundColors.YELLOW}Error parsing JSON script tag: {e}{Style.RESET_ALL}")
                    continue  # Skip invalid or incompatible JSON
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.YELLOW}Error extracting old price from JSON: {e}{Style.RESET_ALL}")
        
        verbose_output(f"{BackgroundColors.YELLOW}JSON old price not found, trying HTML extraction...{Style.RESET_ALL}")
        
        for tag, attrs in HTML_SELECTORS["old_price"]:  # Iterate through each selector combination from centralized dictionary
            price_element = soup.find(tag, attrs if attrs else None)  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = match.group(1)  # Extract integer part of price
                    decimal_part = match.group(2)  # Extract decimal part of price
                    verbose_output(f"{BackgroundColors.GREEN}Old price from HTML: R${integer_part},{decimal_part}{Style.RESET_ALL}")  # Log successfully extracted old price
                    return integer_part, decimal_part  # Return price components as tuple
        
        verbose_output(f"{BackgroundColors.YELLOW}HTML old price not found, trying computational method...{Style.RESET_ALL}")
        
        if current_price_int not in ["0", "N/A"] and discount_percentage not in ["N/A", ""]:
            try:
                discount_match = re.search(r"(\d+)%", discount_percentage)
                if discount_match:
                    discount_decimal = float(discount_match.group(1)) / 100.0  # Convert percentage to decimal (20% -> 0.20)
                    
                    current_price_float = float(f"{current_price_int}.{current_price_dec}")
                    
                    if discount_decimal < 1.0:  # Ensure discount is less than 100%
                        original_price_float = current_price_float / (1.0 - discount_decimal)
                        
                        original_price_float = round(original_price_float, 2)
                        
                        integer_part = str(int(original_price_float))
                        decimal_part = str(int((original_price_float % 1) * 100)).zfill(2)
                        
                        verbose_output(f"{BackgroundColors.GREEN}Old price calculated from current price and discount: R${integer_part},{decimal_part}{Style.RESET_ALL}")
                        return integer_part, decimal_part
            
            except (ValueError, ZeroDivisionError) as e:
                verbose_output(f"{BackgroundColors.YELLOW}Error calculating old price from discount: {e}{Style.RESET_ALL}")
        
        verbose_output(f"{BackgroundColors.YELLOW}Old price not found by any method.{Style.RESET_ALL}")  # Warn that old price could not be extracted
        return "N/A", "N/A"  # Return N/A when old price is not available


    def extract_discount_percentage(self, soup=None):
        """
        Extracts the discount percentage from the parsed HTML soup.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Discount percentage string or "N/A" if not found
        """

        if soup is None:  # Guard against None to avoid attribute access on None
            return "N/A"  # Default discount when no soup provided
        for tag, attrs in HTML_SELECTORS["discount"]:  # Iterate through each selector combination from centralized dictionary
            discount_element = soup.find(tag, attrs if attrs else None)  # Search for element matching current selector
            if discount_element:  # Verify if matching element was found
                discount_text = discount_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+%)", discount_text)  # Search for discount percentage pattern
                if match:  # Verify if discount pattern was found in text
                    verbose_output(f"{BackgroundColors.GREEN}Discount: {match.group(1)}{Style.RESET_ALL}")  # Log successfully extracted discount percentage
                    return match.group(1)  # Return the discount percentage string
        return "N/A"  # Return N/A when discount is not available


    def extract_product_description(self, soup=None):
        """
        Extracts the product description from the parsed HTML soup.
        First tries HTML extraction from class="product-intro__attr-list-text",
        then tries structured specification table extraction from common-entry__content,
        then tries goods_desc JSON field extraction from script tags.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product description string or "No description available" if not found
        """

        if soup is None:  # Guard against None to avoid attribute access on None
            return "No description available"  # Default description when no soup provided

        for tag, attrs in HTML_SELECTORS["description"]:  # Iterate through description selectors
            description_element = soup.find(tag, attrs if attrs else None)  # Find element for each selector
            if description_element:  # If an element was found
                description = description_element.get_text(strip=True)  # Extract and strip text
                description = self.to_sentence_case(description)  # Convert HTML description to sentence case
                if description and len(description) > 10:  # If description is sufficiently long
                    verbose_output(f"{BackgroundColors.GREEN}Description found from HTML ({len(description)} chars).{Style.RESET_ALL}")  # Log success
                    return description  # Return formatted HTML description

        verbose_output(f"{BackgroundColors.YELLOW}HTML description not found, trying structured specification extraction...{Style.RESET_ALL}")  # Notify about next fallback

        try:  # Attempt structured specification extraction
            specifications = []  # Collect valid label:value pairs
            script_tags = soup.find_all("script")  # Find all script tags in document
            verbose_output(f"{BackgroundColors.CYAN}Searching through {len(script_tags)} script tags for specification table...{Style.RESET_ALL}")  # Log script tag count
            
            for script_tag in script_tags:  # Iterate through each script tag
                if not script_tag.string:  # Skip script tags with no content
                    continue
                
                script_content = str(script_tag.string)  # Convert script content to string
                anchor_pos = script_content.find('class="common-entry__content"')  # Search for specification table anchor
                
                if anchor_pos == -1:  # Anchor not found in this script tag
                    continue
                
                verbose_output(f"{BackgroundColors.GREEN}Found specification table anchor in script tag.{Style.RESET_ALL}")  # Log anchor found
                
                start_pos = max(0, anchor_pos - 100)  # Start extraction slightly before anchor for context
                end_search = script_content.find('class="common-entry__content"', anchor_pos + 1)  # Look for next occurrence
                end_pos = end_search if end_search != -1 else anchor_pos + 50000  # Limit extraction window to 50KB
                fragment = script_content[start_pos:end_pos]  # Extract HTML fragment containing table
                
                verbose_output(f"{BackgroundColors.CYAN}Isolated table fragment ({len(fragment)} chars), parsing...{Style.RESET_ALL}")  # Log fragment size
                
                try:  # Parse isolated fragment
                    fragment_soup = BeautifulSoup(fragment, "html.parser")  # Parse fragment with BeautifulSoup
                    all_text_nodes = []  # Collect all text nodes from fragment
                    
                    for element in fragment_soup.descendants:  # Iterate through all descendant nodes
                        if isinstance(element, str):  # Check if node is text (NavigableString)
                            text = element.strip()  # Strip whitespace from text
                            if text and len(text) > 0:  # Only include non-empty text
                                all_text_nodes.append(text)  # Add to collection
                    
                    verbose_output(f"{BackgroundColors.CYAN}Extracted {len(all_text_nodes)} text nodes from fragment.{Style.RESET_ALL}")  # Log node count
                    
                    i = 0  # Initialize index for text node iteration
                    noise_keywords = ["Classificação", "Itens", "Seguidores", "pago", "seguido", "está navegando", "Vendas", "Avaliações"]  # Noise filters
                    seen_labels = set()  # Track seen labels to avoid duplicates
                    
                    while i < len(all_text_nodes):  # Process text nodes sequentially
                        current_text = all_text_nodes[i]  # Get current text node
                        
                        if any(noise in current_text for noise in noise_keywords):  # Check for noise keywords
                            i += 1  # Skip noise node
                            continue
                        
                        if ":" in current_text and len(current_text) < 50:  # Likely a label (short text with colon)
                            label = current_text.replace(":", "").strip()  # Extract label without colon
                            
                            if label in seen_labels:  # Check for duplicate label
                                i += 1  # Skip duplicate
                                continue
                            
                            if len(label) > 2:  # Validate label length
                                value_parts = []  # Collect value parts
                                j = i + 1  # Start looking for value in next nodes
                                
                                while j < len(all_text_nodes) and j < i + 5:  # Look ahead up to 5 nodes for value
                                    next_text = all_text_nodes[j]  # Get next text node
                                    
                                    if ":" in next_text and len(next_text) < 50:  # Stop if next label found
                                        break
                                    
                                    if len(next_text) > 0 and not any(noise in next_text for noise in noise_keywords):  # Valid value part
                                        value_parts.append(next_text)  # Add to value parts
                                        
                                        if len(" ".join(value_parts)) > 100:  # Stop if value is long enough
                                            break
                                    
                                    j += 1  # Move to next node
                                
                                if value_parts:  # If value parts found
                                    value = " ".join(value_parts).strip()  # Join value parts with space
                                    
                                    if len(value) > 0:  # Validate value is not empty
                                        specifications.append(f"{label}: {value}")  # Append formatted pair
                                        seen_labels.add(label)  # Mark label as seen
                                        verbose_output(f"{BackgroundColors.CYAN}Extracted pair: {label}: {value[:50]}...{Style.RESET_ALL}")  # Log extracted pair
                                        
                                        if "sku" in label.lower() or "skij" in label.lower():  # Check if SKU reached
                                            verbose_output(f"{BackgroundColors.GREEN}Reached SKU label, stopping extraction.{Style.RESET_ALL}")  # Log SKU reached
                                            break  # Stop extraction at SKU
                                
                                i = j  # Move index to where value ended
                            else:
                                i += 1  # Skip invalid label
                        else:
                            i += 1  # Move to next node
                    
                    break  # Exit script tag loop after processing first matching script
                    
                except Exception as parse_error:  # Catch fragment parsing errors
                    verbose_output(f"{BackgroundColors.YELLOW}Error parsing fragment: {parse_error}{Style.RESET_ALL}")  # Log parse error
                    continue  # Try next script tag
            
            if len(specifications) >= 3:  # Require at least 3 pairs to accept
                description = "\n".join(specifications)  # Join pairs with newline
                description = self.to_sentence_case(description)  # Convert structured specification description to sentence case
                verbose_output(f"{BackgroundColors.GREEN}Structured specifications extracted successfully ({len(specifications)} pairs, {len(description)} characters).{Style.RESET_ALL}")  # Log success with counts
                return description  # Return formatted structured description
            else:
                verbose_output(f"{BackgroundColors.YELLOW}Found only {len(specifications)} specifications, need at least 3. Continuing to JSON extraction...{Style.RESET_ALL}")  # Not enough pairs
                
        except Exception as e:  # Catch and log extraction errors
            verbose_output(f"{BackgroundColors.YELLOW}Error extracting structured specifications: {e}{Style.RESET_ALL}")  # Log exception

        verbose_output(f"{BackgroundColors.YELLOW}Structured specification extraction failed, trying goods_desc JSON extraction...{Style.RESET_ALL}")  # Proceed to goods_desc fallback

        try:  # Attempt goods_desc JSON extraction from script tags
            script_tags = soup.find_all("script")  # Find all script tags in document
            verbose_output(f"{BackgroundColors.CYAN}Searching through {len(script_tags)} script tags for goods_desc field...{Style.RESET_ALL}")  # Log search start
            
            for script_tag in script_tags:  # Iterate through each script tag
                if not script_tag.string:  # Skip script tags with no content
                    continue
                
                script_content = str(script_tag.string)  # Convert script content to string
                
                if '"goods_desc"' in script_content or "'goods_desc'" in script_content:  # Check if goods_desc field exists
                    verbose_output(f"{BackgroundColors.GREEN}Found goods_desc field in script tag, parsing JSON...{Style.RESET_ALL}")  # Log field found
                    
                    try:  # Parse JSON data
                        json_data = json.loads(script_content)  # Parse script content as JSON
                        
                        if isinstance(json_data, dict) and "goods_desc" in json_data:  # Check if goods_desc exists in parsed data
                            goods_desc = json_data["goods_desc"]  # Extract goods_desc value
                            goods_desc = self.to_sentence_case(goods_desc)  # Convert goods_desc to sentence case
                            if goods_desc and len(goods_desc) > 10:  # Validate description length
                                verbose_output(f"{BackgroundColors.GREEN}goods_desc extracted successfully ({len(goods_desc)} chars).{Style.RESET_ALL}")  # Log success
                                return goods_desc  # Return formatted goods_desc content
                        
                    except json.JSONDecodeError:  # Handle JSON parsing errors
                        verbose_output(f"{BackgroundColors.YELLOW}Failed to parse JSON in script tag.{Style.RESET_ALL}")  # Log parse failure
                        continue  # Try next script tag
                    except Exception as parse_error:  # Handle other parsing errors
                        verbose_output(f"{BackgroundColors.YELLOW}Error parsing goods_desc: {parse_error}{Style.RESET_ALL}")  # Log error
                        continue  # Try next script tag
            
            verbose_output(f"{BackgroundColors.YELLOW}goods_desc field not found or invalid.{Style.RESET_ALL}")  # Log failure
                
        except Exception as e:  # Catch and log extraction errors
            verbose_output(f"{BackgroundColors.YELLOW}Error extracting goods_desc: {e}{Style.RESET_ALL}")  # Log exception

        verbose_output(f"{BackgroundColors.YELLOW}All description extraction methods failed.{Style.RESET_ALL}")  # Log complete failure

        return "No description available"  # Return default when no description found


    def detect_international(self, soup=None) -> bool:
        """
        Detects whether the product has only international shipping available.
        Checks for "Envio Nacional" (National Shipping) availability.
        If "Envio Nacional" is sold out or not available, and "International" is active/available, returns True.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: True if only international shipping is available, False otherwise
        """
        
        if soup is None:  # Guard against None to avoid attribute access on None
            verbose_output(f"{BackgroundColors.YELLOW}No soup provided for shipping detection.{Style.RESET_ALL}")  # Log missing soup
            return False  # Default to False

        try:  # Begin detection
            for tag, attrs in HTML_SELECTORS["shipping_options"]:  # Iterate shipping selectors
                shipping_elements = soup.find_all(tag, attrs if attrs else None)  # Find matching elements
                if not shipping_elements:  # No elements for this selector
                    continue  # Try next selector

                verbose_output(f"{BackgroundColors.GREEN}Found {len(shipping_elements)} shipping option elements.{Style.RESET_ALL}")  # Log count

                national_available = False  # Flag: national available
                national_soldout = False  # Flag: national sold out
                international_available = False  # Flag: international available
                international_soldout = False  # Flag: international sold out

                for element in shipping_elements:  # Iterate found elements
                    aria = element.get("aria-label")  # Read aria-label
                    if aria is None:  # Missing aria-label
                        continue  # Skip element

                    classes = element.get("class") or []  # Get class list
                    is_soldout = any("_soldout" in c for c in classes)  # Detect sold-out via class

                    if aria == "Envio Nacional":  # Exact match national
                        if is_soldout:  # If marked sold out
                            national_soldout = True  # Mark sold out
                            verbose_output(f"{BackgroundColors.YELLOW}Found 'Envio Nacional' marked sold out.{Style.RESET_ALL}")  # Log sold out
                        else:  # Available
                            national_available = True  # Mark available
                            verbose_output(f"{BackgroundColors.GREEN}Found available 'Envio Nacional'.{Style.RESET_ALL}")  # Log available

                    elif aria == "International":  # Exact match international
                        if is_soldout:  # If marked sold out
                            international_soldout = True  # Mark sold out
                            verbose_output(f"{BackgroundColors.YELLOW}Found 'International' marked sold out.{Style.RESET_ALL}")  # Log sold out
                        else:  # Available
                            international_available = True  # Mark available
                            verbose_output(f"{BackgroundColors.GREEN}Found available 'International'.{Style.RESET_ALL}")  # Log available

                if (not national_available) and international_available:  # National not available and international available
                    self.product_data["INTERNATIONAL_ONLY"] = True  # Set international-only
                    self.product_data.pop("OUT_OF_STOCK", None)  # Clear out_of_stock
                    verbose_output(f"{BackgroundColors.YELLOW}Product has ONLY international shipping.{Style.RESET_ALL}")  # Log result
                    return True  # Return True

                if national_available and international_available:  # Both available
                    self.product_data["INTERNATIONAL_ONLY"] = False  # Not international-only
                    self.product_data.pop("OUT_OF_STOCK", None)  # Clear out_of_stock
                    verbose_output(f"{BackgroundColors.GREEN}Product has both national and international shipping available.{Style.RESET_ALL}")  # Log result
                    return False  # Return False

                if (national_soldout or (not national_available)) and (international_soldout or (not international_available)) and (national_soldout or international_soldout):  # Both unavailable
                    self.product_data["OUT_OF_STOCK"] = True  # Mark out of stock
                    self.product_data["INTERNATIONAL_ONLY"] = False  # Clear international-only
                    verbose_output(f"{BackgroundColors.RED}Both shipping options are sold out — treating product as OUT_OF_STOCK.{Style.RESET_ALL}")  # Log out of stock
                    return False  # Return False

                if national_available:  # National available only or detected
                    self.product_data["INTERNATIONAL_ONLY"] = False  # Not international-only
                    self.product_data.pop("OUT_OF_STOCK", None)  # Clear out_of_stock
                    verbose_output(f"{BackgroundColors.GREEN}National shipping available or detected; not international-only.{Style.RESET_ALL}")  # Log national available
                    return False  # Return False

            verbose_output(f"{BackgroundColors.YELLOW}No shipping options found.{Style.RESET_ALL}")  # No shipping elements found
            return False  # Preserve behavior when missing

        except Exception as e:  # Unexpected error
            verbose_output(f"{BackgroundColors.RED}Error detecting international shipping: {e}{Style.RESET_ALL}")  # Log exception
            return False  # Default to False on error


    def find_image_urls(self, soup=None) -> List[str]:
        """
        Extracts all image URLs from the product gallery.
        Only extracts preload image links that appear BEFORE the canonical link tag.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of image URLs (absolute URLs or relative paths for offline mode)
        """
        
        if soup is None:  # Guard against None to avoid attribute access on None
            verbose_output(f"{BackgroundColors.YELLOW}No soup provided for image extraction.{Style.RESET_ALL}")
            return []  # Return empty list when no soup provided
        
        image_urls = []
        
        images_dir = None
        if self.local_html_path:
            html_dir = os.path.dirname(os.path.abspath(self.local_html_path))
            potential_images_dir = os.path.join(html_dir, "images")
            if os.path.exists(potential_images_dir) and os.path.isdir(potential_images_dir):
                images_dir = potential_images_dir
                verbose_output(f"{BackgroundColors.GREEN}Found local images directory: {images_dir}{Style.RESET_ALL}")
        
        try:
            canonical_link = soup.find("link", {"rel": "canonical"})
            
            all_preload_links = soup.find_all("link", {"rel": "preload", "as": "image"})
            verbose_output(f"{BackgroundColors.GREEN}Found {len(all_preload_links)} total preload image links.{Style.RESET_ALL}")
            
            product_image_links = []
            if canonical_link:
                for link in all_preload_links:
                    if link.sourceline and canonical_link.sourceline:
                        if link.sourceline < canonical_link.sourceline:
                            product_image_links.append(link)
                    else:
                        all_links = soup.find_all("link")
                        preload_idx = all_links.index(link) if link in all_links else -1
                        canonical_idx = all_links.index(canonical_link) if canonical_link in all_links else -1
                        if preload_idx != -1 and canonical_idx != -1 and preload_idx < canonical_idx:
                            product_image_links.append(link)
                
                verbose_output(f"{BackgroundColors.GREEN}Filtered to {len(product_image_links)} product image preload links (before canonical link).{Style.RESET_ALL}")
            else:
                product_image_links = all_preload_links
                verbose_output(f"{BackgroundColors.YELLOW}No canonical link found, using all preload links.{Style.RESET_ALL}")
            
            if product_image_links:
                for link in product_image_links:
                    href = link.get("href")
                    if href:
                        if "_thumbnail_220x293" in href:
                            href = href.replace("_thumbnail_220x293", "_thumbnail_900x")
                        
                        if self.local_html_path and images_dir:
                            filename = os.path.basename(urlparse(href).path)
                            local_file_path = os.path.join(images_dir, filename)
                            
                            if os.path.exists(local_file_path):
                                relative_path = f"./images/{filename}"
                                image_urls.append(relative_path)
                                verbose_output(f"{BackgroundColors.GREEN}Using local image: {filename}{Style.RESET_ALL}")
                            else:
                                if not href.startswith(("http://", "https://")):
                                    href = urljoin(self.url if self.url else "https://www.shein.com", href)
                                image_urls.append(href)
                                verbose_output(f"{BackgroundColors.YELLOW}Image not local, will download: {filename}{Style.RESET_ALL}")
                        else:
                            if not href.startswith(("http://", "https://")):
                                href = urljoin(self.url, href)
                            image_urls.append(href)
                
                if image_urls:
                    seen = set()
                    unique_urls = []
                    for url in image_urls:
                        if url not in seen:
                            seen.add(url)
                            unique_urls.append(url)
                    image_urls = unique_urls
                    verbose_output(f"{BackgroundColors.GREEN}Extracted {len(image_urls)} unique product image URLs.{Style.RESET_ALL}")
                    return image_urls
            
            for tag, attrs in HTML_SELECTORS["gallery_images"]:  # Iterate through each selector combination
                gallery_container = soup.find(tag, attrs if attrs else None)
                if gallery_container:
                    verbose_output(f"{BackgroundColors.GREEN}Found gallery container.{Style.RESET_ALL}")
                    
                    gallery_items = gallery_container.find_all("li", {"class": re.compile(r"thumbs-picture__column")})
                    
                    if gallery_items:
                        verbose_output(f"{BackgroundColors.GREEN}Found {len(gallery_items)} gallery items.{Style.RESET_ALL}")
                        
                        for item in gallery_items:  # Process each gallery item
                            img_tag = item.find("img")
                            if img_tag:
                                img_src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-before-crop-src")
                                if img_src:
                                    if not img_src.startswith(("http://", "https://", "data:")):
                                        if self.local_html_path:
                                            image_urls.append(img_src)
                                        else:
                                            img_src = urljoin(self.url, img_src)
                                            image_urls.append(img_src)
                                    else:
                                        image_urls.append(img_src)
                    else:
                        img_tags = gallery_container.find_all("img")
                        for img_tag in img_tags:
                            img_src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-before-crop-src")
                            if img_src:
                                if not img_src.startswith(("http://", "https://", "data:")):
                                    if self.local_html_path:
                                        image_urls.append(img_src)
                                    else:
                                        img_src = urljoin(self.url, img_src)
                                        image_urls.append(img_src)
                                else:
                                    image_urls.append(img_src)
                    
                    if image_urls:
                        verbose_output(f"{BackgroundColors.GREEN}Extracted {len(image_urls)} image URLs from gallery.{Style.RESET_ALL}")
                        return image_urls  # Return images once found
            
            verbose_output(f"{BackgroundColors.YELLOW}No gallery images found.{Style.RESET_ALL}")
            return []  # Return empty list if no images found
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.RED}Error extracting image URLs: {e}{Style.RESET_ALL}")
            return []  # Return empty list on error


    def find_video_urls(self, soup=None) -> List[str]:
        """
        Extracts all video URLs from the product gallery.
        Searches for video elements or JSON data containing video information.

        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of video URLs (absolute URLs or relative paths for offline mode)
        """
        
        if soup is None:  # Guard against None to avoid attribute access on None
            verbose_output(f"{BackgroundColors.YELLOW}No soup provided for video extraction.{Style.RESET_ALL}")
            return []  # Return empty list when no soup provided
        
        video_urls = []
        
        try:
            video_tags = soup.find_all("video")
            for video_tag in video_tags:
                video_src = video_tag.get("src")
                if video_src:
                    if not video_src.startswith(("http://", "https://")):
                        if self.local_html_path:
                            video_urls.append(video_src)
                        else:
                            video_src = urljoin(self.url, video_src)
                            video_urls.append(video_src)
                    else:
                        video_urls.append(video_src)
                
                source_tags = video_tag.find_all("source")
                for source_tag in source_tags:
                    src = source_tag.get("src")
                    if src and src not in video_urls:
                        if not src.startswith(("http://", "https://")):
                            if self.local_html_path:
                                video_urls.append(src)
                            else:
                                src = urljoin(self.url, src)
                                video_urls.append(src)
                        else:
                            video_urls.append(src)
            
            script_tags = soup.find_all("script", {"type": "application/json"})
            for script_tag in script_tags:
                try:
                    json_data = json.loads(script_tag.string)
                    if isinstance(json_data, dict):
                        video_url = self.extract_video_from_json(json_data)
                        if video_url and video_url not in video_urls:
                            video_urls.append(video_url)
                except (json.JSONDecodeError, AttributeError, TypeError):
                    continue  # Skip invalid JSON
            
            if video_urls:
                verbose_output(f"{BackgroundColors.GREEN}Extracted {len(video_urls)} video URLs.{Style.RESET_ALL}")
            else:
                verbose_output(f"{BackgroundColors.YELLOW}No videos found in gallery.{Style.RESET_ALL}")
            
            return video_urls
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.RED}Error extracting video URLs: {e}{Style.RESET_ALL}")
            return []  # Return empty list on error


    def extract_video_from_json(self, data: Any) -> Optional[str]:
        """
        Helper method to recursively search for video URLs in JSON data.

        :param data: JSON data (dict, list, or primitive)
        :return: First video URL found, or None
        """
        
        if isinstance(data, dict):
            for key in ["video", "videoUrl", "video_url", "url", "src", "source"]:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and (".mp4" in value or ".m3u8" in value or "video" in value):
                        return value
            
            for value in data.values():
                result = self.extract_video_from_json(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            for item in data:
                result = self.extract_video_from_json(item)
                if result:
                    return result
        
        return None


    def print_product_info(self, product_data=None):
        """
        Prints the extracted product information in a formatted manner.

        :param product_data: Dictionary containing the scraped product data
        :return: None
        """

        if not product_data:  # Verify if product data dictionary is empty or None
            print(f"{BackgroundColors.RED}No product data to display.{Style.RESET_ALL}")  # Alert user that no data is available
            return  # Exit method early when no data to print
        verbose_output(f"{BackgroundColors.GREEN}Product information extracted successfully:{BackgroundColors.GREEN}\n  {BackgroundColors.CYAN}Name:{BackgroundColors.GREEN} {product_data.get('name', 'N/A')}\n  {BackgroundColors.CYAN}Old Price:{BackgroundColors.GREEN} R${product_data.get('old_price_integer', 'N/A')},{product_data.get('old_price_decimal', 'N/A') if product_data.get('old_price_integer', 'N/A') != 'N/A' else 'N/A'}\n  {BackgroundColors.CYAN}Current Price:{BackgroundColors.GREEN} R${product_data.get('current_price_integer', 'N/A')},{product_data.get('current_price_decimal', 'N/A')}\n  {BackgroundColors.CYAN}Discount:{BackgroundColors.GREEN} {product_data.get('discount_percentage', 'N/A')}\n  {BackgroundColors.CYAN}Description:{BackgroundColors.GREEN} {product_data.get('description', 'N/A')[:100]}...{Style.RESET_ALL}")


    def scrape_product_info(self, html_content=""):
        """
        Scrapes product information from rendered HTML content.

        :param html_content: Rendered HTML string
        :return: Dictionary containing the scraped product data
        """

        verbose_output(f"{BackgroundColors.GREEN}Parsing product information...{Style.RESET_ALL}")
        try:  # Attempt to parse product information with error handling
            soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object
            product_name = self.extract_product_name(soup)  # Extract product name from parsed HTML
            current_price_int, current_price_dec = self.extract_current_price(soup)  # Extract current price integer and decimal parts
            discount_percentage = self.extract_discount_percentage(soup)  # Extract discount percentage value
            old_price_int, old_price_dec = self.extract_old_price(soup, current_price_int, current_price_dec, discount_percentage)  # Extract old price with computational fallback
            description = self.extract_product_description(soup)  # Extract product description text
            is_international = self.detect_international(soup)  # Detect if product has only international shipping
            self.product_data = {"name": product_name, "current_price_integer": current_price_int, "current_price_decimal": current_price_dec, "old_price_integer": old_price_int, "old_price_decimal": old_price_dec, "discount_percentage": discount_percentage, "description": description, "url": self.product_url, "is_international": is_international}  # Store all extracted data in dictionary
            self.print_product_info(self.product_data)  # Display extracted product information to user
            return self.product_data  # Return complete product data dictionary
        except Exception as e:  # Catch any exceptions during parsing
            print(f"{BackgroundColors.RED}Error parsing product info: {e}{Style.RESET_ALL}")  # Alert user about parsing error
            return None  # Return None to indicate parsing failed


    def create_directory(self, full_directory_name="", relative_directory_name=""):
        """
        Creates a directory if it does not exist.

        :param full_directory_name: Full path of the directory to be created
        :param relative_directory_name: Relative name of the directory for terminal display
        :return: None
        """

        verbose_output(true_string=f"{BackgroundColors.GREEN}Creating the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory...{Style.RESET_ALL}")
        if os.path.isdir(full_directory_name):  # Verify if directory already exists
            return  # Exit early if directory exists to avoid redundant creation
        try:  # Attempt directory creation with error handling
            os.makedirs(full_directory_name)  # Create directory including all intermediate directories
        except OSError:  # Catch OS-level errors during directory creation
            print(f"{BackgroundColors.GREEN}The creation of the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory failed.{Style.RESET_ALL}")  # Alert user about directory creation failure


    def create_output_directory(self, product_name_safe=""):
        """
        Creates the output directory for storing downloaded media files.

        :param product_name_safe: Safe product name for directory naming
        :return: Path to the created output directory
        """

        directory_name = f"{self.prefix} - {product_name_safe}" if self.prefix else product_name_safe  # Construct directory name with platform prefix if available
        output_dir = os.path.join(self.output_directory, directory_name)  # Construct full path for product output directory using instance output directory
        self.create_directory(os.path.abspath(output_dir), output_dir.replace(".", ""))  # Create directory with absolute path and cleaned relative name
        return output_dir  # Return the created output directory path


    def collect_assets(self, html_content="", output_dir=""):
        """
        Collects and downloads all assets (images, CSS, JS) from the page.

        :param html_content: Rendered HTML string
        :param output_dir: Directory to save assets
        :return: Dictionary mapping original URLs to local paths
        """

        verbose_output(f"{BackgroundColors.GREEN}Collecting page assets...{Style.RESET_ALL}")
        if self.page is None:  # Validate that page instance exists before collecting assets
            return {}  # Return empty dictionary when page is not available
        assets_dir = os.path.join(output_dir, "assets")  # Construct path for assets subdirectory
        self.create_directory(assets_dir, "assets")  # Create assets subdirectory
        asset_map = {}  # Initialize empty dictionary to map original URLs to local paths
        soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object
        img_tags = soup.find_all("img", src=True)  # Find all image tags with src attribute
        for idx, img in enumerate(img_tags, 1):  # Iterate through each image tag with index starting from 1
            if not isinstance(img, Tag):  # Ensure element is a Tag before accessing attributes
                continue  # Skip non-Tag nodes (e.g., NavigableString)
            src_attr = img.get("src")  # Get the src attribute value from image tag
            if src_attr and isinstance(src_attr, str):  # Validate that src is a non-empty string
                src = str(src_attr)  # Cast src to string for consistency
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
                        verbose_output(f"{BackgroundColors.GREEN}Downloaded: {filename}{Style.RESET_ALL}")  # Log successful download
                except Exception as e:  # Catch any exceptions during download
                    verbose_output(f"{BackgroundColors.YELLOW}Failed to download {src}: {e}{Style.RESET_ALL}")  # Log download failure with error
        verbose_output(f"{BackgroundColors.GREEN}Collected {len(asset_map)} assets.{Style.RESET_ALL}")  # Log total number of assets collected
        return asset_map  # Return dictionary mapping URLs to local paths


    def save_snapshot(self, html_content="", output_dir="", asset_map=None):
        """
        Saves the complete page snapshot with localized asset references.

        :param html_content: Rendered HTML string
        :param output_dir: Directory to save the snapshot
        :param asset_map: Dictionary mapping original URLs to local paths
        :return: Path to saved HTML file or None if failed
        """

        verbose_output(f"{BackgroundColors.GREEN}Saving page snapshot...{Style.RESET_ALL}")
        if asset_map is None:  # Verify if asset_map parameter was not provided
            asset_map = {}  # Initialize empty dictionary as default
        try:  # Attempt to save snapshot with error handling
            modified_html = html_content  # Create copy of HTML content for modification
            for original_url, local_path in asset_map.items():  # Iterate through each URL to local path mapping
                modified_html = modified_html.replace(original_url, local_path)  # Replace original URL with local path in HTML
            snapshot_path = os.path.join(output_dir, "page.html")  # Construct path for snapshot HTML file
            with open(snapshot_path, "w", encoding="utf-8") as f:  # Open file in write mode with UTF-8 encoding
                f.write(modified_html)  # Write modified HTML content to file
            verbose_output(f"{BackgroundColors.GREEN}Snapshot saved: {snapshot_path}{Style.RESET_ALL}")
            return snapshot_path  # Return path to saved snapshot file
        except Exception as e:  # Catch any exceptions during snapshot saving
            print(f"{BackgroundColors.RED}Failed to save snapshot: {e}{Style.RESET_ALL}")  # Alert user about snapshot saving failure
            return None  # Return None to indicate save operation failed


    def create_product_description_file(self, product_data, output_dir, product_name_safe, url):
        """
        Creates a text file with product description and details.
        
        :param product_data: Dictionary with product information
        :param output_dir: Directory to save the file
        :param product_name_safe: Safe product name for filename
        :param url: Original product URL
        :return: Path to the created description file or None if failed
        """
        
        try:  # Try to create the .txt file
            product_name = product_data.get("name", "Produto")  # Get product name
            if isinstance(product_name, str):
                product_name = product_name.title()

            if isinstance(product_name, str) and product_name.strip().lower() == "unknown product":  # If product name is "Unknown Product", don't create file
                verbose_output(
                    f"{BackgroundColors.YELLOW}Skipping description file creation for Unknown Product.{Style.RESET_ALL}"
                )
                return None  # Return None
            
            description = product_data.get("description", "")  # Get description
            if description:  # If description exists
                description = self.clean_description(description)  # Clean description
                description = self.to_sentence_case(description)  # Convert to sentence case
            
            old_price_int = product_data.get("old_price_integer", "0")  # Get old price integer
            old_price_dec = product_data.get("old_price_decimal", "00")  # Get old price decimal
            current_price_int = product_data.get("current_price_integer", "0")  # Get current price integer
            current_price_dec = product_data.get("current_price_decimal", "00")  # Get current price decimal
            discount = product_data.get("discount_percentage", "N/A")  # Get discount percentage
            
            old_price = f"{old_price_int},{old_price_dec}" if old_price_int != "N/A" else "N/A"  # Format old price
            current_price = f"{current_price_int},{current_price_dec}"  # Format current price
            
            template_content = PRODUCT_DESCRIPTION_TEMPLATE.format(
                product_name=product_name,
                current_price=current_price,
                old_price=old_price,
                discount=discount,
                description=description,
                url=url
            )  # Format the template with product data
            
            txt_filename = f"{product_name_safe}_description.txt"  # Create .txt filename
            txt_filepath = os.path.join(output_dir, txt_filename)  # Create .txt file path
            
            with open(txt_filepath, "w", encoding="utf-8") as f:  # Write file with UTF-8 encoding
                f.write(template_content)  # Write content
            
            verbose_output(
                f"{BackgroundColors.GREEN}✓ Created product description file: {BackgroundColors.CYAN}{txt_filename}{Style.RESET_ALL}"
            )  # Output success
            
            return txt_filepath  # Return the file path
            
        except Exception as e:  # If error creating .txt file
            print(
                f"{BackgroundColors.YELLOW}Warning: Could not create product description file: {e}{Style.RESET_ALL}"
            )  # Output warning
            return None  # Return None on failure


    def clean_description(self, text):
        """
        Cleans and preprocesses the product description by removing markdown formatting
        and excessive empty lines.
        
        :param text: The raw description text
        :return: Cleaned description text
        """
        
        if not text:  # If text is empty
            return text  # Return as is
        
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Remove markdown bold formatting
        
        text = re.sub(r"\n{3,}", "\n\n", text)  # Replace 3 or more newlines with 2 newlines
        
        lines = text.split("\n")  # Split into lines
        cleaned_lines = []  # List to store cleaned lines
        for line in lines:  # Iterate through lines
            cleaned_line = line.strip()  # Strip leading/trailing whitespace
            if cleaned_line or (cleaned_lines and cleaned_lines[-1]):  # Keep single empty lines between paragraphs
                cleaned_lines.append(cleaned_line)  # Add cleaned line
        
        text = "\n".join(cleaned_lines)  # Join cleaned lines
        text = re.sub(r"\n{3,}", "\n\n", text)  # Ensure no more than 2 consecutive newlines
        
        return text.strip()  # Return cleaned text
    
    
    def to_sentence_case(self, text=""):
        """
        Converts text to sentence case (first letter of each sentence uppercase).

        :param text: The text to convert
        :return: Text in sentence case
        """

        if not text:  # Validate that input text is not empty or None
            return text  # Return original text if it's empty to avoid unnecessary processing

        sentences = re.split(r"([.!?]\s*)", text)  # Split text into sentences while keeping delimiters
        result = []  # Initialize list to hold processed sentences
        for i, sentence in enumerate(sentences):  # Iterate through each sentence with index for processing
            if sentence.strip():  # Check if sentence has non-whitespace content before processing
                if i % 2 == 0:  # Process only the actual sentences, not the delimiters
                    sentence = sentence.strip()  # Remove leading and trailing whitespace from sentence
                    if sentence:  # Validate that sentence is not empty after stripping
                        sentence = sentence[0].upper() + sentence[1:].lower()  # Convert first character to uppercase and the rest to lowercase for sentence case formatting
                result.append(sentence)  # Add processed sentence or delimiter back to result list

        return "".join(result)  # Join all processed sentences and delimiters back into a single string and return it


    def download_single_image(self, image_url: str, output_dir: str, index: int) -> Optional[str]:
        """
        Downloads a single product image from URL or copies from local path.
        Supports both online (HTTP) and offline (local file) modes.

        :param image_url: URL or relative path of the image
        :param output_dir: Directory where the image should be saved
        :param index: Index number for the image filename
        :return: Path to the downloaded image file, or None if download failed
        """
        
        try:
            if self.local_html_path and not image_url.startswith(("http://", "https://")):
                local_html_dir = os.path.dirname(self.local_html_path)
                source_path = os.path.join(local_html_dir, image_url.lstrip("./"))
                
                if not os.path.exists(source_path):
                    verbose_output(f"{BackgroundColors.RED}Local image file not found: {source_path}{Style.RESET_ALL}")
                    return None
                
                _, ext = os.path.splitext(source_path)
                if not ext:
                    ext = ".jpg"  # Default extension
                
                dest_path = os.path.join(output_dir, f"image_{index:02d}{ext}")
                
                shutil.copy2(source_path, dest_path)
                verbose_output(f"{BackgroundColors.GREEN}Copied local image {index} to {dest_path}{Style.RESET_ALL}")
                return dest_path
            
            else:
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                
                ext = os.path.splitext(urlparse(image_url).path)[1]
                if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    content_type = response.headers.get("content-type", "")
                    if "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"
                    elif "png" in content_type:
                        ext = ".png"
                    elif "webp" in content_type:
                        ext = ".webp"
                    elif "gif" in content_type:
                        ext = ".gif"
                    else:
                        ext = ".jpg"  # Default
                
                dest_path = os.path.join(output_dir, f"image_{index:02d}{ext}")
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                
                verbose_output(f"{BackgroundColors.GREEN}Downloaded image {index} to {dest_path}{Style.RESET_ALL}")
                return dest_path
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.RED}Error downloading image {index}: {e}{Style.RESET_ALL}")
            return None


    def download_single_video(self, video_url: str, output_dir: str, index: int) -> Optional[str]:
        """
        Downloads a single product video from URL or copies from local path.
        Supports HLS streams (.m3u8), direct video files (.mp4), and local files.

        :param video_url: URL or relative path of the video
        :param output_dir: Directory where the video should be saved
        :param index: Index number for the video filename
        :return: Path to the downloaded video file, or None if download failed
        """
        
        try:
            if self.local_html_path and not video_url.startswith(("http://", "https://")):
                local_html_dir = os.path.dirname(self.local_html_path)
                source_path = os.path.join(local_html_dir, video_url.lstrip("./"))
                
                if not os.path.exists(source_path):
                    verbose_output(f"{BackgroundColors.RED}Local video file not found: {source_path}{Style.RESET_ALL}")
                    return None
                
                _, ext = os.path.splitext(source_path)
                if not ext:
                    ext = ".mp4"  # Default extension
                
                dest_path = os.path.join(output_dir, f"video_{index:02d}{ext}")
                
                shutil.copy2(source_path, dest_path)
                verbose_output(f"{BackgroundColors.GREEN}Copied local video {index} to {dest_path}{Style.RESET_ALL}")
                return dest_path
            
            else:
                dest_path = os.path.join(output_dir, f"video_{index:02d}.mp4")
                
                if ".m3u8" in video_url:
                    verbose_output(f"{BackgroundColors.CYAN}Downloading HLS video {index} using ffmpeg...{Style.RESET_ALL}")
                    
                    try:
                        result = subprocess.run(
                            [
                                "ffmpeg",
                                "-i", video_url,
                                "-c", "copy",
                                "-bsf:a", "aac_adtstoasc",
                                "-y",  # Overwrite output file
                                dest_path
                            ],
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        
                        if result.returncode == 0 and os.path.exists(dest_path):
                            verbose_output(f"{BackgroundColors.GREEN}Downloaded HLS video {index} to {dest_path}{Style.RESET_ALL}")
                            return dest_path
                        else:
                            verbose_output(f"{BackgroundColors.RED}ffmpeg failed: {result.stderr}{Style.RESET_ALL}")
                            return None
                    
                    except FileNotFoundError:
                        verbose_output(f"{BackgroundColors.RED}ffmpeg not found. Please install ffmpeg to download HLS videos.{Style.RESET_ALL}")
                        return None
                    except subprocess.TimeoutExpired:
                        verbose_output(f"{BackgroundColors.RED}ffmpeg timeout while downloading video {index}.{Style.RESET_ALL}")
                        return None
                
                else:
                    verbose_output(f"{BackgroundColors.CYAN}Downloading video {index}...{Style.RESET_ALL}")
                    response = requests.get(video_url, timeout=60, stream=True)
                    response.raise_for_status()
                    
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    verbose_output(f"{BackgroundColors.GREEN}Downloaded video {index} to {dest_path}{Style.RESET_ALL}")
                    return dest_path
        
        except Exception as e:
            verbose_output(f"{BackgroundColors.RED}Error downloading video {index}: {e}{Style.RESET_ALL}")
            return None


    def download_product_images(self, image_urls: List[str], output_dir: str) -> List[str]:
        """
        Downloads all product images from the gallery.

        :param image_urls: List of image URLs or relative paths
        :param output_dir: Directory where images should be saved
        :return: List of paths to successfully downloaded image files
        """
        
        downloaded_images = []
        
        if not image_urls:
            verbose_output(f"{BackgroundColors.YELLOW}No image URLs to download.{Style.RESET_ALL}")
            return downloaded_images
        
        verbose_output(f"{BackgroundColors.CYAN}Downloading {len(image_urls)} images...{Style.RESET_ALL}")
        
        for idx, image_url in enumerate(image_urls, start=1):
            image_path = self.download_single_image(image_url, output_dir, idx)
            if image_path:
                downloaded_images.append(image_path)
        
        verbose_output(f"{BackgroundColors.GREEN}Successfully downloaded {len(downloaded_images)} of {len(image_urls)} images.{Style.RESET_ALL}")
        return downloaded_images


    def download_product_videos(self, video_urls: List[str], output_dir: str) -> List[str]:
        """
        Downloads all product videos from the gallery.

        :param video_urls: List of video URLs or relative paths
        :param output_dir: Directory where videos should be saved
        :return: List of paths to successfully downloaded video files
        """
        
        downloaded_videos = []
        
        if not video_urls:
            verbose_output(f"{BackgroundColors.YELLOW}No video URLs to download.{Style.RESET_ALL}")
            return downloaded_videos
        
        verbose_output(f"{BackgroundColors.CYAN}Downloading {len(video_urls)} videos...{Style.RESET_ALL}")
        
        for idx, video_url in enumerate(video_urls, start=1):
            video_path = self.download_single_video(video_url, output_dir, idx)
            if video_path:
                downloaded_videos.append(video_path)
        
        verbose_output(f"{BackgroundColors.GREEN}Successfully downloaded {len(downloaded_videos)} of {len(video_urls)} videos.{Style.RESET_ALL}")
        return downloaded_videos


    def download_media(self):
        """
        Downloads product media and creates snapshot.
        Works for both online (browser) and offline (local HTML) modes.
        Extracts and downloads gallery images and videos separately.

        :return: List of downloaded file paths
        """

        verbose_output(f"{BackgroundColors.GREEN}Processing product media...{Style.RESET_ALL}")
        downloaded_files = []  # Initialize empty list to track downloaded file paths
        try:  # Attempt media download with error handling
            if not self.product_data or not self.product_data.get("name"):  # Validate that product data with name exists
                print(f"{BackgroundColors.RED}No product data available for media download.{Style.RESET_ALL}")  # Alert user that required data is missing
                return downloaded_files  # Return empty list when data is unavailable
            
            product_name = self.product_data.get("name", "Unknown Product")  # Get product name or use default
            
            html_content = self.html_content  # Use stored HTML content (from browser or local file)
            if not html_content:  # Verify if HTML content is unavailable
                print(f"{BackgroundColors.RED}No HTML content available.{Style.RESET_ALL}")  # Alert user about HTML unavailability
                return downloaded_files  # Return empty list when HTML is unavailable
            
            soup = BeautifulSoup(html_content, "lxml")  # Parse HTML content with lxml parser
            
            is_international = self.detect_international(soup)
            if is_international and not product_name.startswith("International"):
                product_name = f"International - {product_name}"
                self.product_data["name"] = product_name  # Update product data with prefixed name
                verbose_output(f"{BackgroundColors.YELLOW}Product name prefixed with 'International'.{Style.RESET_ALL}")
            
            output_dir = self.create_output_directory(product_name)  # Create output directory for product
            
            image_urls = self.find_image_urls(soup)
            if image_urls:
                verbose_output(f"{BackgroundColors.CYAN}Found {len(image_urls)} images in gallery.{Style.RESET_ALL}")
                image_paths = self.download_product_images(image_urls, output_dir)
                downloaded_files.extend(image_paths)  # Add all downloaded image paths
            else:
                verbose_output(f"{BackgroundColors.YELLOW}No gallery images found.{Style.RESET_ALL}")
            
            video_urls = self.find_video_urls(soup)
            if video_urls:
                verbose_output(f"{BackgroundColors.CYAN}Found {len(video_urls)} videos in gallery.{Style.RESET_ALL}")
                video_paths = self.download_product_videos(video_urls, output_dir)
                downloaded_files.extend(video_paths)  # Add all downloaded video paths
            else:
                verbose_output(f"{BackgroundColors.YELLOW}No gallery videos found.{Style.RESET_ALL}")
            
            if not self.local_html_path:  # Only collect assets and save snapshot when not using a provided local HTML
                asset_map = self.collect_assets(html_content, output_dir)  # Download and collect all page assets
                snapshot_path = self.save_snapshot(html_content, output_dir, asset_map)  # Save HTML snapshot with localized assets
                if snapshot_path:  # Verify if snapshot was saved successfully
                    downloaded_files.append(snapshot_path)  # Add snapshot path to downloaded files list
            
            description_file = self.create_product_description_file(self.product_data, output_dir, product_name, self.product_url)  # Create product description text file
            if description_file:  # Verify if description file was created successfully
                downloaded_files.append(description_file)  # Add description file path to downloaded files list
            
            verbose_output(f"{BackgroundColors.GREEN}Media processing completed. {len(downloaded_files)} files saved.{Style.RESET_ALL}")
        except Exception as e:  # Catch any exceptions during media download
            print(f"{BackgroundColors.RED}Error during media download: {e}{Style.RESET_ALL}")  # Alert user about media download error
        return downloaded_files  # Return list of all downloaded file paths


    def scrape(self, verbose=False):
        """
        Main scraping method that orchestrates the entire scraping process.
        Supports both online scraping (via browser) and offline scraping (from local HTML file).

        :param verbose: Boolean flag to enable verbose output
        :return: Dictionary containing all scraped data and downloaded file paths
        """

        verbose_output(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Starting {BackgroundColors.CYAN}Shein{BackgroundColors.GREEN} Scraping process...{Style.RESET_ALL}")
        try:  # Attempt scraping process with error handling
            if self.local_html_path:  # If local HTML file path is provided
                verbose_output(f"{BackgroundColors.GREEN}Using offline mode with local HTML file{Style.RESET_ALL}")
                html_content = self.read_local_html()  # Read HTML content from local file
                if not html_content:  # Verify if HTML reading failed
                    return None  # Return None if HTML is unavailable
                self.html_content = html_content  # Store HTML content for later use
            else:  # Online scraping mode
                verbose_output(f"{BackgroundColors.GREEN}Using online mode with browser automation{Style.RESET_ALL}")
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
            verbose_output(f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Shein scraping completed successfully!{Style.RESET_ALL}")
            return product_info  # Return complete product information with downloaded files
        except Exception as e:  # Catch any exceptions during scraping process
            print(f"{BackgroundColors.RED}Scraping failed: {e}{Style.RESET_ALL}")  # Alert user about scraping failure
            return None  # Return None to indicate scraping failed
        finally:  # Always execute cleanup regardless of success or failure
            if not self.local_html_path:  # Only close browser in online mode
                self.close_browser()  # Close browser and release resources


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


def output_result(result=None):
    """
    Outputs the scraping result to the terminal.

    :param result: The result dictionary to be outputted
    :return: None
    """

    if result:  # Verify if result dictionary is not None or empty
        print(f"{BackgroundColors.GREEN}Scraping successful! Product data:{Style.RESET_ALL}\n  {BackgroundColors.CYAN}Name:{Style.RESET_ALL} {result.get('name', 'N/A')}\n  {BackgroundColors.CYAN}Price:{Style.RESET_ALL} R${result.get('current_price_integer', 'N/A')},{result.get('current_price_decimal', 'N/A')}\n  {BackgroundColors.CYAN}Files:{Style.RESET_ALL} {len(result.get('downloaded_files', []))} downloaded")  # Display formatted success message with product data
    else:  # Handle case when result is None or empty
        print(f"{BackgroundColors.RED}Scraping failed. No data returned.{Style.RESET_ALL}")  # Display failure message


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

    print(
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Shein Scraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n",
    )
    
    start_time = datetime.datetime.now()  # Record the start time of the program execution

    test_url = "https://br.shein.com/product-example"  # Test URL
    
    verbose_output(
        f"{BackgroundColors.GREEN}Testing Shein scraper with URL: {BackgroundColors.CYAN}{test_url}{Style.RESET_ALL}\n"
    )
    
    try:  # Attempt to run scraper with error handling to catch any exceptions during the test
        scraper = Shein(test_url)  # Create instance of Shein scraper with test URL
        result = scraper.scrape()  # Run the scraping process and store the result
        output_result(result)  # Output the scraping result to the terminal
    except Exception as e:  # Catch any exceptions that occur during the scraping test
        print(f"{BackgroundColors.RED}Error during test: {e}{Style.RESET_ALL}")

    finish_time = datetime.datetime.now()  # Record the finish time of the program execution
    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )
    print(
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )
    
    (
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None
    )


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
