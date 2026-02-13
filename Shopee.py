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
        return "Unknown Product"  # Return default placeholder when name extraction fails


    def extract_current_price(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """
        Extracts the current price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for current price
        """
        
        # Try multiple selectors for Shopee prices
        price_selectors = [  # Define list of CSS selectors to find current price in priority order
            ("div", {"class": re.compile(r".*price.*current.*", re.IGNORECASE)}),  # Shopee current price container with regex pattern
            ("div", {"class": re.compile(r".*price.*sale.*", re.IGNORECASE)}),  # Alternative sale price container with regex pattern
            ("span", {"class": re.compile(r".*price.*", re.IGNORECASE)}),  # Generic price span as fallback
        ]  # End of price_selectors list
        
        for tag, attrs in price_selectors:  # Iterate through each selector combination
            price_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                # Extract numeric values from price text
                match = re.search(r"(\d+)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = match.group(1)  # Extract integer part of price
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
        
        # Try multiple selectors for Shopee old prices
        price_selectors = [  # Define list of CSS selectors to find old price in priority order
            ("div", {"class": re.compile(r".*price.*original.*", re.IGNORECASE)}),  # Shopee original price container with regex pattern
            ("div", {"class": re.compile(r".*price.*before.*", re.IGNORECASE)}),  # Alternative before discount price container with regex pattern
            ("span", {"class": re.compile(r".*old.*price.*", re.IGNORECASE)}),  # Generic old price span as fallback
        ]  # End of price_selectors list
        
        for tag, attrs in price_selectors:  # Iterate through each selector combination
            price_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if price_element:  # Verify if matching element was found
                price_text = price_element.get_text(strip=True)  # Extract and clean text content from element
                match = re.search(r"(\d+)[,.](\d{2})", price_text)  # Search for price pattern with integer and decimal parts
                if match:  # Verify if price pattern was found in text
                    integer_part = match.group(1)  # Extract integer part of price
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
        
        # Try multiple selectors for discount
        discount_selectors = [  # Define list of CSS selectors to find discount percentage in priority order
            ("div", {"class": re.compile(r".*discount.*", re.IGNORECASE)}),  # Shopee discount container with regex pattern
            ("span", {"class": re.compile(r".*discount.*", re.IGNORECASE)}),  # Alternative discount span with regex pattern
            ("div", {"class": re.compile(r".*sale.*badge.*", re.IGNORECASE)}),  # Sale badge container as fallback
        ]  # End of discount_selectors list
        
        for tag, attrs in discount_selectors:  # Iterate through each selector combination
            discount_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if discount_element:  # Verify if matching element was found
                discount_text = discount_element.get_text(strip=True)  # Extract and clean text content from element
                # Look for percentage pattern
                match = re.search(r"(\d+%)", discount_text)  # Search for discount percentage pattern
                if match:  # Verify if discount pattern was found in text
                    verbose_output(  # Log successfully extracted discount percentage
                        f"{BackgroundColors.GREEN}Discount: {match.group(1)}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return match.group(1)  # Return the discount percentage string
        
        return "N/A"  # Return N/A when discount is not available


    def extract_product_description(self, soup: BeautifulSoup) -> str:
        """
        Extracts the product description from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product description string or "No description available" if not found
        """
        
        # Try multiple selectors for Shopee descriptions
        description_selectors = [  # Define list of CSS selectors to find product description in priority order
            ("div", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Shopee description container with regex pattern
            ("div", {"class": re.compile(r".*product.*detail.*", re.IGNORECASE)}),  # Alternative product detail container with regex pattern
            ("section", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Section element containing description as fallback
        ]  # End of description_selectors list
        
        for tag, attrs in description_selectors:  # Iterate through each selector combination
            description_element = soup.find(tag, attrs if attrs else None)  # type: ignore[arg-type]  # Search for element matching current selector
            if description_element:  # Verify if matching element was found
                description = description_element.get_text(strip=True)  # Extract and clean text content from element
                if description and len(description) > 10:  # Validate that description has substantial content
                    verbose_output(  # Log successfully extracted description with character count
                        f"{BackgroundColors.GREEN}Description found ({len(description)} chars).{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return description  # Return the product description
        
        return "No description available"  # Return default message when description is not found


    def print_product_info(self, product_data: Dict[str, Any]) -> None:
        """
        Prints the extracted product information in a formatted manner.
        
        :param product_data: Dictionary containing the scraped product data
        :return: None
        """
        
        if not product_data:  # Verify if product data dictionary is empty or None
            print(f"{BackgroundColors.RED}No product data to display.{Style.RESET_ALL}")  # Alert user that no data is available
            return  # Exit method early when no data to print
        
        print(  # Display formatted product information to user
            f"{BackgroundColors.GREEN}Product information extracted successfully:{Style.RESET_ALL}\n"
            f"  {BackgroundColors.CYAN}Name:{Style.RESET_ALL} {product_data.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Old Price:{Style.RESET_ALL} R${product_data.get('old_price_integer', 'N/A')},{product_data.get('old_price_decimal', 'N/A') if product_data.get('old_price_integer', 'N/A') != 'N/A' else 'N/A'}\n"
            f"  {BackgroundColors.CYAN}Current Price:{Style.RESET_ALL} R${product_data.get('current_price_integer', 'N/A')},{product_data.get('current_price_decimal', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Discount:{Style.RESET_ALL} {product_data.get('discount_percentage', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Description:{Style.RESET_ALL} {product_data.get('description', 'N/A')[:100]}..."
        )  # End of print statement


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
            
            # Extract all product information
            product_name = self.extract_product_name(soup)  # Extract product name from parsed HTML
            current_price_int, current_price_dec = self.extract_current_price(soup)  # Extract current price integer and decimal parts
            old_price_int, old_price_dec = self.extract_old_price(soup)  # Extract old price integer and decimal parts
            discount_percentage = self.extract_discount_percentage(soup)  # Extract discount percentage value
            description = self.extract_product_description(soup)  # Extract product description text
            
            self.product_data = {  # Store all extracted data in dictionary
                "name": product_name,  # Product name string
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
        
        output_dir = os.path.join(OUTPUT_DIRECTORY, product_name_safe)  # Construct full path for product output directory
        self.create_directory(os.path.abspath(output_dir), output_dir.replace(".", ""))  # Create directory with absolute path and cleaned relative name
        
        return output_dir  # Return the created output directory path


    def _collect_assets(self, html_content: str, output_dir: str) -> Dict[str, str]:
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
            print(f"{BackgroundColors.YELLOW}Warning: Page not initialized, skipping asset collection.{Style.RESET_ALL}")  # Warn user that asset collection will be skipped
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
                        # Generate unique filename
                        parsed_url = urlparse(absolute_url)  # Parse URL to extract components
                        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"  # Extract file extension or use default .jpg
                        filename = f"image_{idx}{ext}"  # Generate filename with index and extension
                        filepath = os.path.join(assets_dir, filename)  # Construct full file path for saving
                        
                        # Save asset
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


    def _save_snapshot(self, html_content: str, output_dir: str, asset_map: Dict[str, str]) -> Optional[str]:
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
            
            # Prepare price strings
            current_price = f"{product_data.get('current_price_integer', '0')},{product_data.get('current_price_decimal', '00')}"  # Format current price from dictionary values
            old_price_int = product_data.get('old_price_integer', 'N/A')  # Get old price integer part or default
            old_price_dec = product_data.get('old_price_decimal', 'N/A')  # Get old price decimal part or default
            
            if old_price_int != 'N/A' and old_price_dec != 'N/A':  # Verify if old price components are available
                old_price = f"{old_price_int},{old_price_dec}"  # Format old price from components
            else:  # Handle case when old price is not available
                old_price = "N/A"  # Use N/A as old price placeholder
            
            discount = product_data.get('discount_percentage', 'N/A')  # Get discount percentage or default
            
            # Format the description content
            content = PRODUCT_DESCRIPTION_TEMPLATE.format(  # Format template with product data
                product_name=product_data.get('name', 'Unknown Product'),  # Product name with fallback
                current_price=current_price,  # Formatted current price
                old_price=old_price,  # Formatted old price or N/A
                discount=discount,  # Discount percentage or N/A
                description=product_data.get('description', 'No description available'),  # Product description with fallback
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


    def download_media(self) -> List[str]:
        """
        Downloads product media and creates snapshot after browser automation.

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
            
            # Sanitize product name for directory
            product_name = self.product_data.get("name", "Unknown Product")  # Get product name or use default
            product_name_safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in product_name).strip()  # Sanitize product name for filesystem use
            
            # Create output directory
            output_dir = self.create_output_directory(product_name_safe)  # Create output directory for product
            
            # Get rendered HTML
            html_content = self._get_rendered_html()  # Get fully rendered HTML content
            if not html_content:  # Verify if HTML content retrieval failed
                print(f"{BackgroundColors.RED}Failed to get rendered HTML.{Style.RESET_ALL}")  # Alert user about HTML retrieval failure
                return downloaded_files  # Return empty list when HTML is unavailable
            
            # Collect and download assets
            asset_map = self._collect_assets(html_content, output_dir)  # Download and collect all page assets
            
            # Save page snapshot with localized assets
            snapshot_path = self._save_snapshot(html_content, output_dir, asset_map)  # Save HTML snapshot with localized assets
            if snapshot_path:  # Verify if snapshot was saved successfully
                downloaded_files.append(snapshot_path)  # Add snapshot path to downloaded files list
            
            # Create description file
            description_file = self.create_product_description_file(  # Create product description text file
                self.product_data, output_dir, product_name_safe, self.product_url  # Pass all required parameters
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

        :param verbose: Boolean flag to enable verbose output
        :return: Dictionary containing all scraped data and downloaded file paths
        """

        print(  # Display scraping start message to user
            f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Starting {BackgroundColors.CYAN}Shopee{BackgroundColors.GREEN} Scraping process...{Style.RESET_ALL}"
        )  # End of print statement
        
        try:  # Attempt scraping process with error handling
            # Step 1: Launch authenticated browser
            self._launch_browser()  # Initialize and launch browser instance
            
            # Step 2: Load page
            if not self._load_page():  # Attempt to load product page
                return None  # Return None if page loading failed
            
            # Step 3: Wait for full render and auto-scroll
            self._wait_full_render()  # Wait for page to fully render with dynamic content
            self._auto_scroll()  # Scroll page to trigger lazy-loaded content
            
            # Step 4: Get rendered HTML
            html_content = self._get_rendered_html()  # Extract fully rendered HTML content
            if not html_content:  # Verify if HTML extraction failed
                return None  # Return None if HTML is unavailable
            
            # Step 5: Scrape product information
            product_info = self.scrape_product_info(html_content)  # Parse and extract product information
            if not product_info:  # Verify if product info extraction failed
                return None  # Return None if extraction failed
            
            # Step 6: Download media and create snapshot
            downloaded_files = self.download_media()  # Download product media and create snapshot
            product_info["downloaded_files"] = downloaded_files  # Add downloaded files to product info dictionary
            
            print(  # Display success message to user
                f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Shopee scraping completed successfully!{Style.RESET_ALL}"
            )  # End of print statement
            
            return product_info  # Return complete product information with downloaded files
            
        except Exception as e:  # Catch any exceptions during scraping process
            print(f"{BackgroundColors.RED}Scraping failed: {e}{Style.RESET_ALL}")  # Alert user about scraping failure
            return None  # Return None to indicate scraping failed
        finally:  # Always execute cleanup regardless of success or failure
            # Always close browser
            self._close_browser()  # Close browser and release resources
   
            
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
