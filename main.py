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
    4. Verify outputs in the ./Outputs/ directory for scraped data.

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
import hashlib  # For hashing image data
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import re # For regular expressions in text processing
import shutil  # For removing directories
import sys  # For system-specific parameters and functions
import time  # For adding delays between requests
import zipfile  # For handling zip files
from tqdm import tqdm  # Progress bar for URL processing
# from AliExpress import AliExpress  # Import the AliExpress class
from colorama import Style  # For coloring the terminal
from dotenv import load_dotenv  # For loading environment variables
from Gemini import Gemini  # Import the Gemini class
from Logger import Logger  # For logging output to both terminal and file
from MercadoLivre import MercadoLivre  # Import the MercadoLivre class
from pathlib import Path  # For handling file paths
from PIL import Image  # For image processing
from Shein import Shein  # Import the Shein class
from Shopee import Shopee  # Import the Shopee class


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

TEST_URLs = [""]  # Test URLs for scraping

PLATFORMS_MAP = {
    "AliExpress": "aliexpress",
    "MercadoLivre": "mercadolivre",
    "Shein": "shein",
    "Shopee": "shopee",
}  # Mapping of platform names to identifiers

PLATFORM_PREFIXES = {
    "aliexpress": "AliExpress",
    "mercadolivre": "MercadoLivre",
    "shein": "Shein",
    "shopee": "Shopee",
}  # Mapping of platform identifiers to display prefixes for output directories

PLATFORM_PREFIX_SEPARATOR = " - "  # Separator between platform prefix and product name in directory structure
    

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

# Delay Constants:
DELAY_BETWEEN_REQUESTS = 5  # Seconds to wait between processing URLs to avoid rate limiting

# Gemini AI Constants:
GEMINI_MARKETING_PROMPT_TEMPLATE = """Você é um especialista em marketing de e-commerce. Sua tarefa é transformar as informações do produto abaixo em um texto de marketing persuasivo, chamativo, direto e formatado.

INFORMAÇÕES DO PRODUTO:
{product_description}

FORMATO OBRIGATÓRIO (siga EXATAMENTE este formato):
*{{{{NOME DO PRODUTO}}}} – {{{{DIFERENCIAL CURTO}}}}*

💰 DE *R${{{{PREÇO_ANTIGO}}}}* POR APENAS *R${{{{PREÇO_ATUAL}}}}* (SE DISPONÍVEL)
🎟️ *{{{{INFORMAÇÃO DE CUPOM / % DE DESCONTO}}}}* (SE DISPONÍVEL)

*{{{{FRASE DE IMPACTO / BENEFÍCIO PRINCIPAL}}}}*

✨ {{{{CARACTERÍSTICA 1}}}}
✨ {{{{CARACTERÍSTICA 2}}}}
✨ {{{{ONDE / COMO USAR}}}}
✨ {{{{IDEIA DE PRESENTE / OCASIÃO}}}}

🛒 Encontre na {{{{LOJA / PLATAFORMA}}}}:
👉 {{{{LINK DO PRODUTO}}}}

INSTRUÇÕES:
1. Use as informações fornecidas para preencher cada campo
2. Seja persuasivo, criativo e chamativo
3. Mantenha o formato EXATAMENTE como mostrado
4. Use os preços e descontos reais do produto quando disponíveis
5. Se o preço antigo ou desconto não estiver disponível (N/A), OMITA essas linhas completamente
6. Inclua o link real do produto
7. Crie 2-3 características principais marcantes
8. Sugira onde/como usar o produto
9. Se aplicável, sugira como presente ou ocasião especial
10. Para o desconto, quando existir, nunca usar o termo "off", prefira algo como "20% de Desconto!"
11. O texto final NÃO pode ultrapassar 1000 caracteres (incluindo espaços e emojis)
12. Seja direto, evite parágrafos longos e evite textos explicativos extensos — consumidores não gostam de ler textos longos
13. Priorize frases curtas, objetivas e de alto impacto

Gere APENAS o texto formatado, sem explicações adicionais."""  # Template for Gemini AI marketing text generation

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


def ensure_input_file_exists():
    """
    Ensure the input file exists; create an empty one if missing.

    :param: None
    :return: True if the input file exists or was created successfully, False otherwise
    """

    if not verify_filepath_exists(INPUT_FILE):  # Verify if the input file exists
        try:  # Attempt to create an empty input file
            open(INPUT_FILE, "w", encoding="utf-8").close()  # Create an empty file at INPUT_FILE
            verbose_output(  # Verbose message indicating creation
                f"{BackgroundColors.GREEN}Created empty input file: {BackgroundColors.CYAN}{INPUT_FILE}{Style.RESET_ALL}"
            )  # Output the verbose message
            return True  # Return True when file was created successfully
        except Exception as e:  # If creating the file fails
            print(  # Print the failure message so user can see the error
                f"{BackgroundColors.RED}Failed to create input file {BackgroundColors.CYAN}{INPUT_FILE}{BackgroundColors.RED}: {e}{Style.RESET_ALL}"
            )  # Output reason for failure
            return False  # Return False to indicate failure to ensure file
    return True  # Return True when file already exists


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


