"""
================================================================================
Mercado Livre Web Scraper
================================================================================
Author      : Breno Farias da Silva
Created     : 2026-02-04
Description :
    This script provides a MercadoLivre class for scraping product information
    from Mercado Livre product pages. It extracts comprehensive product details
    including name, prices, discount information, descriptions, and media assets.

    Key features include:
        - Automatic product URL extraction from listing pages
        - Product name and description extraction
        - Price information (current and old prices with integer and decimal parts)
        - Discount percentage extraction
        - Product images download
        - Product description file generation in marketing template format
        - Organized output in product-specific directories

Usage:
    1. Import the MercadoLivre class in your main script.
    2. Create an instance with a product URL:
            scraper = MercadoLivre("https://mercadolivre.com.br/product-url")
    3. Call the scrape method to extract product information:
            product_data = scraper.scrape()
    4. Media files are saved in ./Outputs/{Product Name}/ directory.

Outputs:
    - Product data dictionary with all extracted information
    - Downloaded images in ./Outputs/{Product Name}/ directory
    - Product description .txt file with marketing template in ./Outputs/{Product Name}/ directory
    - Log files in ./Logs/ directory

TODOs:
    - Add support for multiple product variations
    - Implement retry mechanism for failed requests
    - Add data export to CSV/JSON formats
    - Implement rate limiting to respect website policies

Dependencies:
    - Python >= 3.8
    - requests
    - beautifulsoup4
    - lxml
    - colorama

Assumptions & Notes:
    - Requires stable internet connection
    - Website structure may change over time
    - Respects robots.txt and ethical scraping practices
    - Creates output directories automatically if they don't exist
"""

import atexit  # For playing a sound when the program finishes
import datetime  # For getting the current date and time
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import re  # For regular expressions
import requests  # For making HTTP requests
import sys  # For system-specific parameters and functions
from bs4 import BeautifulSoup, Tag  # For parsing HTML content
from colorama import Style  # For coloring the terminal
from Logger import Logger  # For logging output to both terminal and file
from main import create_directory  # For creating directories
from pathlib import Path  # For handling file paths
from urllib.parse import urlparse  # For URL manipulation


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
OUTPUT_DIRECTORY = "./Outputs/"  # The base path to the output directory

# Template Constants:
PRODUCT_DESCRIPTION_TEMPLATE = """Product Name: {product_name}

Price: From R${current_price} to R${old_price} ({discount} OFF)

Description: {description}

🛒 Encontre no Mercado Livre:
👉 {url}"""

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


