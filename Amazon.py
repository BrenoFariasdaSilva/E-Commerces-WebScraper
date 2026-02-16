"""
================================================================================
Amazon Web Scraper
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-02-11
Description :
    This script provides an Amazon class for scraping product information
    from Amazon Brasil product pages using authenticated browser sessions. It extracts
    comprehensive product details including name, prices, discount information,
    descriptions, and media assets from fully rendered pages.

    Key features include:
        - Authenticated browser session using existing Chrome profile
        - Automatic product URL extraction and validation
        - Full page rendering with JavaScript execution
        - Product name and description extraction
        - Price information (current and old prices with formatted strings)
        - Discount percentage extraction
        - Product images download
        - Product details table extraction
        - International seller detection
        - Complete page snapshot capture (HTML + localized assets)
        - Product description file generation in marketing template format
        - Organized output in product-specific directories

Usage:
    1. Import the Amazon class in your main script.
    2. Create an instance with a product URL:
        scraper = Amazon("https://amazon.com.br/product-url")
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

# HTML Selectors Dictionary:
HTML_SELECTORS = {
    "product_name": [  # List of CSS selectors for product name in priority order
        ("span", {"id": "productTitle"}),  # Amazon product title span with specific id
        ("h1", {"id": "title"}),  # Alternative H1 heading for product title
        ("h1", {}),  # Generic H1 heading as last resort fallback
    ],
    "current_price": [  # List of CSS selectors for current price in priority order
        ("span", {"class": "a-price aok-align-center reinventPricePriceToPayMargin priceToPay"}),  # Amazon current price container
        ("span", {"class": re.compile(r".*priceToPay.*", re.IGNORECASE)}),  # Generic price to pay pattern fallback
        ("span", {"class": re.compile(r".*a-price.*", re.IGNORECASE)}),  # Generic price span as last resort fallback
    ],
    "old_price": [  # List of CSS selectors for old price in priority order
        ("span", {"class": "a-price a-text-price"}),  # Amazon old price container with specific class
        ("span", {"class": re.compile(r".*a-text-price.*", re.IGNORECASE)}),  # Generic original price pattern fallback
        ("span", {"class": re.compile(r".*list.*price.*", re.IGNORECASE)}),  # Generic list price span as last resort fallback
    ],
    "discount": [  # List of CSS selectors for discount percentage in priority order
        ("span", {"class": "a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin savingsPercentage"}),  # Amazon discount container with specific class
        ("span", {"class": re.compile(r".*savingsPercentage.*", re.IGNORECASE)}),  # Generic discount span fallback
        ("span", {"class": re.compile(r".*discount.*", re.IGNORECASE)}),  # Sale badge container as last resort fallback
    ],
    "description": [  # List of CSS selectors for product description in priority order
        ("div", {"class": "a-section a-spacing-large bucket"}),  # Amazon description container with specific class
        ("div", {"id": "feature-bullets"}),  # Feature bullets section fallback
        ("div", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Generic description pattern fallback
    ],
    "gallery": {"id": "altImages"},  # CSS selector for product gallery container with images
    "detail_table": {"id": "productDetails_techSpec_section_1"},  # CSS selector for product details table
    "detail_section": {"id": "prodDetails"},  # CSS selector for product details section
    "foreign_seller_badge": "https://m.media-amazon.com/images/G/32/foreignseller/Foreign_Seller_Badge_v2._CB403622375_.png",  # Foreign seller badge image URL
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

🛒 Encontre na Amazon:
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


class Amazon:
    """
    A web scraper class for extracting product information from Amazon Brasil using
    authenticated browser sessions.
    
    This class handles the extraction of product details including name, prices,
    discounts, descriptions, and media files from Amazon product pages using
    Playwright for full page rendering and authenticated access.
    """


    def __init__(self, url: str, local_html_path: Optional[str] = None, prefix: str = "", output_directory: str = OUTPUT_DIRECTORY) -> None:
        """
        Initializes the Amazon scraper with a product URL and optional local HTML file path.

        :param url: The URL of the Amazon product page to scrape
        :param local_html_path: Optional path to a local HTML file for offline scraping
        :param prefix: Optional platform prefix for output directory naming (e.g., "Amazon")
        :param output_directory: Output directory path for storing scraped data (defaults to OUTPUT_DIRECTORY constant)
        :return: None
        """

        self.url: str = url  # Store the initial product URL for reference
        self.product_url: str = url  # Maintain separate copy of product URL for Amazon direct usage
        self.local_html_path: Optional[str] = local_html_path  # Store path to local HTML file for offline scraping
        self.html_content: Optional[str] = None  # Store HTML content for reuse (from browser or local file)
        self.product_data: Optional[Dict[str, Any]] = None  # Initialize product data (may be None until scraped)
        self.prefix: str = prefix  # Store the platform prefix for directory naming
        self.output_directory: str = output_directory  # Store the output directory path for this scraping session
        self.playwright: Optional[Any] = None  # Placeholder for Playwright instance
        self.browser: Optional[Any] = None  # Placeholder for browser instance
        self.page: Optional[Any] = None  # Placeholder for page object

        verbose_output(  # Output initialization message to user
            f"{BackgroundColors.GREEN}Amazon scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
        )  # End of verbose output call
        if local_html_path:  # If local HTML file path is provided
            verbose_output(  # Output offline mode message to user
                f"{BackgroundColors.GREEN}Offline mode enabled. Will read from: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}"
            )  # End of verbose output call


    def extract_old_price(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extracts the old price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Formatted price string or None if not found
        """
        
        for tag, attrs in HTML_SELECTORS["old_price"]:  # Iterate through prioritized selectors
            price_container = soup.find(tag, attrs)  # Search for old price container element
            if price_container:  # Check if container was found
                try:  # Attempt to extract price components
                    price_text = price_container.get_text(strip=True)  # Extract all text from container
                    
                    if price_text:  # Check if text exists
                        verbose_output(  # Output found old price
                            f"{BackgroundColors.GREEN}Old price found: {BackgroundColors.CYAN}{price_text}{Style.RESET_ALL}"
                        )  # End of verbose output call
                        return price_text  # Return extracted price text
                except Exception as e:  # Catch exceptions during extraction
                    continue  # Try next selector on error
        
        verbose_output(  # Output not found message
            f"{BackgroundColors.YELLOW}Old price not found.{Style.RESET_ALL}"
        )  # End of verbose output call
        return None  # Return None when old price is not available


    def extract_discount_percentage(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extracts the discount percentage from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Discount percentage string (e.g., "15%") or None if not found
        """
        
        for tag, attrs in HTML_SELECTORS["discount"]:  # Iterate through prioritized selectors
            discount_element = soup.find(tag, attrs)  # Search for discount element
            if discount_element:  # Check if element was found
                discount_text = discount_element.get_text(strip=True)  # Extract and strip whitespace
                discount_text = discount_text.replace("-", "").strip()  # Remove minus sign and extra spaces
                verbose_output(  # Output found discount
                    f"{BackgroundColors.GREEN}Discount found: {BackgroundColors.CYAN}{discount_text}{Style.RESET_ALL}"
                )  # End of verbose output call
                return discount_text  # Return cleaned discount text
        
        verbose_output(  # Output not found message
            f"{BackgroundColors.YELLOW}Discount percentage not found.{Style.RESET_ALL}"
        )  # End of verbose output call
        return None  # Return None when discount is not available


    def extract_product_description(self, soup: BeautifulSoup) -> str:
        """
        Extracts the product description from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product description string or "No description available" if not found
        """
        
        for tag, attrs in HTML_SELECTORS["description"]:  # Iterate through prioritized selectors
            desc_container = soup.find(tag, attrs)  # Search for description container
            if desc_container:  # Check if container was found
                description_parts = []  # Initialize list for description parts
                
                for element in desc_container.find_all(["p", "li", "span", "div"]):  # Find all text-containing elements
                    text = element.get_text(strip=True)  # Extract text with stripped whitespace
                    if text and len(text) > 10:  # Filter out very short or empty text
                        description_parts.append(text)  # Add text to parts list
                
                if description_parts:  # Check if any parts were collected
                    description = " ".join(description_parts)  # Join all parts with spaces
                    description = re.sub(r"\s+", " ", description)  # Normalize multiple spaces
                    verbose_output(  # Output found description preview
                        f"{BackgroundColors.GREEN}Description found: {BackgroundColors.CYAN}{description[:100]}...{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return description  # Return complete description
        
        verbose_output(  # Output not found message
            f"{BackgroundColors.YELLOW}Description not found.{Style.RESET_ALL}"
        )  # End of verbose output call
        return "No description available"  # Return default message when description is not found


    def extract_product_details(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extracts the product details table from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Dictionary of product details or empty dict if not found
        """
        
        details_dict: Dict[str, str] = {}  # Initialize empty dictionary for details
        
        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Extracting product details table...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt table extraction with error handling
            details_section = soup.find("div", HTML_SELECTORS["detail_section"])  # Find product details section
            if not details_section:  # Check if section was found
                verbose_output(  # Output not found message
                    f"{BackgroundColors.YELLOW}Product details section not found.{Style.RESET_ALL}"
                )  # End of verbose output call
                return details_dict  # Return empty dictionary
            
            details_table = details_section.find("table", HTML_SELECTORS["detail_table"])  # Find details table
            if not details_table:  # Check if table was found
                verbose_output(  # Output not found message
                    f"{BackgroundColors.YELLOW}Product details table not found.{Style.RESET_ALL}"
                )  # End of verbose output call
                return details_dict  # Return empty dictionary
            
            rows = details_table.find_all("tr")  # Find all table rows
            for row in rows:  # Iterate through each row
                try:  # Attempt to extract row data
                    key_cell = row.find("th", {"class": "prodDetSectionEntry"})  # Find key cell
                    value_cell = row.find("td", {"class": "prodDetAttrValue"})  # Find value cell
                    
                    if key_cell and value_cell:  # Check if both cells exist
                        key = key_cell.get_text(strip=True)  # Extract key text
                        value = value_cell.get_text(strip=True)  # Extract value text
                        
                        key = re.sub(r"\s+", " ", key)  # Normalize key spacing
                        value = re.sub(r"\s+", " ", value)  # Normalize value spacing
                        
                        details_dict[key] = value  # Add key-value pair to dictionary
                except Exception as e:  # Catch exceptions during row extraction
                    continue  # Skip row on error
            
            verbose_output(  # Output success message with count
                f"{BackgroundColors.GREEN}Extracted {BackgroundColors.CYAN}{len(details_dict)}{BackgroundColors.GREEN} product details.{Style.RESET_ALL}"
            )  # End of verbose output call
            
        except Exception as e:  # Catch any exceptions during table extraction
            print(f"{BackgroundColors.YELLOW}Warning during details extraction: {e}{Style.RESET_ALL}")  # Warn user about extraction issues
        
        return details_dict  # Return dictionary with extracted details


    def find_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Finds all image URLs from the product gallery.
        Extracts full-size images from the gallery container.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of image URLs
        """
        
        image_urls: List[str] = []  # Initialize empty list to store image URLs
        seen_urls: set = set()  # Track URLs to avoid duplicates
        
        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Extracting image URLs from gallery...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt image extraction with error handling
            gallery = soup.find("div", HTML_SELECTORS["gallery"])  # Find gallery container
            
            if not gallery:  # Check if gallery was found
                verbose_output(  # Output warning message
                    f"{BackgroundColors.YELLOW}Gallery container not found.{Style.RESET_ALL}"
                )  # End of verbose output call
                return image_urls  # Return empty list if gallery not found
            
            images = gallery.find_all("img")  # Find all image tags in gallery
            for img in images:  # Iterate through each image
                from typing import cast

                img_url = None  # Initialize URL variable

                if img.has_attr("src"):  # Check if img has src attribute
                    img_url = cast(str, img.get("src", ""))  # Get src attribute value as str
                elif img.has_attr("data-src"):  # Check if img has data-src attribute
                    img_url = cast(str, img.get("data-src", ""))  # Get data-src attribute value as str
                elif img.has_attr("data-old-hires"):  # Check if img has high-res data attribute
                    img_url = cast(str, img.get("data-old-hires", ""))  # Get high-res URL as str
                
                if img_url:  # Check if URL was found
                    if img_url.startswith("//"):  # Check if protocol-relative URL
                        img_url = "https:" + img_url  # Add HTTPS protocol
                    elif img_url.startswith("/"):  # Check if absolute path
                        img_url = "https://www.amazon.com.br" + img_url  # Build complete URL
                    
                    if img_url not in seen_urls:  # Check if URL is not duplicate
                        if "images-amazon.com" in img_url or "ssl-images-amazon.com" in img_url:  # Validate Amazon image domain
                            image_urls.append(img_url)  # Add URL to list
                            seen_urls.add(img_url)  # Mark URL as seen
                            verbose_output(  # Output found image
                                f"{BackgroundColors.CYAN}Image found: {img_url}{Style.RESET_ALL}"
                            )  # End of verbose output call
        
        except Exception as e:  # Catch any exceptions during image extraction
            print(f"{BackgroundColors.YELLOW}Warning during image extraction: {e}{Style.RESET_ALL}")  # Warn user about extraction issues
        
        verbose_output(  # Output total count
            f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(image_urls)}{BackgroundColors.GREEN} images.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return image_urls  # Return list of image URLs


    def find_video_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Finds all video URLs from the product page.
        Searches for video elements and extracts src attributes.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: List of video URLs
        """
        
        video_urls: List[str] = []  # Initialize empty list to store video URLs
        seen_urls: set = set()  # Track URLs to avoid duplicates
        
        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Extracting video URLs from page...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        try:  # Attempt video extraction with error handling
            videos = soup.find_all("video")  # Find all video tags
            from typing import cast
            from urllib.parse import urljoin

            for video in videos:  # Iterate through each video
                video_url = None  # Initialize URL variable

                if video.has_attr("src"):  # Check if video has src attribute
                    video_url = cast(str, video.get("src", ""))  # Get src attribute value as str

                source_tags = video.find_all("source")  # Find all source tags within video
                for source in source_tags:  # Iterate through sources
                    if source.has_attr("src"):  # Check if source has src
                        video_url = cast(str, source.get("src", ""))  # Get source URL as str
                        break  # Use first valid source
                
                if video_url:  # Check if URL was found
                    if video_url.startswith("//"):  # Check if protocol-relative URL
                        video_url = "https:" + video_url  # Add HTTPS protocol
                    elif video_url.startswith("/"):  # Check if absolute path
                        video_url = "https://www.amazon.com.br" + video_url  # Build complete URL
                    
                    if video_url not in seen_urls:  # Check if URL is not duplicate
                        video_urls.append(video_url)  # Add URL to list
                        seen_urls.add(video_url)  # Mark URL as seen
                        verbose_output(  # Output found video
                            f"{BackgroundColors.CYAN}Video found: {video_url}{Style.RESET_ALL}"
                        )  # End of verbose output call
        
        except Exception as e:  # Catch any exceptions during video extraction
            print(f"{BackgroundColors.YELLOW}Warning during video extraction: {e}{Style.RESET_ALL}")  # Warn user about extraction issues
        
        verbose_output(  # Output total count
            f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(video_urls)}{BackgroundColors.GREEN} videos.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return video_urls  # Return list of video URLs


    def print_product_info(self, product_data: Dict[str, Any]) -> None:
        """
        Prints the extracted product information in a formatted manner.
        
        :param product_data: Dictionary containing the scraped product data
        :return: None
        """
        
        if not product_data:  # Check if product data exists
            print(f"{BackgroundColors.YELLOW}No product data to display.{Style.RESET_ALL}")  # Warn user no data available
            return  # Exit method early
        
        verbose_output(  # Output formatted product information
            f"{BackgroundColors.GREEN}Product information extracted successfully:{BackgroundColors.GREEN}\n"
            f"  {BackgroundColors.CYAN}Name:{BackgroundColors.GREEN} {product_data.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Current Price:{BackgroundColors.GREEN} {product_data.get('current_price', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Old Price:{BackgroundColors.GREEN} {product_data.get('old_price', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Discount:{BackgroundColors.GREEN} {product_data.get('discount_percentage', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Description:{BackgroundColors.GREEN} {product_data.get('description', 'N/A')[:100]}...{Style.RESET_ALL}"
        )  # End of verbose_output call


    def scrape_product_info(self, html_content: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes product information from rendered HTML content.

        :param html_content: Rendered HTML string
        :return: Dictionary containing the scraped product data
        """

        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Parsing product information...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt parsing with error handling
            soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object
            
            product_name = self.extract_product_name(soup)  # Extract product name
            is_international = self.detect_international(soup)  # Detect international seller
            if is_international:  # Check if product is international
                product_name = self.prefix_international_name(product_name)  # Add international prefix
            
            current_price = self.extract_current_price(soup)  # Extract current price
            old_price = self.extract_old_price(soup)  # Extract old price
            discount = self.extract_discount_percentage(soup)  # Extract discount percentage
            description = self.extract_product_description(soup)  # Extract product description
            product_details = self.extract_product_details(soup)  # Extract product details table
            
            product_data = {  # Build product data dictionary
                "name": product_name,  # Store product name
                "current_price": current_price,  # Store current price
                "old_price": old_price,  # Store old price
                "discount_percentage": discount,  # Store discount percentage
                "description": description,  # Store description
                "product_details": product_details,  # Store details table
                "is_international": is_international,  # Store international flag
            }  # End of dictionary construction
            
            self.print_product_info(product_data)  # Print extracted information
            return product_data  # Return complete product data
            
        except Exception as e:  # Catch any exceptions during scraping
            print(f"{BackgroundColors.RED}Failed to scrape product info: {e}{Style.RESET_ALL}")  # Alert user about scraping failure
            return None  # Return None to indicate scraping failed


    def create_directory(self, full_directory_name, relative_directory_name):
        """
        Creates a directory.

        :param full_directory_name: Name of the directory to be created.
        :param relative_directory_name: Relative name of the directory to be created that will be shown in the terminal.
        :return: None
        """

        verbose_output(  # Output directory creation message
            true_string=f"{BackgroundColors.GREEN}Creating the {BackgroundColors.CYAN}{relative_directory_name}{BackgroundColors.GREEN} directory...{Style.RESET_ALL}"
        )  # End of verbose output call

        if os.path.isdir(full_directory_name):  # Check if directory already exists
            return  # Exit early if directory exists
        try:  # Attempt directory creation
            os.makedirs(full_directory_name)  # Create directory with all parent directories
        except OSError:  # Catch OS errors during creation
            print(f"{BackgroundColors.RED}Failed to create directory: {full_directory_name}{Style.RESET_ALL}")  # Alert user about creation failure


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

        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Collecting page assets...{Style.RESET_ALL}"
        )  # End of verbose output call

        if self.page is None:  # Validate page instance exists
            return {}  # Return empty dictionary if page not initialized

        assets_dir = os.path.join(output_dir, "assets")  # Construct path for assets subdirectory
        self.create_directory(assets_dir, "assets")  # Create assets subdirectory

        asset_map: Dict[str, str] = {}  # Maps original URL to local path  # Initialize empty dictionary to map original URLs to local paths
        soup = BeautifulSoup(html_content, "html.parser")  # Parse HTML content into BeautifulSoup object

        img_tags = soup.find_all("img", src=True)  # Find all image tags with src attribute
        for idx, img in enumerate(img_tags, 1):  # Iterate with counter starting at 1
            try:  # Attempt asset download with error handling
                img_url = cast(str, img.get("src", ""))  # Get image source URL as str
                if img_url.startswith("//"):  # Check if protocol-relative URL
                    img_url = "https:" + img_url  # Add HTTPS protocol
                elif img_url.startswith("/"):  # Check if absolute path
                    img_url = urljoin(self.product_url, img_url)  # Build complete URL from base

                if not img_url.startswith("http"):  # Skip non-HTTP URLs
                    continue  # Skip to next image

                parsed = urlparse(img_url)  # Parse URL to extract components
                ext = os.path.splitext(parsed.path)[1] or ".jpg"  # Get extension or default to jpg
                local_filename = f"asset_{idx}{ext}"  # Generate unique filename
                local_path = os.path.join(assets_dir, local_filename)  # Build full local path

                asset_map[img_url] = f"assets/{local_filename}"  # Map original URL to relative path

            except Exception as e:  # Catch exceptions during asset processing
                verbose_output(  # Output error message
                    f"{BackgroundColors.YELLOW}Failed to process asset {idx}: {e}{Style.RESET_ALL}"
                )  # End of verbose output call

        verbose_output(  # Output success message with count
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

        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Saving page snapshot...{Style.RESET_ALL}"
        )  # End of verbose output call

        try:  # Attempt snapshot save with error handling
            for original_url, local_path in asset_map.items():  # Iterate through asset mappings
                html_content = html_content.replace(original_url, local_path)  # Replace original URL with local path
            
            snapshot_path = os.path.join(output_dir, "index.html")  # Build snapshot file path
            with open(snapshot_path, "w", encoding="utf-8") as file:  # Open file for writing with UTF-8 encoding
                file.write(html_content)  # Write modified HTML content
            
            verbose_output(  # Output success message
                f"{BackgroundColors.GREEN}Snapshot saved to: {BackgroundColors.CYAN}{snapshot_path}{Style.RESET_ALL}"
            )  # End of verbose output call
            return snapshot_path  # Return path to saved snapshot
            
        except Exception as e:  # Catch any exceptions during save
            print(f"{BackgroundColors.RED}Failed to save snapshot: {e}{Style.RESET_ALL}")  # Alert user about save failure
            return None  # Return None to indicate save failed


    def create_product_description_file(self, product_data: Dict[str, Any], output_dir: str, product_name_safe: str, url: str) -> Optional[str]:
        """
        Creates a text file with product description and details.
        
        :param product_data: Dictionary with product information
        :param output_dir: Directory to save the file
        :param product_name_safe: Safe product name for filename
        :param url: Original product URL
        :return: Path to the created description file or None if failed
        """
        
        try:  # Attempt file creation with error handling
            current_price = product_data.get("current_price", "N/A")  # Get current price or default
            old_price = product_data.get("old_price", "N/A")  # Get old price or default
            discount = product_data.get("discount_percentage", "N/A")  # Get discount or default
            description = product_data.get("description", "No description available")  # Get description or default
            
            description_content = PRODUCT_DESCRIPTION_TEMPLATE.format(  # Format template with product data
                product_name=product_data.get("name", "Unknown Product"),  # Insert product name
                current_price=current_price if current_price else "N/A",  # Insert current price
                old_price=old_price if old_price else "N/A",  # Insert old price
                discount=discount if discount else "N/A",  # Insert discount
                description=description,  # Insert description
                url=url  # Insert product URL
            )  # End of template formatting
            
            desc_filename = f"{product_name_safe}.txt"  # Construct description filename
            desc_path = os.path.join(output_dir, desc_filename)  # Build full file path
            
            with open(desc_path, "w", encoding="utf-8") as file:  # Open file for writing with UTF-8 encoding
                file.write(description_content)  # Write formatted description content
            
            verbose_output(  # Output success message
                f"{BackgroundColors.GREEN}Product description saved to: {BackgroundColors.CYAN}{desc_path}{Style.RESET_ALL}"
            )  # End of verbose output call
            
            return desc_path  # Return path to created file
            
        except Exception as e:  # Catch any exceptions during file creation
            print(f"{BackgroundColors.RED}Failed to create description file: {e}{Style.RESET_ALL}")  # Alert user about creation failure
            return None  # Return None to indicate creation failed


    def to_sentence_case(self, text: str) -> str:
        """
        Converts text to sentence case (first letter of each sentence uppercase).

        :param text: The text to convert
        :return: Text in sentence case
        """

        if not text:  # Check if text is empty or None
            return text  # Return as-is if empty

        sentences = re.split(r"([.!?]\s*)", text)  # Keep the delimiters

        result = []  # Initialize list to hold processed sentences
        for i, sentence in enumerate(sentences):  # Iterate with index
            if i % 2 == 0 and sentence:  # Process actual sentences (not delimiters)
                sentence = sentence[0].upper() + sentence[1:].lower() if sentence else sentence  # Capitalize first letter
            result.append(sentence)  # Add processed sentence to result

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
        
        try:  # Attempt image download with error handling
            if img_url.startswith("file://") or (not img_url.startswith("http") and os.path.exists(img_url)):  # Check if local file
                local_img_path = img_url.replace("file://", "")  # Remove file protocol
                
                if not os.path.exists(local_img_path):  # Verify file exists
                    verbose_output(  # Output not found message
                        f"{BackgroundColors.YELLOW}Local image not found: {local_img_path}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return None  # Return None if file doesn't exist
                
                file_ext = os.path.splitext(local_img_path)[1] or ".jpg"  # Get file extension or default
                image_filename = f"image_{image_count}{file_ext}"  # Generate unique filename
                image_path = os.path.join(output_dir, image_filename)  # Build full destination path
                
                shutil.copy2(local_img_path, image_path)  # Copy file preserving metadata
                
                verbose_output(  # Output success message
                    f"{BackgroundColors.GREEN}Image copied: {BackgroundColors.CYAN}{image_filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return image_path  # Return path to copied image
            
            else:  # Handle HTTP URL download
                import requests  # Import requests library for HTTP
                
                response = requests.get(img_url, timeout=30, stream=True)  # Send GET request with timeout
                response.raise_for_status()  # Raise exception for bad status codes
                
                content_type = response.headers.get("content-type", "")  # Get content type header
                if "image" not in content_type:  # Validate content is image
                    verbose_output(  # Output warning message
                        f"{BackgroundColors.YELLOW}URL does not point to an image: {img_url}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return None  # Return None if not image
                
                file_ext = ".jpg"  # Default extension
                if "jpeg" in content_type or "jpg" in content_type:  # Check for JPEG
                    file_ext = ".jpg"  # Set JPEG extension
                elif "png" in content_type:  # Check for PNG
                    file_ext = ".png"  # Set PNG extension
                elif "gif" in content_type:  # Check for GIF
                    file_ext = ".gif"  # Set GIF extension
                elif "webp" in content_type:  # Check for WebP
                    file_ext = ".webp"  # Set WebP extension
                
                image_filename = f"image_{image_count}{file_ext}"  # Generate unique filename
                image_path = os.path.join(output_dir, image_filename)  # Build full destination path
                
                with open(image_path, "wb") as file:  # Open file for binary writing
                    for chunk in response.iter_content(chunk_size=8192):  # Stream content in chunks
                        file.write(chunk)  # Write chunk to file
                
                verbose_output(  # Output success message
                    f"{BackgroundColors.GREEN}Image downloaded: {BackgroundColors.CYAN}{image_filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return image_path  # Return path to downloaded image
        
        except Exception as e:  # Catch any exceptions during download
            print(f"{BackgroundColors.YELLOW}Failed to download image {image_count}: {e}{Style.RESET_ALL}")  # Warn user about download failure
            return None  # Return None to indicate download failed


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
        
        try:  # Attempt video download with error handling
            if video_url.startswith("file://") or (not video_url.startswith("http") and os.path.exists(video_url)):  # Check if local file
                local_video_path = video_url.replace("file://", "")  # Remove file protocol
                
                if not os.path.exists(local_video_path):  # Verify file exists
                    verbose_output(  # Output not found message
                        f"{BackgroundColors.YELLOW}Local video not found: {local_video_path}{Style.RESET_ALL}"
                    )  # End of verbose output call
                    return None  # Return None if file doesn't exist
                
                file_ext = os.path.splitext(local_video_path)[1] or ".mp4"  # Get file extension or default
                video_filename = f"video_{video_count}{file_ext}"  # Generate unique filename
                video_path = os.path.join(output_dir, video_filename)  # Build full destination path
                
                shutil.copy2(local_video_path, video_path)  # Copy file preserving metadata
                
                verbose_output(  # Output success message
                    f"{BackgroundColors.GREEN}Video copied: {BackgroundColors.CYAN}{video_filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return video_path  # Return path to copied video
            
            elif is_hls:  # Handle HLS stream download
                if shutil.which("ffmpeg") is None:  # Check if ffmpeg is available
                    print(f"{BackgroundColors.YELLOW}ffmpeg not found. Cannot download HLS video.{Style.RESET_ALL}")  # Warn user ffmpeg missing
                    return None  # Return None if ffmpeg unavailable
                
                video_filename = f"video_{video_count}.mp4"  # Generate MP4 filename
                video_path = os.path.join(output_dir, video_filename)  # Build full destination path
                
                ffmpeg_command = [  # Build ffmpeg command list
                    "ffmpeg",  # FFmpeg executable
                    "-i", video_url,  # Input HLS URL
                    "-c", "copy",  # Copy streams without re-encoding
                    "-bsf:a", "aac_adtstoasc",  # Convert AAC format
                    "-y",  # Overwrite output file
                    video_path  # Output file path
                ]  # End of command list
                
                verbose_output(  # Output download start message
                    f"{BackgroundColors.GREEN}Downloading HLS video with ffmpeg...{Style.RESET_ALL}"
                )  # End of verbose output call
                
                result = subprocess.run(  # Execute ffmpeg command
                    ffmpeg_command,  # Command to run
                    stdout=subprocess.PIPE,  # Capture stdout
                    stderr=subprocess.PIPE,  # Capture stderr
                    timeout=300  # 5 minute timeout
                )  # End of subprocess call
                
                if result.returncode != 0:  # Check if command failed
                    print(f"{BackgroundColors.RED}ffmpeg failed: {result.stderr.decode()}{Style.RESET_ALL}")  # Output error message
                    return None  # Return None on failure
                
                verbose_output(  # Output success message
                    f"{BackgroundColors.GREEN}HLS video downloaded: {BackgroundColors.CYAN}{video_filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return video_path  # Return path to downloaded video
            
            else:  # Handle regular HTTP video download
                import requests  # Import requests library for HTTP
                
                response = requests.get(video_url, timeout=60, stream=True)  # Send GET request with timeout
                response.raise_for_status()  # Raise exception for bad status codes
                
                content_type = response.headers.get("content-type", "")  # Get content type header
                
                file_ext = ".mp4"  # Default extension
                if "mp4" in content_type:  # Check for MP4
                    file_ext = ".mp4"  # Set MP4 extension
                elif "webm" in content_type:  # Check for WebM
                    file_ext = ".webm"  # Set WebM extension
                elif "quicktime" in content_type or "mov" in content_type:  # Check for QuickTime
                    file_ext = ".mov"  # Set MOV extension
                
                video_filename = f"video_{video_count}{file_ext}"  # Generate unique filename
                video_path = os.path.join(output_dir, video_filename)  # Build full destination path
                
                with open(video_path, "wb") as file:  # Open file for binary writing
                    for chunk in response.iter_content(chunk_size=8192):  # Stream content in chunks
                        file.write(chunk)  # Write chunk to file
                
                verbose_output(  # Output success message
                    f"{BackgroundColors.GREEN}Video downloaded: {BackgroundColors.CYAN}{video_filename}{Style.RESET_ALL}"
                )  # End of verbose output call
                
                return video_path  # Return path to downloaded video
        
        except Exception as e:  # Catch any exceptions during download
            print(f"{BackgroundColors.YELLOW}Failed to download video {video_count}: {e}{Style.RESET_ALL}")  # Warn user about download failure
            return None  # Return None to indicate download failed


    def download_product_images(self, soup: BeautifulSoup, output_dir: str) -> List[str]:
        """
        Downloads all product images from the gallery.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :param output_dir: Directory to save images
        :return: List of downloaded image file paths
        """
        
        downloaded_images: List[str] = []  # Initialize list to track downloaded images
        
        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Downloading product images...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        image_urls = self.find_image_urls(soup)  # Get all image URLs from gallery
        
        for idx, img_url in enumerate(image_urls, 1):  # Iterate with counter starting at 1
            image_path = self.download_single_image(img_url, output_dir, idx)  # Download image
            if image_path:  # Check if download succeeded
                downloaded_images.append(image_path)  # Add to downloaded list
        
        verbose_output(  # Output success message with count
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
        
        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Downloading product videos...{Style.RESET_ALL}"
        )  # End of verbose output call
        
        video_urls = self.find_video_urls(soup)  # Get all video URLs from gallery
        
        for idx, video_url in enumerate(video_urls, 1):  # Iterate with counter starting at 1
            video_path = self.download_single_video(video_url, output_dir, idx)  # Download video
            if video_path:  # Check if download succeeded
                downloaded_videos.append(video_path)  # Add to downloaded list
        
        verbose_output(  # Output success message with count
            f"{BackgroundColors.GREEN}Downloaded {BackgroundColors.CYAN}{len(downloaded_videos)}{BackgroundColors.GREEN} videos.{Style.RESET_ALL}"
        )  # End of verbose output call
        
        return downloaded_videos  # Return list of downloaded video paths


    def download_media(self) -> List[str]:
        """
        Downloads product media and creates snapshot.
        Works for both online (browser) and offline (local HTML) modes.

        :return: List of downloaded file paths
        """

        verbose_output(  # Output status message
            f"{BackgroundColors.GREEN}Processing product media...{Style.RESET_ALL}"
        )  # End of verbose output call

        downloaded_files: List[str] = []  # Initialize empty list to track downloaded file paths
        
        try:  # Attempt media processing with error handling
            if not self.html_content:  # Validate HTML content exists
                print(f"{BackgroundColors.RED}No HTML content available for media download.{Style.RESET_ALL}")  # Alert user no content
                return downloaded_files  # Return empty list
            
            if not self.product_data:  # Validate product data exists
                print(f"{BackgroundColors.RED}No product data available for media download.{Style.RESET_ALL}")  # Alert user no data
                return downloaded_files  # Return empty list
            
            product_name = self.product_data.get("name", "Unknown Product")  # Get product name or default
            # Use shared helper to sanitize and enforce 80-character limit.
            product_name_safe = normalize_product_dir_name(product_name, replace_with="", title_case=False)  # Normalize name for directory usage
            
            output_dir = self.create_output_directory(product_name_safe)  # Create product output directory
            
            soup = BeautifulSoup(self.html_content, "html.parser")  # Parse HTML content
            
            images = self.download_product_images(soup, output_dir)  # Download all product images
            downloaded_files.extend(images)  # Add image paths to downloaded files
            
            videos = self.download_product_videos(soup, output_dir)  # Download all product videos
            downloaded_files.extend(videos)  # Add video paths to downloaded files
            
            asset_map = self.collect_assets(self.html_content, output_dir)  # Collect page assets
            
            snapshot_path = self.save_snapshot(self.html_content, output_dir, asset_map)  # Save page snapshot
            if snapshot_path:  # Check if snapshot was saved
                downloaded_files.append(snapshot_path)  # Add snapshot to downloaded files
            
            desc_path = self.create_product_description_file(  # Create description file
                self.product_data,  # Pass product data
                output_dir,  # Pass output directory
                product_name_safe,  # Pass safe product name
                self.url  # Pass original URL
            )  # End of function call
            if desc_path:  # Check if description file was created
                downloaded_files.append(desc_path)  # Add description to downloaded files
            
        except Exception as e:  # Catch any exceptions during media processing
            print(f"{BackgroundColors.RED}Error during media download: {e}{Style.RESET_ALL}")  # Alert user about error
        
        return downloaded_files  # Return list of all downloaded file paths


    def scrape(self, verbose: bool = VERBOSE) -> Optional[Dict[str, Any]]:
        """
        Main scraping method that orchestrates the entire scraping process.
        Supports both online scraping (via browser) and offline scraping (from local HTML file).

        :param verbose: Boolean flag to enable verbose output
        :return: Dictionary containing all scraped data and downloaded file paths
        """

        verbose_output(  # Output starting message
            f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Starting {BackgroundColors.CYAN}Amazon{BackgroundColors.GREEN} Scraping process...{Style.RESET_ALL}"
        )  # End of verbose_output call
        
        try:  # Attempt scraping process with error handling
            if self.local_html_path:  # Check if offline mode is enabled
                self.html_content = self.read_local_html()  # Read HTML from local file
                if not self.html_content:  # Validate HTML was read successfully
                    print(f"{BackgroundColors.RED}Failed to read local HTML file.{Style.RESET_ALL}")  # Alert user about read failure
                    return None  # Return None to indicate failure
            else:  # Handle online scraping mode
                self.launch_browser()  # Launch browser instance
                
                if not self.load_page():  # Load product page
                    print(f"{BackgroundColors.RED}Failed to load product page.{Style.RESET_ALL}")  # Alert user about load failure
                    return None  # Return None to indicate failure
                
                self.auto_scroll()  # Scroll page to load lazy content
                self.wait_full_render()  # Wait for full page render
                
                self.html_content = self.get_rendered_html()  # Get rendered HTML content
                if not self.html_content:  # Validate HTML was extracted
                    print(f"{BackgroundColors.RED}Failed to extract HTML content.{Style.RESET_ALL}")  # Alert user about extraction failure
                    return None  # Return None to indicate failure
            
            self.product_data = self.scrape_product_info(self.html_content)  # Scrape product information
            if not self.product_data:  # Validate product data was extracted
                print(f"{BackgroundColors.RED}Failed to scrape product information.{Style.RESET_ALL}")  # Alert user about scraping failure
                return None  # Return None to indicate failure
            
            downloaded_files = self.download_media()  # Download product media
            self.product_data["downloaded_files"] = downloaded_files  # Add downloaded files to product data
            
            verbose_output(  # Output completion message
                f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Scraping completed successfully!{Style.RESET_ALL}"
            )  # End of verbose_output call
            
            return self.product_data  # Return complete product data dictionary
            
        except Exception as e:  # Catch any exceptions during scraping process
            print(f"{BackgroundColors.RED}Error during scraping: {e}{Style.RESET_ALL}")  # Alert user about error
            return None  # Return None to indicate failure
        finally:  # Always execute cleanup
            if not self.local_html_path:  # Only close browser if online mode
                self.close_browser()  # Close browser and cleanup resources


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


def output_result(result):
    """
    Outputs the result to the terminal.

    :param result: The result to be outputted
    :return: None
    """

    if result:  # Verify if result dictionary is not None or empty
        print(  # Output formatted result message
            f"{BackgroundColors.GREEN}Scraping successful! Product data:{Style.RESET_ALL}\n"
            f"  {BackgroundColors.CYAN}Name:{Style.RESET_ALL} {result.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Price:{Style.RESET_ALL} {result.get('current_price', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Files:{Style.RESET_ALL} {len(result.get('downloaded_files', []))} downloaded"
        )  # End of print statement
    else:  # Handle case when result is None or empty
        print(  # Output failure message
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
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Amazon Scraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n",  # End with newline
    )  # End of print statement
    start_time = datetime.datetime.now()  # Record program start time

    test_url = "https://www.amazon.com.br/product-example"  # Test URL  # Define test URL for scraping demonstration
    
    verbose_output(  # Log test URL being used
        f"{BackgroundColors.GREEN}Testing Amazon scraper with URL: {BackgroundColors.CYAN}{test_url}{Style.RESET_ALL}\n"
    )  # End of verbose output call
    
    try:  # Attempt scraping process with error handling
        scraper = Amazon(test_url)  # Create Amazon scraper instance with test URL
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