def clean_unknown_product_directories(output_directory):
    """
    Cleans up any "Unknown Product" directories from previous runs in the output directory.

    :param output_directory: The path to the output directory to clean
    :return: None
    """
    
    verbose_output(
        f"{BackgroundColors.GREEN}Cleaning up any 'Unknown Product' directories in {BackgroundColors.CYAN}{output_directory}{BackgroundColors.GREEN}...{Style.RESET_ALL}"
    )
    
    try:  # Try to clean up "Unknown Product" directories
        for item in os.listdir(output_directory):  # List all items in the output directory
            item_path = os.path.join(output_directory, item)  # Get the full path of the item
            if os.path.isdir(item_path) and item == "Unknown Product":  # If the item is a directory named "Unknown Product"
                shutil.rmtree(item_path)  # Remove the directory and its contents
                verbose_output(f"{BackgroundColors.YELLOW}Removed old 'Unknown Product' directory: {item_path}{Style.RESET_ALL}")
    except Exception as e:  # If an error occurs during cleanup
        print(f"{BackgroundColors.RED}Error during cleanup of 'Unknown Product' directories: {e}{Style.RESET_ALL}")


def get_image_files(product_dir):
    """
    Retrieves a list of image files from the specified product directory.

    :param product_dir: Path to the product directory
    :return: List of image filenames (webp, jpg, jpeg, png)
    """
    
    return [f for f in os.listdir(product_dir) if f.lower().endswith((".webp", ".jpg", ".jpeg", ".png"))]


def load_images(product_dir, image_files):
    """
    Loads image objects from the list of image files using PIL.

    :param product_dir: Path to the product directory
    :param image_files: List of image filenames
    :return: List of tuples (image_path, size_tuple, PIL_Image_object)
    """
    
    images = []  # List to store loaded images
    for img_file in image_files:  # Iterate through image files
        img_path = os.path.join(product_dir, img_file)  # Get the full path of the image file
        try:  # Try to open the image
            img = Image.open(img_path)  # Open the image using PIL
            images.append((img_path, img.size, img))  # Store the image path, size, and object
        except Exception as e:  # If opening the image fails
            print(f"{BackgroundColors.RED}Error opening image {img_path}: {e}{Style.RESET_ALL}")
    
    return images  # Return the list of loaded images


def find_min_dimensions(images):
    """
    Finds the minimum width and height across all loaded images.

    :param images: List of tuples (image_path, size_tuple, PIL_Image_object)
    :return: Tuple (min_width, min_height)
    """
    
    min_width = min(size[0] for _, size, _ in images)  # Find the minimum width
    min_height = min(size[1] for _, size, _ in images)  # Find the minimum height
    
    return min_width, min_height  # Return the minimum dimensions


def group_images_by_resized_hash(images, min_width, min_height):
    """
    Groups images by their MD5 hash after resizing to the minimum dimensions.
    This detects duplicates by content similarity after normalization.

    :param images: List of tuples (image_path, size_tuple, PIL_Image_object)
    :param min_width: Minimum width to resize to
    :param min_height: Minimum height to resize to
    :return: Dictionary with hash as key, list of (image_path, pixel_count) as values
    """
    
    groups = {}  # Dictionary to group images by hash
    
    for img_path, size, img in images:  # Iterate through loaded images
        resized = img.resize((min_width, min_height), Image.Resampling.LANCZOS)  # Resize image to minimum dimensions
        resized_bytes = resized.tobytes()  # Get the byte representation of the resized image
        img_hash = hashlib.md5(resized_bytes).hexdigest()  # Compute MD5 hash of the resized image
    
        if img_hash not in groups:  # If this hash is not yet in the groups
            groups[img_hash] = []  # Initialize a new list for this hash
        groups[img_hash].append((img_path, size[0] * size[1]))  # store path and pixel count
    
    return groups  # Return the grouped images


def remove_duplicate_images(groups):
    """
    For each group of duplicate images (same hash), keeps the highest resolution version
    and deletes the lower resolution duplicates.

    :param groups: Dictionary with hash as key, list of (image_path, pixel_count) as values
    :return: None
    """
    
    for img_hash, group in groups.items():  # Iterate through each group of images
        if len(group) > 1:  # If there are duplicates in this group
            group.sort(key=lambda x: x[1], reverse=True)  # Sort by pixel count descending (highest resolution first)
            for img_path, _ in group[1:]:  # Delete all except the first (highest res)
                try:  # Try to remove the duplicate image
                    os.remove(img_path)  # Remove the image file
                    verbose_output(f"{BackgroundColors.YELLOW}Removed duplicate image: {BackgroundColors.CYAN}{img_path}{Style.RESET_ALL}")
                except Exception as e:  # If an error occurs while removing the image
                    print(f"{BackgroundColors.RED}Error removing image {BackgroundColors.CYAN}{img_path}{BackgroundColors.RED}: {BackgroundColors.YELLOW}{e}{Style.RESET_ALL}")


def clean_duplicate_images(product_directory):
    """
    Cleans up duplicate images in the product directory by normalizing all images to the smallest size,
    computing MD5 hashes of the resized versions, and removing lower-resolution duplicates while keeping
    the highest-resolution version of each unique image.

    This approach detects duplicates that may have different resolutions but represent the same content,
    such as thumbnails and full-size images.

    :param product_directory: Directory name (may include platform prefix) for the product
    :return: None
    """
    
    product_dir = os.path.join(OUTPUT_DIRECTORY, product_directory)  # Path to the product directory
    if not os.path.exists(product_dir):  # If the product directory does not exist
        return  # Return if the directory does not exist
    
    image_files = get_image_files(product_dir)  # Get list of image files
    if len(image_files) < 2:  # If there are less than 2 images, no duplicates possible
        return
    
    images = load_images(product_dir, image_files)  # Load images using PIL
    if not images:  # If no images were loaded successfully
        return  # Return if no images loaded
    
    min_width, min_height = find_min_dimensions(images)  # Find minimum dimensions among images
    groups = group_images_by_resized_hash(images, min_width, min_height)  # Group images by hash of resized versions
    remove_duplicate_images(groups)  # Remove duplicate images