class MercadoLivre:
    """
    A web scraper class for extracting product information from Mercado Livre.
    
    This class handles the extraction of product details including name, prices,
    discounts, descriptions, and media files from Mercado Livre product pages.
    It also generates a marketing description file in a predefined template format.
    """

    def __init__(self, url):
        """
        Initializes the MercadoLivre scraper with a product URL.

        :param url: The URL of the Mercado Livre product page to scrape
        :return: None
        """

        self.url = url  # Store the initial URL
        self.product_url = None  # Will store the actual product page URL
        self.session = requests.Session()  # Create a session for making requests
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })  # Set a realistic User-Agent to avoid being blocked
        self.product_data = {}  # Dictionary to store scraped product data

        verbose_output(
            f"{BackgroundColors.GREEN}MercadoLivre scraper initialized with URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
        )  # Output the verbose message

    def get_product_url(self):
        """
        Extracts the actual product URL from the listing page by finding the href
        that comes right before the "Ir para produto" button.

        :return: The product URL if found, None otherwise
        """

        verbose_output(
            f"{BackgroundColors.GREEN}Extracting product URL from listing page...{Style.RESET_ALL}"
        )  # Output the verbose message

        try:  # Try to fetch and parse the page
            response = self.session.get(self.url, timeout=10)  # Make a GET request to the URL
            response.raise_for_status()  # Raise an exception for bad status codes
            
            soup = BeautifulSoup(response.content, "html.parser")  # Parse the HTML content
            
            ir_para_produto = soup.find(string=re.compile(r"Ir para produto", re.IGNORECASE))  # Find the "Ir para produto" text
            
            if ir_para_produto:  # If the button text was found
                parent_link = ir_para_produto.find_parent("a")  # Find the parent anchor tag
                
                if isinstance(parent_link, Tag):  # If a parent link was found and is a Tag
                    href = parent_link.get("href")  # Extract the href attribute
                    if href and isinstance(href, str):  # If href exists and is a string
                        self.product_url = href  # Store the product URL
                        print(
                            f"{BackgroundColors.GREEN}Product URL found: {BackgroundColors.CYAN}{self.product_url}{Style.RESET_ALL}"
                        )  # Output the success message
                        return self.product_url  # Return the product URL
            
            product_links = soup.find_all("a", href=re.compile(r"/p/|/MLB"))  # Find all product links
            
            if product_links:  # If product links were found
                first_link = product_links[0]  # Get the first product link
                if isinstance(first_link, Tag):  # If it's a Tag element
                    href = first_link.get("href")  # Get the href attribute
                    if href and isinstance(href, str):  # If href exists and is a string
                        self.product_url = href  # Store the product URL
                        print(
                            f"{BackgroundColors.GREEN}Product URL found (alternative method): {BackgroundColors.CYAN}{self.product_url}{Style.RESET_ALL}"
                        )  # Output the success message
                        return self.product_url  # Return the product URL
            
            print(
                f"{BackgroundColors.YELLOW}Could not find product URL. Using original URL.{Style.RESET_ALL}"
            )  # Output the warning message
            self.product_url = self.url  # Use the original URL as fallback
            return self.product_url  # Return the URL
            
        except requests.RequestException as e:  # If a request error occurred
            print(
                f"{BackgroundColors.RED}Error fetching listing page: {e}{Style.RESET_ALL}"
            )  # Output the error message
            self.product_url = self.url  # Use the original URL as fallback
            return self.product_url  # Return the URL
        except Exception as e:  # If any other error occurred
            print(
                f"{BackgroundColors.RED}Unexpected error in get_product_url: {e}{Style.RESET_ALL}"
            )  # Output the error message
            self.product_url = self.url  # Use the original URL as fallback
            return self.product_url  # Return the URL

    def extract_product_name(self, soup):
        """
        Extracts the product name from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product name string or "Unknown Product" if not found
        """
        
        name_element = soup.find(class_="ui-pdp-title")  # Find the product name element
        product_name = name_element.get_text(strip=True) if name_element else "Unknown Product"  # Extract the product name
        
        verbose_output(
            f"{BackgroundColors.GREEN}Product name: {BackgroundColors.CYAN}{product_name}{Style.RESET_ALL}"
        )  # Output the verbose message
        
        return product_name  # Return the product name

    def extract_current_price(self, soup):
        """
        Extracts the current price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for current price
        """
        
        current_price_container = soup.find("span", class_=re.compile(r"andes-money-amount.*andes-money-amount--superscript-36"))  # Find the current price with superscript-36 cents
        if current_price_container and isinstance(current_price_container, Tag):  # If found
            current_fraction = current_price_container.find(class_="andes-money-amount__fraction")  # Find the fraction within this container
            current_cents = current_price_container.find(class_="andes-money-amount__cents")  # Find the cents within this container
            
            integer_part = current_fraction.get_text(strip=True) if current_fraction and isinstance(current_fraction, Tag) else "0"  # Extract integer part
            decimal_part = current_cents.get_text(strip=True) if current_cents and isinstance(current_cents, Tag) else "00"  # Extract decimal part
        else:  # If not found
            cents_element = soup.find(class_="andes-money-amount__cents--superscript-36")  # Find the cents with superscript-36
            if cents_element and isinstance(cents_element, Tag):  # If found
                parent = cents_element.find_parent(class_=re.compile(r"andes-money-amount"))  # Find the parent container
                if parent and isinstance(parent, Tag):  # If parent found
                    fraction = parent.find(class_="andes-money-amount__fraction")  # Find the fraction within this container
                    integer_part = fraction.get_text(strip=True) if fraction and isinstance(fraction, Tag) else "0"  # Extract integer part
                    decimal_part = cents_element.get_text(strip=True)  # Extract decimal part
                else:  # If parent not found
                    integer_part = "0"  # Default integer part
                    decimal_part = "00"  # Default decimal part
            else:  # If no superscript-36 cents found
                integer_part = "0"  # Default integer part
                decimal_part = "00"  # Default decimal part
        
        return integer_part, decimal_part  # Return the price parts

    def extract_old_price(self, soup):
        """
        Extracts the old price from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Tuple of (integer_part, decimal_part) for old price
        """
        
        old_price_container = soup.find("span", class_=re.compile(r"andes-money-amount.*andes-money-amount--superscript-16"))  # Find the old price with superscript-16 cents
        if old_price_container and isinstance(old_price_container, Tag):  # If found
            old_fraction = old_price_container.find(class_="andes-money-amount__fraction")  # Find the fraction within this container
            old_cents = old_price_container.find(class_="andes-money-amount__cents")  # Find the cents within this container
            
            integer_part = old_fraction.get_text(strip=True) if old_fraction and isinstance(old_fraction, Tag) else "N/A"  # Extract integer part
            decimal_part = old_cents.get_text(strip=True) if old_cents and isinstance(old_cents, Tag) else "N/A"  # Extract decimal part
        else:  # If not found
            all_prices = soup.find_all(class_="andes-money-amount__fraction")  # Find all price fractions
            if len(all_prices) > 1:  # If more than one price found
                first_fraction = all_prices[0]  # Assume the first is the old price
                if isinstance(first_fraction, Tag):  # If it's a Tag
                    integer_part = first_fraction.get_text(strip=True)  # Extract integer part
                    parent = first_fraction.find_parent(class_=re.compile(r"andes-money-amount"))  # Find the parent container
                    if parent and isinstance(parent, Tag):  # If parent found
                        cents = parent.find(class_="andes-money-amount__cents")  # Find the cents within this container
                        decimal_part = cents.get_text(strip=True) if cents and isinstance(cents, Tag) else "00"  # Extract decimal part
                    else:  # If parent not found
                        decimal_part = "00"  # Default decimal part
                else:  # If not a Tag
                    integer_part = "N/A"  # Default to N/A
                    decimal_part = "N/A"  # Default to N/A
            else:  # If no old price found
                integer_part = "N/A"  # Default to N/A
                decimal_part = "N/A"  # Default to N/A
        
        return integer_part, decimal_part  # Return the price parts

    def extract_discount_percentage(self, soup):
        """
        Extracts the discount percentage from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Discount percentage string or "N/A" if not found
        """
        
        discount_element = soup.find(class_=re.compile(r"andes-money-amount__discount.*ui-pdp-family--SEMIBOLD.*ui-pdp-color--GREEN", re.IGNORECASE))  # Find discount element
        discount_percentage = discount_element.get_text(strip=True) if discount_element else "N/A"  # Extract discount percentage
        
        return discount_percentage  # Return the discount percentage

    def extract_product_description(self, soup):
        """
        Extracts the product description from the parsed HTML soup.
        
        :param soup: BeautifulSoup object containing the parsed HTML
        :return: Product description string or "No description available" if not found
        """
        
        description_element = soup.find(class_="ui-pdp-description__content")  # Find description title element
        description = description_element.get_text(strip=True) if description_element else "No description available"  # Extract description
        
        return description  # Return the description

    def print_product_info(self, product_data):
        """
        Prints the extracted product information in a formatted manner.
        
        :param product_data: Dictionary containing the scraped product data
        :return: None
        """
        
        if not product_data:  # If no product data
            print(f"{BackgroundColors.RED}No product data to display.{Style.RESET_ALL}")  # Output the error message
            return  # Return early
        
        print(
            f"{BackgroundColors.GREEN}Product information extracted successfully:{Style.RESET_ALL}\n"
            f"  {BackgroundColors.CYAN}Name:{Style.RESET_ALL} {product_data.get('name', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Old Price:{Style.RESET_ALL} R${product_data.get('old_price_integer', 'N/A')},{product_data.get('old_price_decimal', 'N/A') if product_data.get('old_price_integer', 'N/A') != 'N/A' else 'N/A'}\n"
            f"  {BackgroundColors.CYAN}Current Price:{Style.RESET_ALL} R${product_data.get('current_price_integer', 'N/A')},{product_data.get('current_price_decimal', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Discount:{Style.RESET_ALL} {product_data.get('discount_percentage', 'N/A')}\n"
            f"  {BackgroundColors.CYAN}Description:{Style.RESET_ALL} {product_data.get('description', 'N/A')[:100]}..."
        )  # Output the extracted information

    def scrape_product_info(self, verbose_output):
        """
        Scrapes product information from the product page by orchestrating
        the extraction of individual data components.

        :param verbose_output: Function to output verbose messages
        :return: Dictionary containing the scraped product data
        """

        verbose_output(
            f"{BackgroundColors.GREEN}Scraping product information from: {BackgroundColors.CYAN}{self.product_url}{Style.RESET_ALL}"
        )  # Output the verbose message

        if not self.product_url or not isinstance(self.product_url, str):  # If product URL is invalid
            print(
                f"{BackgroundColors.RED}Invalid product URL. Cannot scrape product information.{Style.RESET_ALL}"
            )  # Output the error message
            return None  # Return None on invalid URL

        try:  # Try to fetch and parse the product page
            response = self.session.get(self.product_url, timeout=10)  # Make a GET request to the product URL
            response.raise_for_status()  # Raise an exception for bad status codes
            
            soup = BeautifulSoup(response.content, "html.parser")  # Parse the HTML content
            
            self.product_data["name"] = self.extract_product_name(soup)  # Extract product name
            
            current_price_int, current_price_dec = self.extract_current_price(soup)  # Extract current price
            self.product_data["current_price_integer"] = current_price_int  # Store integer part
            self.product_data["current_price_decimal"] = current_price_dec  # Store decimal part
            
            old_price_int, old_price_dec = self.extract_old_price(soup)  # Extract old price
            self.product_data["old_price_integer"] = old_price_int  # Store integer part
            self.product_data["old_price_decimal"] = old_price_dec  # Store decimal part
            
            self.product_data["discount_percentage"] = self.extract_discount_percentage(soup)  # Extract discount percentage
            self.product_data["description"] = self.extract_product_description(soup)  # Extract product description
            
            self.print_product_info(self.product_data)  if VERBOSE else None  # Print the extracted product information if verbose
            
            return self.product_data  # Return the scraped data
            
        except requests.RequestException as e:  # If a request error occurred
            print(
                f"{BackgroundColors.RED}Error fetching product page: {e}{Style.RESET_ALL}"
            )  # Output the error message
            return None  # Return None on error
        except Exception as e:  # If any other error occurred
            print(
                f"{BackgroundColors.RED}Unexpected error in scrape_product_info: {e}{Style.RESET_ALL}"
            )  # Output the error message
            return None  # Return None on error

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

    def to_sentence_case(self, text):
        """
        Converts text to sentence case (first letter of each sentence uppercase).
        
        :param text: The text to convert
        :return: Text in sentence case
        """
        
        if not text:  # If text is empty
            return text  # Return as is
        
        sentences = re.split(r"([.!?]\s*)", text)  # Keep the delimiters
        
        result = []  # List to store processed sentences
        for i, sentence in enumerate(sentences):  # Iterate through sentences
            if sentence.strip():  # If sentence is not empty
                if i % 2 == 0:  # Even indices are the actual sentence content
                    sentence = sentence.strip()  # Strip leading/trailing whitespace
                    if sentence:  # If still not empty
                        sentence = sentence[0].upper() + sentence[1:].lower()  # Capitalize first letter
                result.append(sentence)  # Add to result
        
        return "".join(result)  # Join and return

    def create_output_directory(self, product_name_safe):
        """
        Creates the output directory for storing downloaded media files.
        
        :param product_name_safe: Safe product name for directory naming
        :return: Path to the created output directory
        """
        
        output_dir = os.path.join(OUTPUT_DIRECTORY, product_name_safe)  # Create the output directory path
        create_directory(os.path.abspath(output_dir), output_dir.replace(".", ""))  # Create the output directory
        
        return output_dir  # Return the output directory path

    def fetch_product_page(self, session, product_url):
        """
        Fetches the product page and returns the parsed BeautifulSoup object.
        
        :param session: Requests session object
        :param product_url: URL of the product page
        :return: BeautifulSoup object containing the parsed HTML
        """
        
        response = session.get(product_url, timeout=10)  # Make a GET request to the product URL
        response.raise_for_status()  # Raise exception for bad status
        soup = BeautifulSoup(response.content, "html.parser")  # Parse the HTML content
        
        return soup  # Return the parsed soup


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

    env_path = Path(__file__).parent / ".env"  # Path to the .env file
    
    if not verify_filepath_exists(env_path):  # If the .env file does not exist
        print(f"{BackgroundColors.CYAN}.env{BackgroundColors.YELLOW} file not found at {BackgroundColors.CYAN}{env_path}{BackgroundColors.YELLOW}.{Style.RESET_ALL}")
        return False  # Return False

    return True  # Return True if the .env file exists


