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
import shutil  # For copying files (local HTML mode)
import subprocess  # For running external commands (ffmpeg)
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

# HTML Selectors Dictionary:
HTML_SELECTORS = {
    "product_name": [  # List of CSS selectors for product name in priority order
        ("div", {"class": "vR6K3w"}),  # Shopee product name container with specific class
        ("div", {"class": re.compile(r".*product.*name.*", re.IGNORECASE)}),  # Generic product name pattern fallback
        ("h1", {}),  # Generic H1 heading as last resort fallback
    ],
    "current_price": [  # List of CSS selectors for current price in priority order
        ("div", {"class": ["IZPeQz", "B67UQ0"]}),  # Shopee current price container with multiple classes
        ("div", {"class": re.compile(r".*price.*current.*", re.IGNORECASE)}),  # Generic current price pattern fallback
        ("span", {"class": re.compile(r".*price.*", re.IGNORECASE)}),  # Generic price span as last resort fallback
    ],
    "old_price": [  # List of CSS selectors for old price in priority order
        ("div", {"class": "ZA5sW5"}),  # Shopee old price container with specific class
        ("div", {"class": re.compile(r".*price.*original.*", re.IGNORECASE)}),  # Generic original price pattern fallback
        ("span", {"class": re.compile(r".*old.*price.*", re.IGNORECASE)}),  # Generic old price span as last resort fallback
    ],
    "discount": [  # List of CSS selectors for discount percentage in priority order
        ("div", {"class": "vms4_3"}),  # Shopee discount container with specific class
        ("span", {"class": re.compile(r".*discount.*", re.IGNORECASE)}),  # Generic discount span fallback
        ("div", {"class": re.compile(r".*sale.*badge.*", re.IGNORECASE)}),  # Sale badge container as last resort fallback
    ],
    "description": [  # List of CSS selectors for product description in priority order
        ("div", {"class": "e8lZp3"}),  # Shopee description container with specific class
        ("div", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Generic description pattern fallback
        ("section", {"class": re.compile(r".*description.*", re.IGNORECASE)}),  # Section element containing description as last resort fallback
    ],
    "gallery": {"class": "airUhU"},  # CSS selector for product gallery container with images and videos
    "detail_label": {"class": "VJOnTD"},  # CSS selector for product detail labels (used for Category, Country of Origin, etc.)
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


 def __init__(self, url: str, local_html_path: Optional[str] = None, prefix: str = "") -> None:
        """
        Initializes the Shopee scraper with a product URL and optional local HTML file path.

        :param url: The URL of the Shopee product page to scrape
        :param local_html_path: Optional path to a local HTML file for offline scraping
        :param prefix: Optional platform prefix for output directory naming (e.g., "Shopee")
        :return: None
        """

        self.url: str = url  # Store the initial product URL for reference
        self.product_url: str = url  # Maintain separate copy of product URL for Shopee direct usage
        self.local_html_path: Optional[str] = local_html_path  # Store path to local HTML file for offline scraping
        self.html_content: Optional[str] = None  # Store HTML content for reuse (from browser or local file)
        self.product_data: Dict[str, Any] = {}  # Initialize empty dictionary to store extracted product data
        self.prefix: str = prefix  # Store the platform prefix for directory naming
        self.playwright: Optional[Any] = None  # Placeholder for Playwright instance
        self.browser: Optional[Any] = None  # Placeholder for browser instance
        self.page: Optional[Any] = None  # Placeholder for page object

        verbose_output(  # Output initialization message to user
            f"{BackgroundColors.GREEN}Shopee scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
        )  # End of verbose output call
        if local_html_path:  # If local HTML file path is provided
            verbose_output(  # Output offline mode message
                f"{BackgroundColors.GREEN}Offline mode enabled. Will read from: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}"
            )  # End of verbose output call


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
            video_tags = soup.find_all("video", class_="tpgcVs")
            
            verbose_output(  # Log number of videos found
                f"{BackgroundColors.GREEN}Found {BackgroundColors.CYAN}{len(video_tags)}{BackgroundColors.GREEN} video elements.{Style.RESET_ALL}"
            )  # End of verbose output call
            
            for video in video_tags:  # Iterate through each video tag
                if not isinstance(video, Tag):  # Ensure element is a BeautifulSoup Tag
                    continue  # Skip non-Tag elements
                
                video_url = video.get("src") or video.get("data-src")
                
                if video_url and isinstance(video_url, str):  # Verify URL is valid string
                    if video_url not in seen_urls:  # Avoid duplicates
                        video_urls.append(video_url)  # Add video URL to list
                        seen_urls.add(video_url)  # Track this URL
                        
                        verbose_output(  # Log found video URL
                            f"{BackgroundColors.GREEN}Found video: {BackgroundColors.CYAN}{video_url[:100]}{Style.RESET_ALL}"
                        )  # End of verbose output call
                
                source_tags = video.find_all("source")
                for source in source_tags:  # Iterate through each source tag
                    if not isinstance(source, Tag):  # Ensure element is a BeautifulSoup Tag
                        continue  # Skip non-Tag elements
                    
                    source_url = source.get("src") or source.get("data-src")
                    if source_url and isinstance(source_url, str):  # Verify URL is valid string
                        if source_url not in seen_urls:  # Avoid duplicates
                            video_urls.append(source_url)  # Add video URL to list
                            seen_urls.add(source_url)  # Track this URL
                            
                            verbose_output(  # Log found video URL
                                f"{BackgroundColors.GREEN}Found video (source): {BackgroundColors.CYAN}{source_url[:100]}{Style.RESET_ALL}"
                            )  # End of verbose output call
        
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
            
            product_name = self.extract_product_name(soup)  # Extract product name from parsed HTML
            
            is_international = self.detect_international(soup)  # Detect if product is international
            if is_international:  # If product is international
                product_name = self.prefix_international_name(product_name)  # Add INTERNACIONAL prefix to name
            
            current_price_int, current_price_dec = self.extract_current_price(soup)  # Extract current price integer and decimal parts
            old_price_int, old_price_dec = self.extract_old_price(soup)  # Extract old price integer and decimal parts
            discount_percentage = self.extract_discount_percentage(soup)  # Extract discount percentage value
            description = self.extract_product_description(soup)  # Extract product description text
            
            self.product_data = {  # Store all extracted data in dictionary
                "name": product_name,  # Product name string (with INTERNACIONAL prefix if applicable)
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
        output_dir = os.path.join(OUTPUT_DIRECTORY, directory_name)  # Construct full path for product output directory
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
            if is_international and not product_name.startswith("INTERNACIONAL"):
                product_name = f"INTERNACIONAL - {product_name}"
                self.product_data["name"] = product_name  # Update product data with prefixed name
                verbose_output(f"{BackgroundColors.YELLOW}Product name prefixed with 'INTERNACIONAL'.{Style.RESET_ALL}")
            
            product_name_safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in product_name).strip()  # Sanitize product name for filesystem use
            
            output_dir = self.create_output_directory(product_name_safe)  # Create output directory for product
            
            image_files = self.download_product_images(soup, output_dir)  # Download all product images
            downloaded_files.extend(image_files)  # Add image files to downloaded list
            
            video_files = self.download_product_videos(soup, output_dir)  # Download all product videos
            downloaded_files.extend(video_files)  # Add video files to downloaded list
            
            asset_map = self.collect_assets(html_content, output_dir)  # Download and collect all page assets
            
            snapshot_path = self.save_snapshot(html_content, output_dir, asset_map)  # Save HTML snapshot with localized assets
            if snapshot_path:  # Verify if snapshot was saved successfully
                downloaded_files.append(snapshot_path)  # Add snapshot path to downloaded files list
            
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
        Supports both online scraping (via browser) and offline scraping (from local HTML file).

        :param verbose: Boolean flag to enable verbose output
        :return: Dictionary containing all scraped data and downloaded file paths
        """

        print(  # Display scraping start message to user
            f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Starting {BackgroundColors.CYAN}Shopee{BackgroundColors.GREEN} Scraping process...{Style.RESET_ALL}"
        )  # End of print statement
        
        try:  # Attempt scraping process with error handling
            if self.local_html_path:  # If local HTML file path is provided
                print(  # Display offline mode message
                    f"{BackgroundColors.GREEN}Using offline mode with local HTML file{Style.RESET_ALL}"
                )  # End of print statement
                
                html_content = self.read_local_html()  # Read HTML content from local file
                if not html_content:  # Verify if HTML reading failed
                    return None  # Return None if HTML is unavailable
                
                self.html_content = html_content  # Store HTML content for later use
                
            else:  # Online scraping mode
                print(  # Display online mode message
                    f"{BackgroundColors.GREEN}Using online mode with browser automation{Style.RESET_ALL}"
                )  # End of print statement
                
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
            
            print(  # Display success message to user
                f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Shopee scraping completed successfully!{Style.RESET_ALL}"
            )  # End of print statement
            
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