def exclude_small_images(product_directory, min_size_bytes=2048):
    """
    Excludes (deletes) image files smaller than the specified minimum size in bytes.
    This helps remove very small or corrupted images that are likely thumbnails or placeholders.

    :param product_directory: Directory name (may include platform prefix) for the product
    :param min_size_bytes: Minimum file size in bytes (default 2048 = 2KB)
    :return: None
    """
    
    product_dir = os.path.join(OUTPUT_DIRECTORY, product_directory)  # Path to the product directory
    
    if not os.path.exists(product_dir):  # If the product directory does not exist
        return  # Return if the directory does not exist
    
    image_files = get_image_files(product_dir)  # Get list of image files
    for img_file in image_files:  # Iterate through image files
        img_path = os.path.join(product_dir, img_file)  # Get the full path of the image file
        try:  # Try to get the file size
            size = os.path.getsize(img_path)  # Get the size of the image file in bytes
            if size < min_size_bytes:  # If the image file is smaller than the minimum size
                os.remove(img_path)  # Remove the image file
                verbose_output(f"{BackgroundColors.YELLOW}Removed small image (<{min_size_bytes} bytes): {BackgroundColors.CYAN}{img_path}{Style.RESET_ALL}")
        except Exception as e:  # If an error occurs while verify/removing the image
            print(f"{BackgroundColors.RED}Error verify/removing image {BackgroundColors.CYAN}{img_path}{BackgroundColors.RED}: {BackgroundColors.YELLOW}{e}{Style.RESET_ALL}")

def load_urls_to_process(test_urls, input_file):
    """
    Determine and return the list of URLs and optional local HTML paths to process.

    Priority:
        1) Non-empty entries in `test_urls` (keeps order and strips whitespace).
        2) If none present, read one URL per line from `input_file` (ignore blank lines).
           Each line can be either:
           - Just a URL (for online scraping)
           - URL local_html_path (space-separated, for offline scraping)

    Args:
        test_urls (list): list of test URL strings (may contain empty/blank entries).
        input_file (str): path to the input file to read fallback URLs from.

    Returns:
        list: list of tuples (url, local_html_path) where local_html_path may be None.
    """

    urls_from_test = [u.strip() for u in (test_urls or []) if u and u.strip()]  # Normalize and filter non-empty test URLs first
    if urls_from_test:  # If any valid test URLs found
        return [(url, None) for url in urls_from_test]  # Return test URLs as tuples with None for local_html_path

    url_data = []  # List to store URL tuples (url, local_html_path)
    
    try:  # Try to read URLs from input file
        if verify_filepath_exists(input_file):  # If the input file exists
            with open(input_file, "r", encoding="utf-8") as fh:  # Open the input file with UTF-8 encoding
                for line in fh:  # Read each line in the file
                    line = line.strip()  # Strip whitespace
                    if line:  # If the line is not empty
                        parts = line.split(maxsplit=1)  # Split by first space to separate URL and local_html_path
                        url = parts[0]  # First part is always the URL
                        local_html_path = parts[1] if len(parts) > 1 else None  # Second part is optional local_html_path
                        url_data.append((url, local_html_path))  # Add tuple to the list
        else:  # If the input file does not exist
            print(f"{BackgroundColors.YELLOW}Input file not found: {input_file}{Style.RESET_ALL}")
    except Exception as e:  # If an error occurs while reading the file
        print(f"{BackgroundColors.RED}Error reading input file {input_file}: {e}{Style.RESET_ALL}")

    return url_data  # Return the list of URL tuples


def sanitize_filename(filename):
    """
    Sanitizes a filename by removing invalid characters for filesystem compatibility.
    
    :param filename: The filename string to sanitize
    :return: Sanitized filename string containing only alphanumeric characters, spaces, hyphens, and underscores
    """
    
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in filename).strip()  # Remove invalid characters


def detect_platform(url):
    """
    Detects the e-commerce platform from a given URL by verifying domain names.
    
    :param url: The product URL to analyze
    :return: Platform name (e.g., 'mercadolivre', 'shein', 'shopee') or None if not recognized
    """
    
    url_lower = url.lower()  # Convert URL to lowercase for case-insensitive matching
    
    for platform_name, platform_id in PLATFORMS_MAP.items():  # Iterate through supported platforms
        if platform_id in url_lower:  # Verify if platform identifier is in URL
            verbose_output(
                f"{BackgroundColors.GREEN}Detected platform: {BackgroundColors.CYAN}{platform_name}{Style.RESET_ALL}"
            )
            return platform_id  # Return the platform identifier
    
    print(f"{BackgroundColors.YELLOW}Warning: Could not detect platform from URL: {url}{Style.RESET_ALL}")
    return None  # Return None if platform not recognized