def output_result(result):
    """
    Outputs the result to the terminal.

    :param result: The result to be outputted
    :return: None
    """

    if result:  # If scraping was successful
        verbose_output(
            f"\n{BackgroundColors.GREEN}Scraping completed successfully!{Style.RESET_ALL}\n"
            f"{BackgroundColors.CYAN}Results:{Style.RESET_ALL}\n"
            f"  Name: {result.get('name', 'N/A')}\n"
            f"  Old Price: {result.get('old_price_integer', 'N/A')}.{result.get('old_price_decimal', 'N/A')}\n"
            f"  Current Price: {result.get('current_price_integer', 'N/A')}.{result.get('current_price_decimal', 'N/A')}\n"
            f"  Discount: {result.get('discount_percentage', 'N/A')}\n"
            f"  Description: {result.get('description', 'N/A')[:100]}...\n"
            f"  Downloaded Media: {len(result.get('downloaded_media', []))} files\n"
        )  # Output the results
    else:  # If scraping failed
        print(
            f"\n{BackgroundColors.RED}Scraping failed. Please check the URL and try again.{Style.RESET_ALL}\n"
        )  # Output the error message


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
        f"{BackgroundColors.CLEAR_TERMINAL}{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}Mercado Livre Scraper Test{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
        end="\n\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program

    test_url = "https://mercadolivre.com/sec/2XY9zrA"  # Test URL
    
    verbose_output(
        f"{BackgroundColors.GREEN}Testing MercadoLivre scraper with URL: {BackgroundColors.CYAN}{test_url}{Style.RESET_ALL}\n"
    )  # Output the test URL
    
    try:  # Try to scrape the product
        scraper = MercadoLivre(test_url)  # Create a MercadoLivre instance
        result = scraper.scrape(VERBOSE)  # Scrape the product
        output_result(result)  # Output the result
    except Exception as e:  # If an error occurred
        print(
            f"\n{BackgroundColors.RED}Error during scraping: {e}{Style.RESET_ALL}\n"
        )  # Output the error message

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