def verify_affiliate_url_format(url):
    """
    Verify if a URL uses the supported short affiliate redirect format.

    :param url: The product URL to verify
    :return: None
    """

    platform_id = detect_platform(url)  # Detect platform from the URL
    platform_modules = {  # Mapping of platform ids to scraper modules
        "mercadolivre": MercadoLivre,  # MercadoLivre module
        "shein": Shein,  # Shein module
        "shopee": Shopee,  # Shopee module
    }  # End mapping

    module = platform_modules.get(platform_id)  # Retrieve module for detected platform
    if module is None:  # If platform unsupported, nothing to validate
        return  # Exit early

    pattern = getattr(module, "AFFILIATE_URL_PATTERN", None)  # Get affiliate regex pattern
    if not pattern:  # If pattern not defined, nothing to validate
        return  # Exit early

    try:  # Attempt regex match
        if not re.search(pattern, url, flags=re.IGNORECASE):  # If URL does not match affiliate pattern
            print(f"{BackgroundColors.YELLOW}Warning: URL is not in the expected affiliate format for {platform_id}: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}")  # Print warning
    except re.error:  # If the pattern is invalid
        print(f"{BackgroundColors.YELLOW}Warning: invalid affiliate regex for {platform_id}.{Style.RESET_ALL}")  # Print invalid-regex warning


def resolve_local_html_path(local_html_path):
    """
    Attempts to resolve a local HTML path by trying various common variations.
    
    Tries the following variations in order:
    1. Path as provided
    2. With ./Inputs/ prefix
    3. With .zip suffix
    4. With /index.html suffix
    5. Combinations of prefix and suffixes
    6. If path ends with .html, try the base directory (without HTML filename):
       - As directory (reconstructing the full HTML path)
       - With ./Inputs/ prefix as directory
       - With .zip suffix
       - With ./Inputs/ prefix and .zip suffix
    
    :param local_html_path: The original path to resolve
    :return: Resolved path if found, original path if not found
    """
    
    if not local_html_path:  # If no path provided
        return local_html_path  # Return as-is
    
    if verify_filepath_exists(local_html_path):  # If path exists as provided
        verbose_output(f"{BackgroundColors.GREEN}Resolved local HTML path: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}")  # Confirm resolution
        return local_html_path  # Return original path
    
    prefixes = ["", "./Inputs/"]  # Empty prefix (already tried) and Inputs directory prefix
    suffixes = ["", ".zip", "/index.html"]  # Empty suffix (already tried), zip extension, and index.html file
    
    for prefix in prefixes:  # Iterate through prefixes
        for suffix in suffixes:  # Iterate through suffixes
            if prefix == "" and suffix == "":  # If both prefix and suffix are empty
                continue  # Skip this combination as it's the original path
            
            test_path = f"{prefix}{local_html_path}{suffix}"  # Construct test path with prefix and suffix
            if verify_filepath_exists(test_path):  # If test path exists
                verbose_output(  # Output resolution message
                    f"{BackgroundColors.GREEN}Resolved local HTML path: {BackgroundColors.CYAN}{local_html_path}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}"
                )  # End of verbose output call
                verbose_output(f"{BackgroundColors.GREEN}Resolved path variation: {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}")  # Inform user about resolution
                return test_path  # Return resolved path
    
    if local_html_path.lower().endswith('.html'):  # Verify if path ends with .html extension
        last_slash_idx = local_html_path.rfind('/')  # Find the last slash in the path
        if last_slash_idx != -1:  # If there's a slash, we can extract base path
            base_path = local_html_path[:last_slash_idx]  # Remove /filename.html to get base directory path
            html_filename = local_html_path[last_slash_idx + 1:]  # Extract the HTML filename for reconstruction
            
            verbose_output(  # Output verbose message about base path resolution attempt
                f"{BackgroundColors.YELLOW}HTML file not found. Attempting to resolve base path: {BackgroundColors.CYAN}{base_path}{Style.RESET_ALL}"
            )  # End of verbose output call
            
            base_variations = [  # List of base path variations to try
                base_path,  # Try as directory
                f"./Inputs/{base_path}",  # Try with Inputs prefix as directory
                f"{base_path}.zip",  # Try as zip file
                f"./Inputs/{base_path}.zip",  # Try with Inputs prefix as zip file
            ]  # End of base variations list
            
            for test_path in base_variations:  # Iterate through base path variations
                if verify_filepath_exists(test_path):  # If base path variation exists
                    if os.path.isdir(test_path):  # Verify if it's a directory
                        resolved_html_path = os.path.join(test_path, html_filename)  # Reconstruct full HTML file path
                        verbose_output(f"{BackgroundColors.GREEN}Resolved base directory: {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}")  # Inform about directory resolution
                        verbose_output(f"{BackgroundColors.GREEN}Using HTML file: {BackgroundColors.CYAN}{resolved_html_path}{Style.RESET_ALL}")  # Inform about HTML file path
                        return resolved_html_path  # Return reconstructed HTML path
                    else:  # It's a zip file
                        verbose_output(f"{BackgroundColors.GREEN}Resolved base path to zip file: {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}")  # Inform about zip resolution
                        return test_path  # Return zip file path
    
    return local_html_path  # Return original path even if not found


def scrape_product(url, local_html_path=None):
    """
    Scrapes product information from a URL by detecting the platform and using the appropriate scraper.
    Supports both online scraping (via browser) and offline scraping (from local HTML file).
    
    :param url: The product URL to scrape
    :param local_html_path: Optional path to a local HTML file for offline scraping
    :return: Tuple of (product_data dict, description_file path, product_directory string, html_path_for_assets string, zip_path string, extracted_dir string) or (None, None, None, None, None, None) on failure
    """
    
    platform = detect_platform(url)  # Detect the e-commerce platform
    
    if not platform:  # If platform detection failed
        print(f"{BackgroundColors.RED}Unsupported platform. Skipping URL: {url}{Style.RESET_ALL}")
        return None, None, None, None, None, None
    
    extracted_dir = None  # Directory where zip is extracted
    zip_path = None  # Path to the zip file for cleanup
    html_path = local_html_path  # Default to local_html_path
    
    if local_html_path and local_html_path.lower().endswith('.zip'):  # If a local HTML path is provided and it is a zip file, extract it
        zip_path = local_html_path  # Store the zip path for later cleanup
        zip_dir = os.path.dirname(zip_path)  # Get the directory of the zip file
        zip_name = os.path.basename(zip_path)  # Get the name of the zip file
        extract_name = zip_name.rsplit('.', 1)[0]  # Remove .zip extension
        extracted_dir = os.path.join(zip_dir, extract_name)  # Directory to extract the zip contents into
        
        try:  # Try to extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:  # Open the zip file for reading
                zip_ref.extractall(extracted_dir)  # Extract the contents to the extracted_dir
            html_path = os.path.join(extracted_dir, 'index.html')  # Assume the main HTML file is named index.html in the extracted directory
            if not os.path.exists(html_path):  # Verify if the expected HTML file exists after extraction
                print(f"{BackgroundColors.RED}Error: index.html not found in extracted directory {extracted_dir}{Style.RESET_ALL}")
                shutil.rmtree(extracted_dir)  # Clean up the extracted directory if the expected HTML file is not found
                return None, None, None, None, None, None  # Return None values if extraction failed or expected file not found
        except Exception as e:  # If an error occurs during extraction
            print(f"{BackgroundColors.RED}Error extracting zip {zip_path}: {e}{Style.RESET_ALL}")
            if os.path.exists(extracted_dir):  # If the extracted directory was created before the error, attempt to clean it up
                shutil.rmtree(extracted_dir)  # Clean up the extracted directory if extraction failed
            return None, None, None, None, None, None  # Return None values if extraction failed
    
    scraper_classes = {  # Mapping of platform identifiers to scraper classes
        # "aliexpress": AliExpress,
        "mercadolivre": MercadoLivre,
        "shein": Shein,
        "shopee": Shopee,
    }
    
    scraper_class = scraper_classes.get(platform)  # Get the appropriate scraper class
    
    if not scraper_class:  # If scraper class not found
        print(f"{BackgroundColors.RED}Scraper not implemented for platform: {platform}{Style.RESET_ALL}")
        return None, None, None, None, None, None  # Return None values
    
    platform_prefix = PLATFORM_PREFIXES.get(platform, "")  # Get the platform prefix for output directory naming
    
    try:  # Try to scrape the product
        scraper = scraper_class(url, local_html_path=html_path, prefix=platform_prefix)  # Create scraper instance with optional local HTML path and platform prefix
        product_data = scraper.scrape()  # Scrape the product
        
        if not product_data:  # If scraping failed
            if extracted_dir and os.path.exists(extracted_dir):  # If extraction occurred and directory exists
                shutil.rmtree(extracted_dir)  # Remove the extracted directory
            if zip_path and os.path.exists(zip_path):  # If zip file exists
                os.remove(zip_path)  # Remove the original zip file
            return None, None, None, None, None, None  # Return None values
        
        product_name = product_data.get("name", "Unknown Product")  # Get product name
        product_name_safe = sanitize_filename(product_name)  # Sanitize filename
        product_directory = f"{platform_prefix}{PLATFORM_PREFIX_SEPARATOR}{product_name_safe}" if platform_prefix else product_name_safe  # Construct directory name with platform prefix
        description_file = f"./Outputs/{product_directory}/{product_name_safe}_description.txt"  # Construct full path to description file using prefixed directory
        
        if not verify_filepath_exists(description_file):  # If description file not found
            print(f"{BackgroundColors.RED}Description file not found: {description_file}{Style.RESET_ALL}")
            if extracted_dir and os.path.exists(extracted_dir):  # If extraction occurred and directory exists
                shutil.rmtree(extracted_dir)  # Remove the extracted directory
            if zip_path and os.path.exists(zip_path):  # If zip file exists
                os.remove(zip_path)  # Remove the original zip file
            return None, None, None, None, None, None  # Return None values
        
        return product_data, description_file, product_directory, html_path, zip_path, extracted_dir
        
    except Exception as e:  # If an error occurs during scraping
        print(f"{BackgroundColors.RED}Error during scraping: {e}{Style.RESET_ALL}")  # Print error message
        if extracted_dir and os.path.exists(extracted_dir):  # If extraction occurred and directory exists
            try:  # Try to clean up
                shutil.rmtree(extracted_dir)  # Remove the extracted directory
            except Exception:  # If cleanup fails
                pass  # Ignore cleanup errors
        if zip_path and os.path.exists(zip_path):  # If zip file exists
            try:  # Try to clean up
                os.remove(zip_path)  # Remove the original zip file
            except Exception:  # If cleanup fails
                pass  # Ignore cleanup errors
        return None, None, None, None, None, None  # Return None values


def validate_product_information(product_data, product_name_safe, description_file):
    """
    Validates the product information to determine if it is likely to be a real product description or a placeholder/invalid entry.

    :param product_data: The dictionary containing the scraped product data (used to verify for missing fields or values)
    :param product_name_safe: The sanitized product name (used to verify for "Unknown Product" placeholders)
    :param description_file: The path to the description file (used to verify for placeholder file paths)
    :return: Tuple of (is_valid boolean, list of reasons for invalidity)
    """

    reasons = []  # List to store reasons why the product information might be invalid

    if not product_data:  # Verify if product data is None or empty
        reasons.append(f"{BackgroundColors.YELLOW}Product data is missing or empty{Style.RESET_ALL}")
        
    if product_name_safe == "Unknown Product":  # Verify if the product name is the default placeholder
        reasons.append(f"{BackgroundColors.YELLOW}Product name is a placeholder (Unknown Product){Style.RESET_ALL}") 
        
    if "name" not in product_data or not product_data["name"].strip():  # Verify if name is missing or empty
        reasons.append(f"{BackgroundColors.YELLOW}Product name is missing or empty{Style.RESET_ALL}")
        
    if "current_price_integer" not in product_data or not str(product_data["current_price_integer"]).strip() or product_data["current_price_integer"] == '0':  # Verify if price is missing, empty, or zero
        reasons.append(f"{BackgroundColors.YELLOW}Product price is missing, empty, or zero{Style.RESET_ALL}")
        
    if "discount_percentage" not in product_data or not str(product_data["discount_percentage"]).strip():  # Verify if discount is missing or empty
        reasons.append(f"{BackgroundColors.YELLOW}Product discount is missing or empty{Style.RESET_ALL}")
    
    if "description" not in product_data or not product_data["description"].strip():  # Verify if description is missing or empty
        reasons.append(f"{BackgroundColors.YELLOW}Product description is missing or empty{Style.RESET_ALL}")
        
    return (len(reasons) == 0), reasons  # Return True if valid (no reasons), otherwise False and the list of reasons


def delete_local_html_file(local_html_path):
    """
    Deletes the local HTML file if it exists after successful scraping.

    :param local_html_path: Path to the local HTML file to delete
    :return: True if deletion successful, False otherwise
    """

    if not local_html_path:  # If no local HTML path provided
        return False  # Return False as nothing to delete
    
    if not verify_filepath_exists(local_html_path):  # If file doesn't exist
        return False  # Return False as file doesn't exist
    
    try:  # Try to delete the file
        os.remove(local_html_path)  # Remove the local HTML file
        verbose_output(f"{BackgroundColors.GREEN}Deleted local HTML file: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}")  # Output verbose deletion message
        return True  # Return True on successful deletion
    except Exception as e:  # If deletion fails
        print(f"{BackgroundColors.RED}Error deleting local HTML file {BackgroundColors.CYAN}{local_html_path}{BackgroundColors.RED}: {BackgroundColors.YELLOW}{e}{Style.RESET_ALL}")  # Output error message
        return False  # Return False on failure


def validate_and_fix_output_file(file_path):
    """
    Validates and fixes common formatting issues in output files.
    
    This function removes:
    - Multiple consecutive empty lines (reduces to single empty line)
    - Multiple consecutive spaces (reduces to single space)
    - Multiple consecutive asterisks (reduces to single asterisk)
    
    :param file_path: Path to the file to validate and fix
    :return: True if validation and fix were successful, False otherwise
    """
    
    verbose_output(
        f"{BackgroundColors.GREEN}Validating and fixing output file: {BackgroundColors.CYAN}{file_path}{Style.RESET_ALL}"
    )  # Output the verbose message
    
    if not verify_filepath_exists(file_path):  # If the file doesn't exist
        print(f"{BackgroundColors.RED}File not found for validation: {file_path}{Style.RESET_ALL}")
        return False  # Return False if file doesn't exist
    
    try:  # Try to read and fix the file
        with open(file_path, "r", encoding="utf-8") as f:  # Open the file for reading
            content = f.read()  # Read the entire content
        
        original_content = content  # Store original content for comparison
        
        content = re.sub(r'\n\n\n+', '\n\n', content)  # Replace 3 or more newlines with exactly 2
        
        content = re.sub(r' {2,}', ' ', content)  # Replace 2 or more spaces with single space
        
        content = re.sub(r'\*{2,}', '*', content)  # Replace 2 or more asterisks with single asterisk
        
        if content != original_content:  # If any fixes were applied
            with open(file_path, "w", encoding="utf-8") as f:  # Open the file for writing
                f.write(content)  # Write the fixed content back to the file
            verbose_output(
                f"{BackgroundColors.GREEN}Fixed formatting issues in: {BackgroundColors.CYAN}{file_path}{Style.RESET_ALL}"
            )
        else:  # If no fixes were needed
            verbose_output(
                f"{BackgroundColors.GREEN}No formatting issues found in: {BackgroundColors.CYAN}{file_path}{Style.RESET_ALL}"
            )
        
        return True  # Return success
        
    except Exception as e:  # If an error occurs during validation
        print(f"{BackgroundColors.RED}Error during file validation: {e}{Style.RESET_ALL}")
        return False  # Return failure


def generate_marketing_text(product_description, description_file, product_data=None):
    """
    Generates marketing text from product description using Gemini AI.
    Supports multiple API keys with automatic failover on rate limit errors.
    
    :param product_description: The raw product description text
    :param description_file: Path to the description file (used to determine output directory)
    :param product_data: Optional dictionary containing product information (e.g., is_international)
    :return: True if successful, False otherwise
    """
    
    api_keys_raw = os.getenv(ENV_VARIABLES["GEMINI"], "")  # Get Gemini API key(s)
    api_keys = [key.strip() for key in api_keys_raw.split(",") if key.strip()]  # Split and clean keys
    
    if not api_keys:  # If no API keys are configured
        print(f"{BackgroundColors.RED}Error: No Gemini API keys configured in .env file.{Style.RESET_ALL}")
        return False  # Return failure
    
    is_international = product_data.get("is_international", False) if product_data else False  # Verify if product is international
    internacional_instruction = ""  # Initialize international instruction as empty
    if is_international:  # If the product is international, we need to add a specific instruction to the prompt
        internacional_instruction = "\n\n**IMPORTANTE**: Este produto é INTERNACIONAL. Você DEVE adicionar '[PRODUTO INTERNACIONAL]: ' antes do nome do produto no início do texto formatado."
    
    old_price_int = str(product_data.get("old_price_integer", "")).strip() if product_data else ""
    old_price_dec = str(product_data.get("old_price_decimal", "")).strip() if product_data else ""
    discount = str(product_data.get("discount_percentage", "")).strip() if product_data else ""
    
    no_discount_instruction = ""
    if (old_price_int in ["N/A", ""] or old_price_dec in ["N/A", ""]) and discount in ["N/A", ""]:
        no_discount_instruction = "\n\n**IMPORTANTE**: Este produto NÃO possui preço antigo ou desconto disponível. Você deve REMOVER as linhas de preço antigo (DE R$...) e desconto (🎟️...) do texto formatado. Mostre APENAS o preço atual."
    
    prompt = GEMINI_MARKETING_PROMPT_TEMPLATE.format(product_description=product_description) + internacional_instruction + no_discount_instruction  # Format template with all instructions
    
    last_error = None  # Store the last error for reporting
    for key_index, api_key in enumerate(api_keys, 1):  # Iterate through API keys
        try:  # Try to generate marketing text with current key
            verbose_output(
                true_string=f"{BackgroundColors.GREEN}Attempting to use Gemini API key {key_index} of {len(api_keys)}...{Style.RESET_ALL}"
            )  # Output verbose message
            
            gemini = Gemini(api_key)  # Create Gemini instance with current key
            formatted_output = gemini.generate_content(prompt)  # Generate formatted marketing text
            
            if formatted_output:  # If generation successful
                description_dir = os.path.dirname(description_file)  # Get directory of description file
                formatted_file = os.path.join(description_dir, f"Template.txt")  # Output file path
                gemini.write_output_to_file(formatted_output, formatted_file)  # Write output to file
                
                gemini.close()  # Close Gemini client
                
                return True  # Return success
            else:  # If generation failed but no exception
                print(f"{BackgroundColors.YELLOW}API key {key_index} returned empty response.{Style.RESET_ALL}")
                gemini.close()  # Close Gemini client
                last_error = "Empty response from API"
                continue  # Try next key
                
        except Exception as e:  # If an error occurs with current key
            error_str = str(e).lower()  # Convert error to lowercase for verify
            
            is_rate_limit = any(keyword in error_str for keyword in [
                "rate", "quota", "limit", "429", "resource_exhausted", 
                "too many requests", "quota exceeded"
            ])  # Verify for rate limit indicators
            
            if is_rate_limit:  # If rate limit error detected
                last_error = e  # Store error
                
                if key_index < len(api_keys):  # If more keys available
                    continue  # Try next key
                else:  # No more keys to try
                    print(f"{BackgroundColors.RED}All API keys exhausted.{Style.RESET_ALL}")
            else:  # Non-rate-limit error
                print(f"{BackgroundColors.RED}Error with API key {key_index}: {e}{Style.RESET_ALL}")
                last_error = e  # Store error
                
                return False  # Return failure
    
    print(f"{BackgroundColors.RED}Failed to generate marketing text after trying all {len(api_keys)} API key(s).{Style.RESET_ALL}")
    if last_error:  # If we have a stored error
        print(f"{BackgroundColors.RED}Last error: {last_error}{Style.RESET_ALL}")
    
    return False  # Return failure


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
        end="\n",
    )  # Output the welcome message
    start_time = datetime.datetime.now()  # Get the start time of the program
    
    if not verify_dot_env_file():  # Verify if the .env file exists
        print(f"{BackgroundColors.RED}Environment setup failed. Exiting...{Style.RESET_ALL}")
        return
    
    load_dotenv(ENV_PATH)  # Load environment variables
    
    if not verify_env_variables():  # Verify if the required environment variables are set
        print(f"{BackgroundColors.RED}Environment variables missing. Exiting...{Style.RESET_ALL}")
        return
    
    create_directory(
        os.path.abspath(INPUT_DIRECTORY), INPUT_DIRECTORY.replace(".", "")
    )  # Create the input directory

    if not ensure_input_file_exists():  # Ensure the input file exists, and if not, create it with instructions
        return  # Exit if unable to ensure input file
    
    create_directory(
        os.path.abspath(OUTPUT_DIRECTORY), OUTPUT_DIRECTORY.replace(".", "")
    )  # Create the output directory
    
    clean_unknown_product_directories(OUTPUT_DIRECTORY)  # Clean up any "Unknown Product" directories from previous runs
    
    successful_scrapes = 0  # Counter for successful operations

    urls_to_process = load_urls_to_process(TEST_URLs, INPUT_FILE)  # Load URLs to process (returns list of tuples)
    
    total_urls = len(urls_to_process)  # Total number of URLs to process

    if total_urls == 0:  # If there are no URLs to process, output a message and skip the processing loop
        print(f"{BackgroundColors.YELLOW}No URLs to process.{Style.RESET_ALL}")
    else:  # If there are URLs to process, proceed with the processing loop
        pbar = tqdm(
            urls_to_process,
            desc=f"{BackgroundColors.GREEN}Processing URLs{Style.RESET_ALL}",
            unit="url",
            ncols=100,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            file=sys.__stdout__,
        )
        for index, (url, local_html_path) in enumerate(pbar, 1):  # Iterate through all URLs with optional local HTML paths
            platform_id = detect_platform(url) or ""  # Detect platform for current URL
            platform_name = PLATFORM_PREFIXES.get(platform_id, platform_id if platform_id else "Unknown")  # Human-friendly platform name
            desc = (
                f"{BackgroundColors.GREEN}Processing {BackgroundColors.CYAN}{index}{BackgroundColors.GREEN}/{BackgroundColors.CYAN}{total_urls}{BackgroundColors.GREEN} - {BackgroundColors.CYAN}{platform_name}{BackgroundColors.GREEN}"
            )  # Build colored description with platform
            pbar.set_description(desc)  # Update the progress bar description

            verify_affiliate_url_format(url)  # Verify affiliate-format URL for supported platforms

            if local_html_path:  # If a local HTML file path is provided
                local_html_path = resolve_local_html_path(local_html_path)  # Resolve path with fallback variations
                verbose_output(f"{BackgroundColors.GREEN}Using local HTML file: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}")  # Inform user about offline mode

            verbose_output(f"{BackgroundColors.CYAN}Step 1{BackgroundColors.GREEN}: Scraping the product information{Style.RESET_ALL}")  # Step 1: Scrape the product information
            scrape_result = scrape_product(url, local_html_path)  # Scrape the product with optional local HTML path
        
            if not scrape_result or len(scrape_result) != 6:  # If scraping failed or returned invalid result
                print(f"{BackgroundColors.RED}Skipping {BackgroundColors.CYAN}{url}{BackgroundColors.RED} due to scraping failure.{Style.RESET_ALL}\n")
                continue  # Move to next URL
            
            product_data, description_file, product_directory, html_path_for_assets, zip_path_to_cleanup, extracted_dir_to_cleanup = scrape_result  # Unpack the scrape result
            
            if product_directory and isinstance(product_directory, str):  # If product directory is valid
                clean_duplicate_images(product_directory)  # Clean up duplicate images in the product directory
                exclude_small_images(product_directory)  # Exclude images smaller than 2KB
            
            if extracted_dir_to_cleanup and os.path.exists(extracted_dir_to_cleanup):  # If extraction occurred and directory exists
                try:  # Try to clean up the extracted directory
                    shutil.rmtree(extracted_dir_to_cleanup)  # Remove the extracted directory
                    verbose_output(f"{BackgroundColors.GREEN}Cleaned up extracted directory: {BackgroundColors.CYAN}{extracted_dir_to_cleanup}{Style.RESET_ALL}")
                except Exception as e:  # If cleanup fails
                    print(f"{BackgroundColors.YELLOW}Warning: Failed to clean up extracted directory: {e}{Style.RESET_ALL}")
            
            if zip_path_to_cleanup and os.path.exists(zip_path_to_cleanup):  # If zip file exists
                try:  # Try to clean up the zip file
                    os.remove(zip_path_to_cleanup)  # Remove the original zip file
                    verbose_output(f"{BackgroundColors.GREEN}Cleaned up zip file: {BackgroundColors.CYAN}{zip_path_to_cleanup}{Style.RESET_ALL}")
                except Exception as e:  # If cleanup fails
                    print(f"{BackgroundColors.YELLOW}Warning: Failed to clean up zip file: {e}{Style.RESET_ALL}")
            
            if not product_data:  # If scraping failed
                print(f"{BackgroundColors.RED}Skipping {BackgroundColors.CYAN}{url}{BackgroundColors.RED} due to scraping failure.{Style.RESET_ALL}\n")
                continue  # Move to next URL
            
            try:  # Read the product description from the file
                with open(str(description_file), "r", encoding="utf-8") as f:  # Open the description file with UTF-8 encoding
                    product_description = f.read()  # Read the product description
            except Exception as e:  # If reading the file fails
                print(f"{BackgroundColors.RED}Error reading description file: {e}{Style.RESET_ALL}")
                continue  # Move to next URL
            
            valid, invalid_reasons = validate_product_information(product_data, product_directory, description_file)  # Validate the product information

            if not valid:  # If the product information is not valid, skip Gemini formatting and output the reasons
                print(
                    f"{BackgroundColors.RED}Skipping Step 2: Gemini formatting due to invalid product information for URL: {BackgroundColors.CYAN}{url}{BackgroundColors.RED}.{Style.RESET_ALL}"
                )
                continue  # Move to next URL

            if local_html_path:  # If a local HTML path was provided
                delete_local_html_file(local_html_path)  # Delete the local HTML file after successful scraping and validation

            verbose_output(f"{BackgroundColors.CYAN}Step 2{BackgroundColors.GREEN}: Formatting with Gemini AI{Style.RESET_ALL}")  # Step 2: Format the product description with Gemini AI
            
            success = generate_marketing_text(product_description, description_file, product_data)  # Generate marketing text with product data
            
            if success:  # If both scraping and formatting succeeded
                description_dir = os.path.dirname(description_file)  # Get directory of description file
                template_file = os.path.join(description_dir, "Template.txt")  # Path to the generated template file
                validate_and_fix_output_file(template_file)  # Validate and fix formatting issues in the output file
                
                successful_scrapes += 1  # Increment successful scrapes counter
            
            if index < total_urls:  # Add delay between requests to avoid rate limiting, but not after the last URL
                time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print(f"{BackgroundColors.GREEN}Successfully processed: {BackgroundColors.CYAN}{successful_scrapes}/{total_urls}{BackgroundColors.GREEN} URLs{Style.RESET_ALL}\n")  # Output the number of successful operations

    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the start and finish times
    print(
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
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
