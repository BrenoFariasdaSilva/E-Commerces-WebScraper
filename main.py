"""
================================================================================
E-Commerces WebScraper - main.py
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
import json  # For JSON history file handling
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import re # For regular expressions in text processing
import shutil  # For removing directories
import subprocess  # For running system commands
import sys  # For system-specific parameters and functions
import time  # For adding delays between requests
import zipfile  # For handling zip files
from AliExpress import AliExpress  # Import the AliExpress class
from Amazon import Amazon  # Import the Amazon class
from colorama import Style  # For coloring the terminal
from dotenv import load_dotenv  # For loading environment variables
from Gemini import Gemini, QuotaExceededError  # Import the Gemini class and quota exhaustion signal.
from Logger import Logger  # For logging output to both terminal and file
from MercadoLivre import MercadoLivre  # Import the MercadoLivre class
from pathlib import Path  # For handling file paths
from PIL import Image  # For image processing
from Shein import Shein  # Import the Shein class
from Shopee import Shopee  # Import the Shopee class
from tkinter import Tk, messagebox  # For showing GUI warnings
from tqdm import tqdm  # Progress bar for URL processing
from typing import Dict, List, Optional, Set, Tuple  # For type-annotated containers used by final verification functions
from urllib.parse import urlparse  # For parsing URL hostnames


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
    "Amazon": "amazon",
    "MercadoLivre": "mercadolivre",
    "Shein": "shein",
    "Shopee": "shopee",
}

PLATFORM_PREFIX_SEPARATOR = " - "  # Separator between platform prefix and product name in directory structure

# File Path Constants:
INPUT_DIRECTORY = "./Inputs/"  # The path to the input directory
INPUT_FILE = f"{INPUT_DIRECTORY}urls.txt"  # The path to the input file
OUTPUT_DIRECTORY = "./Outputs/"  # The path to the output directory
OUTPUT_FILE = f"{OUTPUT_DIRECTORY}output.txt"  # The path to the output file
CLEAR_INPUT_FILE = True  # When True, remove successfully scraped product lines from the input file
DELETE_LOCAL_HTML_FILE = True if CLEAR_INPUT_FILE else False  # When True, delete the local HTML file after processing if the line is cleared from input file

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
OUTPUT_DIRECTORY_RETRY_ATTEMPTS = 1  # Number of retries when the final product output directory is missing

# Gemini AI Constants:
GEMINI_MARKETING_PROMPT_TEMPLATE = """Você é um especialista em marketing de e-commerce. Sua tarefa é transformar as informações do produto abaixo em um texto de marketing persuasivo, chamativo, direto e formatado.

INFORMAÇÕES DO PRODUTO:
{product_description}

FORMATO OBRIGATÓRIO (siga EXATAMENTE este formato):
*{{{{NOME DO PRODUTO}}}} – {{{{DIFERENCIAL CURTO}}}}*

💰 DE *R${{{{PREÇO_ANTIGO}}}}* POR APENAS *R${{{{PREÇO_ATUAL}}}}*
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
5. A linha de preço (💰) é obrigatória e deve sempre aparecer
6. Quando não houver desconto, OMITA apenas a linha de desconto (🎟️)
7. Quando não houver preço antigo, use o mesmo valor do preço atual como preço antigo
8. Quando PREÇO_ANTIGO e PREÇO_ATUAL forem iguais, escreva a linha de preço como: 💰 POR APENAS *R$<PREÇO_ATUAL>* (sem usar "DE")
9. Inclua o link real do produto
10. Crie 2-3 características principais marcantes
11. Sugira onde/como usar o produto
12. Se aplicável, sugira como presente ou ocasião especial
13. Para o desconto, quando existir, nunca usar o termo "off", prefira algo como "20% de Desconto!"
14. O texto final NÃO pode ultrapassar 1000 caracteres (incluindo espaços e emojis)
15. Seja direto, evite parágrafos longos e evite textos explicativos extensos — consumidores não gostam de ler textos longos
16. Priorize frases curtas, objetivas e de alto impacto
17. ESPAÇAMENTO É OBRIGATÓRIO: deixe exatamente 1 linha em branco entre blocos principais (título, preço/desconto, frase de impacto, lista de benefícios, bloco final da loja/link)
18. Após o título, SEMPRE inserir 1 linha em branco antes da linha de preço
19. Após o bloco de preço/desconto, SEMPRE inserir 1 linha em branco antes da frase de impacto
20. Após a frase de impacto, SEMPRE inserir 1 linha em branco antes da primeira linha com ✨
21. Após a última linha com ✨, SEMPRE inserir 1 linha em branco antes de "🛒 Encontre ..."
22. NUNCA comprimir o texto em um bloco único contínuo
23. NUNCA remover as linhas em branco obrigatórias mesmo quando o texto estiver curto

Gere APENAS o texto formatado, sem explicações adicionais."""  # Template for Gemini AI marketing text generation

GEMINI_LAST_KEY_INDEX = 0  # Index to keep track of the last used key in the Gemini prompt template for dynamic replacement
GEMINI_ALL_KEYS_EXHAUSTED_WAIT_SECONDS = 60  # Seconds to wait before restarting key rotation when all keys are exhausted.
GEMINI_MAX_ALL_KEYS_EXHAUSTED_CYCLES = 3  # Maximum all-keys-exhausted cycles per URL before failing the request.

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


def is_ffmpeg_installed():
    """
    Checks if FFmpeg is installed by running 'ffmpeg -version'.

    :return: bool - True if FFmpeg is installed, False otherwise.
    """

    try:  # Try to execute FFmpeg
        subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )  # Run the command
        return True  # FFmpeg is installed
    except (subprocess.CalledProcessError, FileNotFoundError):  # If an error occurs
        return False  # FFmpeg is not installed


def install_ffmpeg_windows():
    """
    Installs FFmpeg on Windows using Chocolatey. If Chocolatey is not installed, it installs it first.

    :return: None
    """

    verbose_output(f"{BackgroundColors.GREEN}Checking for Chocolatey...{Style.RESET_ALL}")  # Output the verbose message

    choco_installed = (
        subprocess.run(["choco", "--version"], capture_output=True, text=True).returncode == 0
    )  # Check if Chocolatey is installed

    if not choco_installed:  # If Chocolatey is not installed
        verbose_output(f"{BackgroundColors.YELLOW}Chocolatey not found. Installing Chocolatey...{Style.RESET_ALL}")

        choco_install_cmd = (
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            '"Set-ExecutionPolicy Bypass -Scope Process -Force; '
            "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
            "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))\""
        )

        subprocess.run(choco_install_cmd, shell=True, check=True)  # Install Chocolatey

        verbose_output(
            f"{BackgroundColors.GREEN}Chocolatey installed successfully. Restart your terminal if needed.{Style.RESET_ALL}"
        )

    verbose_output(f"{BackgroundColors.GREEN}Installing FFmpeg via Chocolatey...{Style.RESET_ALL}")
    subprocess.run(["choco", "install", "ffmpeg", "-y"], check=True)  # Install FFmpeg using Chocolatey

    verbose_output(
        f"{BackgroundColors.GREEN}FFmpeg installed successfully. Please restart your terminal if necessary.{Style.RESET_ALL}"
    )


def install_ffmpeg_linux():
    """
    Installs FFmpeg on Linux using the package manager.

    :return: None
    """

    verbose_output(
        f"{BackgroundColors.GREEN}Installing FFmpeg on Linux...{Style.RESET_ALL}"
    )  # Output the verbose message

    try:  # Try installing FFmpeg
        subprocess.run(["sudo", "apt", "update"], check=True)  # Update package list
        subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)  # Install FFmpeg
        verbose_output(
            f"{BackgroundColors.GREEN}FFmpeg installed successfully.{Style.RESET_ALL}"
        )  # Output the verbose message
    except subprocess.CalledProcessError:  # If an error occurs
        print("Failed to install FFmpeg. Please install it manually using your package manager.")  # Inform the user


def install_ffmpeg_mac():
    """
    Installs FFmpeg on macOS using Homebrew.

    :return: None
    """

    verbose_output(
        f"{BackgroundColors.GREEN}Installing FFmpeg on macOS...{Style.RESET_ALL}"
    )  # Output the verbose message

    try:  # Try installing FFmpeg
        subprocess.run(["brew", "install", "ffmpeg"], check=True)  # Run the installation command
        print("FFmpeg installed successfully.")  # Inform the user
    except subprocess.CalledProcessError:  # If an error occurs
        print(
            "Homebrew not found or installation failed. Please install FFmpeg manually using 'brew install ffmpeg'."
        )  # Inform the user


def ensure_ffmpef_is_installed():
    """
    Verifies if FFmpeg is installed and installs it if missing.

    :return: None
    """

    INSTALL_COMMANDS = {  # Installation commands for different platforms
        "Windows": install_ffmpeg_windows,  # Windows
        "Linux": install_ffmpeg_linux,  # Linux
        "Darwin": install_ffmpeg_mac,  # macOS
    }

    if is_ffmpeg_installed():  # If FFmpeg is already installed
        verbose_output(f"{BackgroundColors.GREEN}FFmpeg is installed.{Style.RESET_ALL}")  # Output the verbose message
    else:  # If FFmpeg is not installed
        verbose_output(
            f"{BackgroundColors.RED}FFmpeg is not installed. Installing FFmpeg...{Style.RESET_ALL}"
        )  # Output the verbose message
        if platform.system() in INSTALL_COMMANDS:  # If the platform is supported
            INSTALL_COMMANDS[platform.system()]()  # Call the corresponding installation function
        else:  # If the platform is not supported
            print(
                f"Installation for {platform.system()} is not implemented. Please install FFmpeg manually."
            )  # Inform the user


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


def clean_duplicate_images(product_directory, base_output_dir=OUTPUT_DIRECTORY):
    """
    Cleans up duplicate images in the product directory by normalizing all images to the smallest size,
    computing MD5 hashes of the resized versions, and removing lower-resolution duplicates while keeping
    the highest-resolution version of each unique image.

    This approach detects duplicates that may have different resolutions but represent the same content,
    such as thumbnails and full-size images.

    :param product_directory: Directory name (may include platform prefix) for the product
    :param base_output_dir: Base output directory path (defaults to OUTPUT_DIRECTORY constant)
    :return: None
    """
    
    product_dir = os.path.join(base_output_dir, product_directory)  # Path to the product directory using provided base directory
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


def exclude_small_images(product_directory, base_output_dir=OUTPUT_DIRECTORY, min_size_bytes=2048):
    """
    Excludes (deletes) image files smaller than the specified minimum size in bytes.
    This helps remove very small or corrupted images that are likely thumbnails or placeholders.

    :param product_directory: Directory name (may include platform prefix) for the product
    :param base_output_dir: Base output directory path (defaults to OUTPUT_DIRECTORY constant)
    :param min_size_bytes: Minimum file size in bytes (default 2048 = 2KB)
    :return: None
    """
    
    product_dir = os.path.join(base_output_dir, product_directory)  # Path to the product directory using provided base directory
    
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


def get_next_run_index(base_output_dir, today_str):
    """
    Determines the next run index for the current day by scanning existing timestamped directories.
    
    :param base_output_dir: The base output directory to scan for existing runs
    :param today_str: The current date string in YYYY-MM-DD format
    :return: The next incremental run index (integer starting from 1)
    """
    
    if not os.path.exists(base_output_dir):  # Verify if base output directory exists
        return 1  # Return 1 as first run index if directory doesn't exist yet
    
    max_index = 0  # Initialize maximum index counter to zero
    pattern = re.compile(r'^(\d+)\. \d{4}-\d{2}-\d{2} - .+$')  # Regex: "index. YYYY-MM-DD - <time>"

    for item in os.listdir(base_output_dir):  # Iterate through all items in base output directory
        item_path = os.path.join(base_output_dir, item)  # Construct full path to item
        if os.path.isdir(item_path):  # Verify if item is a directory
            match = pattern.match(item)  # Try to match directory name against pattern
            if match:  # If directory name matches the expected format
                index = int(match.group(1))  # Extract run index from first capture group
                max_index = max(max_index, index)  # Update max_index if current index is higher

    return max_index + 1  # Return next incremental index across all runs (max found + 1)


def create_timestamped_output_directory(base_output_dir):
    """
    Creates a timestamped output directory with incremental daily run index.
    
    :param base_output_dir: The base output directory path (e.g., "./Outputs/")
    :return: Path to the created timestamped subdirectory
    """
    
    now = datetime.datetime.now()  # Get current date and time
    today_str = now.strftime("%Y-%m-%d")  # Format date as YYYY-MM-DD string
    time_str = now.strftime("%Hh%Mm%Ss")  # Format time as HHh-MMm-SSd string
    
    run_index = get_next_run_index(base_output_dir, today_str)  # Get next run index for today
    
    dir_name = f"{run_index}. {today_str} - {time_str}"  # Construct directory name with index, date, and time
    timestamped_dir = os.path.join(base_output_dir, dir_name)  # Construct full path to timestamped directory
    
    os.makedirs(timestamped_dir, exist_ok=True)  # Create timestamped directory including any missing parent directories
    
    return timestamped_dir  # Return path to created timestamped directory


def detect_platform(url):
    """
    Detects the e-commerce platform from a given URL by verifying domain names.
    
    :param url: The product URL to analyze
    :return: Platform name (e.g., 'mercadolivre', 'shein', 'shopee') or None if not recognized
    """
    
    url_lower = url.lower()  # Convert URL to lowercase for case-insensitive matching

    try:  # Try to parse the URL to obtain hostname for shortened-domain detection
        parsed = urlparse(url)  # Parse the URL into components to extract hostname and path
        hostname = (parsed.hostname or "").lower()  # Extract hostname and normalize to lowercase for comparisons
    except Exception:  # On any parsing error, degrade gracefully to empty hostname
        hostname = ""  # Use empty hostname when parsing fails to avoid exceptions

    if hostname.endswith("amzn.to"):  # Map amzn.to shortened domain explicitly to amazon platform id
        verbose_output(f"{BackgroundColors.GREEN}Detected platform: {BackgroundColors.CYAN}Amazon{Style.RESET_ALL}")  # Output verbose message for shortened Amazon domain detection
        return "amazon"  # Return the canonical platform id for Amazon when shortened domain matched

    if hostname.endswith("meli.la"):  # Map meli.la shortened domain explicitly to mercadolivre platform id
        verbose_output(f"{BackgroundColors.GREEN}Detected platform: {BackgroundColors.CYAN}MercadoLivre{Style.RESET_ALL}")  # Output verbose message for shortened MercadoLivre domain detection
        return "mercadolivre"  # Return the canonical platform id for MercadoLivre when shortened domain matched

    if hostname.endswith("br.shp.ee"):  # Verify if hostname matches Shopee short-link domain used for video pages
        print(f"{BackgroundColors.RED}Error: Shopee short-link {url} appears to be a video page, not a product page. Skipping.{Style.RESET_ALL}")  # Report unsupported Shopee short-link and skip processing
        return None  # Return None to indicate this URL should be skipped and not processed

    for platform_name, platform_id in PLATFORMS_MAP.items():  # Iterate through supported platforms to preserve existing substring detection logic
        if platform_id in url_lower:  # Verify if platform identifier substring exists in the URL (original behavior)
            verbose_output(
                f"{BackgroundColors.GREEN}Detected platform: {BackgroundColors.CYAN}{platform_name}{Style.RESET_ALL}"
            )  # Output verbose message when platform detected by substring
            return platform_id  # Return the platform identifier when detected by substring

    print(f"{BackgroundColors.YELLOW}Warning: Could not detect platform from URL: {url}{Style.RESET_ALL}")  # Warn when platform cannot be detected from the URL
    return None  # Return None if platform not recognized


def verify_affiliate_url_format(url: str) -> bool:
    """
    Verify if a URL uses the supported short affiliate redirect format.

    :param url: The product URL to verify
    :return: True if URL is acceptable or matches affiliate pattern, False if it fails regex validation
    """
    
    platform_id = detect_platform(url)  # Detect the platform identifier from the URL
    if platform_id is None:  # If platform not recognized, skip affiliate validation
        return True  # Accept as no affiliate-format validation required

    platform_modules = {  # Map platform ids to the imported class objects for lookup
        "aliexpress": AliExpress,  # AliExpress handler class reference
        "amazon": Amazon,  # Amazon handler class reference
        "mercadolivre": MercadoLivre,  # MercadoLivre handler class reference
        "shein": Shein,  # Shein handler class reference (class, not module)
        "shopee": Shopee,  # Shopee handler class reference
    }  # End of mapping

    module_or_class = platform_modules.get(platform_id)  # Get the configured module/class for the detected platform
    if module_or_class is None:  # If platform not supported in the mapping
        return True  # Accept as there's nothing to validate for unknown platform

    pattern = getattr(module_or_class, "AFFILIATE_URL_PATTERN", None)  # Try to read AFFILIATE_URL_PATTERN from the class first
    if not pattern:  # If attribute not found on the class, attempt to retrieve it from the originating module object
        try:  # Try to locate the module object for the class to obtain module-level constants
            module_name = getattr(module_or_class, "__module__", None)  # Module name where the class is defined
            if isinstance(module_name, str):  # Ensure module_name is a valid string before using it as dict key
                    module_obj = sys.modules.get(module_name)  # Obtain the actual module object from sys.modules
                    if module_obj is not None:  # If module object was found in sys.modules
                        pattern = getattr(module_obj, "AFFILIATE_URL_PATTERN", None)  # Read AFFILIATE_URL_PATTERN from the module object
        except Exception:  # On any exception while resolving module, fallback to no pattern
            pattern = None  # Ensure pattern remains None on failure

    if not pattern:  # If after lookup no pattern is available to validate against
        return True  # Accept as there's no affiliate pattern to enforce for this platform

    full_pattern = rf"^(?:{pattern})(?:\?.*)?$"  # Build a full-match regex allowing optional querystring parameters

    matched = False  # Initialize matched to avoid possibly unbound variable error

    try:  # Attempt to compile and run a full-match using re.fullmatch for strict validation
        matched = re.fullmatch(full_pattern, url) is not None  # Boolean result of full-match validation
    except re.error:  # If the affiliate regex itself is invalid, inform the user and fail validation
        msg = f"{BackgroundColors.YELLOW}Warning: invalid affiliate regex for {platform_id}.{Style.RESET_ALL}"  # Construct invalid-regex warning
        try:  # Try to write the warning directly to the original stdout stream for visibility
            original_stdout = getattr(sys, "__stdout__", None)  # Get the original stdout if available
            if original_stdout is not None and hasattr(original_stdout, "write"):  # If original stdout supports write
                    try:  # Try to write and flush to original stdout
                        original_stdout.write(msg + "\n")  # Write message
                        if hasattr(original_stdout, "flush"):  # If flush exists on original stdout
                            original_stdout.flush()  # Flush to ensure immediate display
                    except Exception:  # If write/flush fails, fallback to print
                        print(msg)  # Print fallback
            else:  # If original stdout not available, fallback to print
                    print(msg)  # Print fallback
        except Exception:  # Catch-all fallback if attribute access fails
            print(msg)  # Print fallback
        return False  # Invalid regex should fail validation safely

    if not matched:  # If the URL does not strictly match the affiliate pattern
        clear_msg = f"{BackgroundColors.YELLOW}Warning: URL is not in the expected affiliate format for {platform_id}: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"  # Clear terminal and show warning message
        try:  # Try to write the clear warning to the original stdout for visibility above logger redirection
            original_stdout = getattr(sys, "__stdout__", None)  # Fetch the original stdout if present
            if original_stdout is not None and hasattr(original_stdout, "write"):  # If original stdout supports write
                    try:  # Attempt to write and flush the message
                        original_stdout.write(clear_msg + "\n")  # Write the clear message to original stdout
                        if hasattr(original_stdout, "flush"):  # If flush exists on original stdout
                            original_stdout.flush()  # Flush to ensure immediate output
                    except Exception:  # If write/flush fails, fallback to print
                        print(clear_msg)  # Print fallback
            else:  # If original stdout not accessible, fallback to print
                    print(clear_msg)  # Print fallback
        except Exception:  # Catch-all in case attribute access raises
            print(clear_msg)  # Print fallback

    return matched  # Return True only when the URL strictly matches the affiliate format


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
        if os.path.isdir(local_html_path):  # Check if it's a directory
            index_html_path = os.path.join(local_html_path, "index.html")  # Construct path to index.html inside directory
            if verify_filepath_exists(index_html_path):  # If index.html exists inside directory
                verbose_output(f"{BackgroundColors.GREEN}Resolved local HTML path (directory): {BackgroundColors.CYAN}{local_html_path}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{index_html_path}{Style.RESET_ALL}")  # Confirm resolution
                return index_html_path  # Return path to index.html inside directory
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
                if os.path.isdir(test_path):  # Check if the resolved path is a directory
                    index_html_path = os.path.join(test_path, "index.html")  # Construct path to index.html inside directory
                    if verify_filepath_exists(index_html_path):  # If index.html exists inside directory
                        verbose_output(f"{BackgroundColors.GREEN}Resolved local HTML path (directory): {BackgroundColors.CYAN}{local_html_path}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{index_html_path}{Style.RESET_ALL}")  # Inform about resolution
                        return index_html_path  # Return path to index.html inside directory
                verbose_output(  # Output resolution message
                    f"{BackgroundColors.GREEN}Resolved local HTML path: {BackgroundColors.CYAN}{local_html_path}{BackgroundColors.GREEN} -> {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}"
                )  # End of verbose output call
                verbose_output(f"{BackgroundColors.GREEN}Resolved path variation: {BackgroundColors.CYAN}{test_path}{Style.RESET_ALL}")  # Inform user about resolution
                return test_path  # Return resolved path
    
    if local_html_path.lower().endswith(".html"):  # Verify if path ends with .html extension
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


def copy_original_input_to_output(input_source, product_directory, base_output_dir=OUTPUT_DIRECTORY):
    """
    Copies the original input file or directory used for scraping into the product output directory.

    :param input_source: Path to the original input file, zip, or directory used for scraping
    :param product_directory: Relative product directory name under the base output directory
    :param base_output_dir: Base output directory where product directories are created
    :return: True if a copy was attempted/succeeded, False otherwise
    """

    if not input_source:  # If no input source provided
        return False  # Nothing to copy

    product_dir_full = os.path.join(base_output_dir, product_directory)  # Full path to the product output directory

    try:  # Try to copy the input source into the product output folder
        if not os.path.exists(product_dir_full):  # If the product output directory does not exist
            os.makedirs(product_dir_full, exist_ok=True)  # Create the product output directory

        if os.path.isfile(input_source):  # If the input source points to a file
            # If the file is an HTML file, prefer copying the originating zip or extracted folder
            if str(input_source).lower().endswith(".html"):  # If the source is an HTML file
                html_dir = os.path.dirname(input_source)  # Directory containing the HTML file
                html_dir_name = os.path.basename(html_dir)  # Basename of the directory containing HTML
                copied_any = False  # Track whether we copied any preferred artifact

                # Candidate zip locations to check for the original archive
                candidate_zips = [
                    f"{html_dir}.zip",  # Same path with .zip appended
                    os.path.join(os.path.dirname(html_dir), f"{html_dir_name}.zip"),  # Parent dir + basename.zip
                    os.path.join(INPUT_DIRECTORY, f"{html_dir_name}.zip"),  # Inputs/{basename}.zip
                ]  # End candidate zips

                # Copy any existing zip candidates into the product folder
                for cz in candidate_zips:  # Iterate candidate zip paths
                    if os.path.exists(cz) and os.path.isfile(cz):  # If candidate zip exists and is a file
                        shutil.copy2(cz, product_dir_full)  # Copy the zip preserving metadata
                        verbose_output(f"{BackgroundColors.GREEN}Copied original zip {BackgroundColors.CYAN}{cz}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{product_dir_full}{Style.RESET_ALL}")  # Verbose copy message
                        copied_any = True  # Mark that we copied something

                # If the html is inside a directory, copy the entire directory as the extracted folder
                if os.path.isdir(html_dir):  # If the HTML's parent is a directory
                    dest_dir = os.path.join(product_dir_full, os.path.basename(html_dir))  # Destination inside product folder
                    if os.path.exists(dest_dir):  # If destination already exists
                        shutil.rmtree(dest_dir)  # Remove it to replace
                    try:  # Attempt to copy the extracted directory
                        shutil.copytree(html_dir, dest_dir)  # Copy directory tree
                        verbose_output(f"{BackgroundColors.GREEN}Copied extracted directory {BackgroundColors.CYAN}{html_dir}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{dest_dir}{Style.RESET_ALL}")  # Verbose copy message
                        copied_any = True  # Mark that we copied something
                    except Exception:  # If copying directory fails, ignore and fallback
                        pass  # Continue to fallback behavior

                if copied_any:  # If we copied zip or extracted dir, do not copy the HTML itself
                    return True  # Indicate success

            # Fallback: copy the file itself when no zip/extracted folder found or not an HTML file
            shutil.copy2(input_source, product_dir_full)  # Copy the file preserving metadata
            verbose_output(f"{BackgroundColors.GREEN}Copied input file {BackgroundColors.CYAN}{input_source}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{product_dir_full}{Style.RESET_ALL}")  # Verbose copy message
            return True  # Indicate success

        if os.path.isdir(input_source):  # If the input source points to a directory
            dest_dir = os.path.join(product_dir_full, os.path.basename(input_source))  # Destination path inside the product folder
            if os.path.exists(dest_dir):  # If the destination already exists
                shutil.rmtree(dest_dir)  # Remove the existing destination to replace it
            shutil.copytree(input_source, dest_dir)  # Copy the whole directory tree
            verbose_output(f"{BackgroundColors.GREEN}Copied input directory {BackgroundColors.CYAN}{input_source}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{dest_dir}{Style.RESET_ALL}")  # Verbose copy message
            return True  # Indicate success

        candidate = os.path.join(INPUT_DIRECTORY, os.path.basename(input_source))  # Candidate path inside INPUT_DIRECTORY
        if os.path.exists(candidate):  # If the candidate exists in Inputs
            if os.path.isfile(candidate):  # If the candidate is a file
                shutil.copy2(candidate, product_dir_full)  # Copy the candidate file
                verbose_output(f"{BackgroundColors.GREEN}Copied candidate input file {BackgroundColors.CYAN}{candidate}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{product_dir_full}{Style.RESET_ALL}")  # Verbose copy message
                return True  # Indicate success
            else:  # Candidate is a directory
                dest_dir = os.path.join(product_dir_full, os.path.basename(candidate))  # Destination path inside the product folder
                if os.path.exists(dest_dir):  # If destination already exists
                    shutil.rmtree(dest_dir)  # Remove existing destination
                shutil.copytree(candidate, dest_dir)  # Copy the directory tree
                verbose_output(f"{BackgroundColors.GREEN}Copied candidate input directory {BackgroundColors.CYAN}{candidate}{BackgroundColors.GREEN} to {BackgroundColors.CYAN}{dest_dir}{Style.RESET_ALL}")  # Verbose copy message
                return True  # Indicate success

    except Exception as e:  # If an error occurs during copy
        print(f"{BackgroundColors.RED}Error copying input {BackgroundColors.CYAN}{input_source}{BackgroundColors.RED} to {BackgroundColors.CYAN}{product_dir_full}{BackgroundColors.RED}: {e}{Style.RESET_ALL}")  # Print error message
        return False  # Indicate failure

    return False  # Default: nothing copied


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


def scrape_product(url, timestamped_output_dir, local_html_path=None):
    """
    Scrapes product information from a URL by detecting the platform and using the appropriate scraper.
    Supports both online scraping (via browser) and offline scraping (from local HTML file).
    
    :param url: The product URL to scrape
    :param timestamped_output_dir: The timestamped output directory for this run
    :param local_html_path: Optional path to a local HTML file for offline scraping
    :return: Tuple of (product_data dict, description_file path, product_directory string, html_path_for_assets string, zip_path string, extracted_dir string) or (None, None, None, None, None, None) on failure
    """
    
    platform = detect_platform(url)  # Detect the e-commerce platform
    
    if not platform:  # If platform detection failed
        print(f"{BackgroundColors.RED}Unsupported platform. Skipping URL: {url}{Style.RESET_ALL}")
        return None, None, None, None, None, None
    
    extracted_dir = None  # Directory where zip is extracted
    zip_path = None  # Path to the zip file for cleanup
    html_path = local_html_path  # Initialize html_path with local_html_path (will be overridden if zip extraction occurs)
    
    if local_html_path and local_html_path.lower().endswith(".zip"):  # If a local HTML path is provided and it is a zip file, extract it
        zip_path = local_html_path  # Store the zip path for later cleanup
        zip_dir = os.path.dirname(zip_path)  # Get the directory of the zip file
        zip_name = os.path.basename(zip_path)  # Get the name of the zip file
        extract_name = zip_name.rsplit('.', 1)[0]  # Remove .zip extension
        extracted_dir = os.path.join(zip_dir, extract_name)  # Directory to extract the zip contents into
        
        try:  # Try to extract the zip file
            with zipfile.ZipFile(zip_path, "r") as zip_ref:  # Open the zip file for reading
                zip_ref.extractall(extracted_dir)  # Extract the contents to the extracted_dir
            html_path = os.path.join(extracted_dir, "index.html")  # Assume the main HTML file is named index.html in the extracted directory
            if not os.path.exists(html_path):  # Verify if the expected HTML file exists after extraction
                print(f"{BackgroundColors.RED}Error: index.html not found in extracted directory {extracted_dir}{Style.RESET_ALL}")
                return None, None, None, None, None, None  # Return None values if extraction failed or expected file not found
        except Exception as e:  # If an error occurs during extraction
            print(f"{BackgroundColors.RED}Error extracting zip {zip_path}: {e}{Style.RESET_ALL}")
            return None, None, None, None, None, None  # Return None values if extraction failed
    
    scraper_classes = {  # Mapping of platform identifiers to scraper classes
        "aliexpress": AliExpress,
        "amazon": Amazon,
        "mercadolivre": MercadoLivre,
        "shein": Shein,
        "shopee": Shopee,
    }
    
    scraper_class = scraper_classes.get(platform)  # Get the appropriate scraper class
    
    if not scraper_class:  # If scraper class not found
        print(f"{BackgroundColors.RED}Scraper not implemented for platform: {platform}{Style.RESET_ALL}")
        return None, None, None, None, None, None  # Return None values
    
    platform_prefix = {v: k for k, v in PLATFORMS_MAP.items()}.get(platform, "")  # Derive reverse mapping from PLATFORMS_MAP and get platform prefix for output directory naming
    
    try:  # Try to scrape the product
        scraper = scraper_class(url, local_html_path=html_path, prefix=platform_prefix, output_directory=timestamped_output_dir)  # Create scraper instance with timestamped output directory
        product_data = scraper.scrape()  # Scrape the product
        
        if not product_data:  # If scraping failed
            return None, None, None, None, None, None  # Return None values
        
        product_name = product_data.get("name", "Unknown Product")  # Get product name
        if isinstance(product_name, str):  # Ensure we operate only on strings
            product_name = product_name.replace("\u00A0", " ")  # Replace NBSP with normal space
            product_name = re.sub(r"\s+", " ", product_name).strip()  # Collapse multiple whitespace to single spaces
        product_name_safe = product_data.get("product_name_safe", "")  # Get canonical directory name from scraper
        product_directory = product_name_safe  # Use canonical directory name directly (already includes platform prefix)
        description_file = f"{timestamped_output_dir}/{product_directory}/{product_name_safe}_description.txt"  # Construct full path to description file using canonical name
        
        if not verify_filepath_exists(description_file):  # If description file not found
            print(f"{BackgroundColors.RED}Description file not found: {description_file}{Style.RESET_ALL}")
            return None, None, None, None, None, None  # Return None values

        input_source = html_path or local_html_path  # Determine the best candidate input source
        copy_original_input_to_output(input_source, product_directory, base_output_dir=timestamped_output_dir)  # Copy original input to output
        
        return product_data, description_file, product_directory, html_path, zip_path, extracted_dir
        
    except Exception as e:  # If an error occurs during scraping
        print(f"{BackgroundColors.RED}Error during scraping: {e}{Style.RESET_ALL}")  # Print error message
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
        
        content = re.sub(r"\n\n\n+", "\n\n", content)  # Replace 3 or more newlines with exactly 2
        
        content = re.sub(r" {2,}", " ", content)  # Replace 2 or more spaces with single space

        content = re.sub(r"\*{2,}", "*", content)  # Replace 2 or more asterisks with single asterisk
        
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


def read_template_content(template_path: Path) -> Optional[str]:
    """
    Read template file content safely.

    :param template_path: Path to the template file to read.
    :return: The file content string or None when read fails.
    """

    try:  # Try to ensure the template file exists before reading
        if not verify_filepath_exists(template_path):  # Verify template file exists at provided path
            return None  # Return None when file does not exist

        with open(template_path, "r", encoding="utf-8") as f:  # Open the template file for reading
            content = f.read()  # Read the entire file content into a string

        return content  # Return the read content on success
    except Exception:  # Handle unexpected exceptions during file I/O
        return None  # Return None when an exception occurs while reading


def detect_product_name(content: str) -> Optional[str]:
    """
    Detect the product name from template content.

    :param content: The template file content string.
    :return: The detected product name string or None when not found.
    """

    product_name = None  # Initialize variable for detected product name

    for line in content.splitlines():  # Iterate through each line to find a sensible title
        if line and re.search(r"[A-Za-zÀ-ž0-9]", line):  # Verify line contains visible alphanumeric characters
            product_name = line.strip()  # Use the first sensible non-empty line as product name
            break  # Stop after locating the first candidate product name

    return product_name  # Return detected product name or None


def detect_platform_indicator(content: str) -> bool:
    """
    Detect whether a platform indicator exists in the content.

    :param content: The template file content string.
    :return: True when a platform indicator is found, False otherwise.
    """

    normalized_content = re.sub(r"[^a-z0-9]+", "", content.lower())  # Normalize content to compare compact platform names regardless of spaces/punctuation

    for display_name, platform_id in PLATFORMS_MAP.items():  # Iterate platform display and id mappings
        spaced_display_name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", display_name)  # Split camel-cased platform name into spaced variant (e.g., MercadoLivre -> Mercado Livre)
        compact_display_name = re.sub(r"[^a-z0-9]+", "", display_name.lower())  # Compact display name for normalized comparison
        compact_platform_id = re.sub(r"[^a-z0-9]+", "", platform_id.lower())  # Compact platform id for normalized comparison

        if re.search(rf"\b{re.escape(display_name)}\b", content, re.IGNORECASE):  # Verify original display name appears in content
            return True  # Return True immediately when a platform indicator is detected

        if re.search(rf"\b{re.escape(spaced_display_name)}\b", content, re.IGNORECASE):  # Verify spaced display variant appears in content
            return True  # Return True immediately when a platform indicator is detected

        if re.search(rf"\b{re.escape(platform_id)}\b", content, re.IGNORECASE):  # Verify platform id appears in content
            return True  # Return True immediately when a platform indicator is detected

        if compact_display_name in normalized_content or compact_platform_id in normalized_content:  # Verify compact forms against normalized content as a final fallback
            return True  # Return True when compact indicator match is detected

    return False  # Return False when no known platform indicator was found


def detect_product_url(content: str) -> Optional[str]:
    """
    Detect the first HTTP/HTTPS URL in the content.

    :param content: The template file content string.
    :return: The matched URL string or None when not found.
    """

    match = re.search(r"https?://[\w\-\.\/~\?&=%#]+", content)  # Search for HTTP/HTTPS URL using existing pattern
    return match.group(0) if match else None  # Return matched URL or None


def detect_price_fields(content: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Detect price-like tokens and extract current and old prices.

    :param content: The template file content string.
    :return: Tuple(current_price, old_price, price_matches).
    """

    price_matches = re.findall(r"R\$\s*[\d\.,]+|\b[\d]{1,3}(?:[\.,][\d]{2,3})\b", content)  # Find potential price tokens using existing pattern

    current_price = None  # Initialize current price variable
    old_price = None  # Initialize old price variable

    if price_matches:  # If one or more price-like tokens were found
        por_match = re.search(r"POR APENAS\s*\*?R\$\s*([\d\.,]+)\*?", content, re.IGNORECASE)  # Try to capture current price from explicit phrase
        if por_match:  # Verify the explicit current price phrase matched
            current_price = por_match.group(1).strip()  # Extract numeric portion for current price

        de_match = re.search(r"DE\s*\*?R\$\s*([\d\.,]+)\*?", content, re.IGNORECASE)  # Try to capture old price from explicit phrase
        if de_match:  # Verify the explicit old price phrase matched
            old_price = de_match.group(1).strip()  # Extract numeric portion for old price

        if current_price is None and old_price is None and any(m.startswith("R$") for m in price_matches):  # Use currency-prefixed fallback when explicit phrases not present
            r_prices = [m for m in price_matches if m.strip().startswith("R$")]  # Collect tokens that explicitly include currency prefix
            if r_prices:  # Verify there is at least one currency-prefixed token for fallback logic
                if len(r_prices) == 1:  # If only one currency-prefixed token exists
                    current_price = re.sub(r"[^\d,\.]", "", r_prices[0]).strip()  # Normalize token into numeric string for current price
                else:  # If multiple currency-prefixed tokens exist
                    old_price = re.sub(r"[^\d,\.]", "", r_prices[0]).strip()  # Normalize first token as old price
                    current_price = re.sub(r"[^\d,\.]", "", r_prices[-1]).strip()  # Normalize last token as current price

    return current_price, old_price, price_matches  # Return extracted price values and the raw matches list


def validate_price_relationships(old_price: Optional[str], current_price: Optional[str], content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate logical relationships between detected price fields.

    :param old_price: The detected old price string or None.
    :param current_price: The detected current price string or None.
    :param content: The template file content string.
    :return: Tuple(valid_flag, error_message_or_None).
    """

    try:  # Try to parse numeric strings into floats for comparison
        def parse_price(p: str) -> float:  # Define inline parser for localized numeric strings
            return float(p.replace('.', '').replace(',', '.'))  # Convert Brazilian-style numeric to python float

        parsed_old = parse_price(old_price) if old_price else None  # Parse old price when present
        parsed_current = parse_price(current_price) if current_price else None  # Parse current price when present
    except Exception:  # Handle parsing exceptions gracefully
        parsed_old = None  # Reset parsed_old on parse failure
        parsed_current = None  # Reset parsed_current on parse failure

    if old_price and not current_price:  # Verify old price must not appear without a current price
        return False, "inconsistent price fields detected"  # Return invalid status and reason when old price exists alone

    discount_present = bool(re.search(r"\d{1,3}%|desconto", content, re.IGNORECASE))  # Detect discount percentage or keyword using existing pattern
    if discount_present and not old_price:  # Verify discount must not appear without old price
        return False, "inconsistent price fields detected"  # Return invalid status and reason when discount appears without old price

    if parsed_old is not None and parsed_current is not None and abs(parsed_old - parsed_current) < 1e-6:  # Verify old and current prices are not equal
        return False, "inconsistent price fields detected"  # Return invalid status when prices are equal

    return True, None  # Return valid status when all logical price checks passed


def output_missing_fields(missing_fields: List[str]) -> bool:
    """
    Output formatted warning messages for missing mandatory fields and return true if any fields are missing.

    :param missing_fields: List of missing field names.
    :return: True if any fields are missing, False otherwise.
    """
    
    if not missing_fields:  # If the list of missing fields is empty
        return False  # Return False when no fields are missing

    for field in missing_fields:  # Iterate each missing field to create a warning message
        print(f"{BackgroundColors.RED}Template validation failed: missing mandatory field {BackgroundColors.GREEN}{field}{Style.RESET_ALL}")  # Append formatted message for the missing field
    
    return True  # Return True when any missing fields are found


def validate_template_file(template_path: Path) -> bool:
    """
    Orchestrate template validation using smaller validation functions.

    :param template_path: Path to the template file to validate.
    :return: True when template is valid, False when invalid.
    """

    content = read_template_content(template_path)  # Read template file content safely and get string or None

    if content is None:  # Verify the template content was read successfully
        print(f"{BackgroundColors.YELLOW}[WARNING] Template validation failed: missing mandatory field Template File{Style.RESET_ALL}")  # Log warning when file missing or unreadable
        return False  # Return False when content could not be read

    missing_fields: List[str] = []  # Initialize list to collect missing mandatory fields

    product_name = detect_product_name(content)  # Detect product name from content using dedicated function
    if not product_name:  # Verify product name detection result
        missing_fields.append("Product name")  # Record missing product name when detection failed

    platform_ok = detect_platform_indicator(content)  # Detect platform indicator presence using dedicated function
    if not platform_ok:  # Verify platform indicator detection result
        missing_fields.append("Platform indicator")  # Record missing platform indicator when detection failed

    product_url = detect_product_url(content)  # Detect product URL using dedicated function
    if not product_url:  # Verify product URL detection result
        missing_fields.append("Product URL")  # Record missing product URL when detection failed

    current_price, old_price, _ = detect_price_fields(content)  # Detect price fields using dedicated function
    if not current_price:  # Verify current price detection result
        missing_fields.append("Current price")  # Record missing current price when detection failed

    if missing_fields:  # If any mandatory fields are missing, build and emit warnings
        msgs = output_missing_fields(missing_fields)  # Build warning messages for missing fields
        return not msgs  # Return False when mandatory fields are missing

    valid_prices, reason = validate_price_relationships(old_price, current_price, content)  # Validate logical price relationships
    if not valid_prices:  # Verify result of price relationship validation
        print(f"{BackgroundColors.YELLOW}[WARNING] Template validation failed: {BackgroundColors.GREEN}{reason}{Style.RESET_ALL}")  # Print price inconsistency warning with color
        return False  # Return False when price relationships are invalid

    verbose_output(f"{BackgroundColors.GREEN}Template validation successful{Style.RESET_ALL}")  # Output verbose success message when validation passes

    return True  # Return True when all validations passed


def ensure_history_file_exists(history_file_path: str) -> bool:
    """
    Ensure the JSON history file exists and create it if missing.

    :param history_file_path: Path to the JSON history file.
    :return: True if the history file exists or was created successfully.
    """

    history_path = Path(history_file_path)  # Create a Path object for the history file
    if not history_path.exists():  # Verify if the history file does not exist
        try:  # Try to create an empty JSON file when missing
            with history_path.open("w", encoding="utf-8") as f:  # Open the history file for writing
                json.dump({}, f, indent=2, ensure_ascii=False)  # Initialize file with empty JSON object
        except Exception as e:  # Handle any exception during file creation
            print(f"[ERROR] Failed to create history file: {e}")  # Log the error to stdout
            return False  # Return False when file creation failed
    return True  # Return True when file already exists or was created


def read_history_for_day(day_str: str, history_file_path: str) -> dict:
    """
    Read and return the history dictionary for a given day from the JSON history file.

    :param day_str: Day string in format "DD-MM-YYYY" to read history for.
    :param history_file_path: Path to the JSON history file.
    :return: Dictionary with the history for the requested day (empty dict when none).
    """

    if not ensure_history_file_exists(history_file_path):  # Verify the history file exists or was created
        return {}  # Return empty dict when history file is unavailable

    try:  # Try to read the JSON history file
        with open(history_file_path, "r", encoding="utf-8") as f:  # Open the history file for reading
            data = json.load(f)  # Load the JSON content into a Python object
    except Exception:  # Handle JSON parsing or IO exceptions
        data = {}  # Fallback to empty dict when reading fails

    return data.get(day_str, {})  # Return the day's history or empty dict when not present


def remove_url_line_from_input_file(url, local_html_path=None):
    """
    Removes a line containing the specified URL from the input file. If local_html_path is provided, it will only remove the line if it matches both the URL and the local HTML path.
    
    :param url: The URL to remove from the input file
    :param local_html_path: Optional local HTML path to match for more precise removal
    :return: True if a line was removed, False otherwise
    """
    
    verbose_output(
        f"{BackgroundColors.GREEN}Removing URL from input file: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}"
    )  # Output the verbose message
    
    try:  # Wrap file operations to avoid crashing the main loop
        if not verify_filepath_exists(INPUT_FILE): # If the input file doesn't exist, nothing to remove
            return False  # Indicate nothing removed

        removed = False  # Track whether we removed a line
        with open(INPUT_FILE, "r", encoding="utf-8") as f:  # Read current input file
            lines = f.readlines()  # Load all lines

        new_lines = []  # Lines to keep
        for line in lines:  # Iterate existing lines
            stripped = line.strip()  # Trim whitespace
            if not stripped:  # Preserve empty lines
                new_lines.append(line)  # Keep blank lines as-is
                continue  # Continue to next line

            parts = stripped.split(None, 1)  # Split into at most 2 tokens (url and optional path)
            first_token = parts[0] if parts else ""  # Extract URL token
            second_token = parts[1].strip() if len(parts) > 1 else None  # Extract optional local path

            if not removed and first_token == url:  # Candidate match on URL
                if local_html_path:  # If caller provided a local path, prefer exact match with second token
                    if second_token and os.path.normpath(second_token) == os.path.normpath(local_html_path):  # Exact local path match
                        removed = True  # Mark removed and skip appending this line
                        continue  # Skip appending matched line
                    else:  # URL matches but local path differs
                        new_lines.append(line)  # Keep this line
                        continue  # Continue processing
                else:  # No local path required, remove first occurrence of matching URL
                    removed = True  # Mark removed and skip appending this line
                    continue  # Skip appending matched line

            new_lines.append(line)  # Keep non-matching line

        if removed:  # If we removed a line, atomically rewrite the file
            tmp_path = INPUT_FILE + ".tmp"  # Temporary file path for safe write
            with open(tmp_path, "w", encoding="utf-8") as f:  # Write new content to temp file
                f.writelines(new_lines)  # Write kept lines back
            try:  # Attempt atomic replace
                os.replace(tmp_path, INPUT_FILE)  # Replace original file with temp file
            except Exception:  # Fallback to non-atomic replace
                with open(INPUT_FILE, "w", encoding="utf-8") as f:  # Open original for overwrite
                    f.writelines(new_lines)  # Write kept lines
        return removed  # Return whether a line was removed
    except Exception:  # On any error, do not fail the scraping run
        return False  # Indicate nothing removed


def generate_marketing_text(product_description, description_file, product_data=None, product_url=None, api_key=None, key_index=1, total_keys=1):
    """
    Generates marketing text from product description using Gemini AI.
    Uses a single API key attempt and signals quota exhaustion for caller-side key rotation.
    
    :param product_description: The raw product description text
    :param description_file: Path to the description file (used to determine output directory)
    :param product_data: Optional dictionary containing product information (e.g., is_international)
    :param product_url: Optional product URL used to apply platform-specific prompt rules
    :param api_key: Gemini API key string to use for this single generation attempt
    :param key_index: 1-based index of the API key being used
    :param total_keys: Total number of available API keys for log context
    :return: True if successful, False otherwise
    """

    if not api_key:  # Verify if a concrete API key was provided by the caller.
        print(f"{BackgroundColors.RED}Error: No Gemini API key provided for generation.{Style.RESET_ALL}")  # Report missing key for this attempt.
        return False  # Return failure when key is unavailable.
    
    is_international = product_data.get("is_international", False) if product_data else False  # Verify if product is international
    International_instruction = ""  # Initialize international instruction as empty
    if is_international:  # If the product is international, we need to add a specific instruction to the prompt
        International_instruction = "\n\n**IMPORTANTE**: Este produto é INTERNACIONAL. Você DEVE adicionar '[PRODUTO INTERNACIONAL]: ' antes do nome do produto no início do texto formatado. Se o nome do produto já vier com o prefixo 'International - ', REMOVA esse prefixo antes de escrever o título final. Nunca duplique o indicador internacional."
    
    old_price_int = str(product_data.get("old_price_integer", "")).strip() if product_data else ""
    old_price_dec = str(product_data.get("old_price_decimal", "")).strip() if product_data else ""
    current_price_int = str(product_data.get("current_price_integer", "")).strip() if product_data else ""
    current_price_dec = str(product_data.get("current_price_decimal", "")).strip() if product_data else ""
    discount = str(product_data.get("discount_percentage", "")).strip() if product_data else ""
    
    no_discount_instruction = ""
    if ((old_price_int in ["N/A", ""] or old_price_dec in ["N/A", ""]) and discount in ["N/A", ""]) or (discount in ["N/A", ""] and old_price_int == current_price_int and old_price_dec == current_price_dec and current_price_int not in ["", "N/A"] and current_price_dec not in ["", "N/A"]):
        no_discount_instruction = "\n\n**IMPORTANTE**: Este produto NÃO possui desconto disponível. A linha de preço (💰) é OBRIGATÓRIA e deve permanecer. Quando o preço antigo e o preço atual forem iguais, use EXATAMENTE o formato: 💰 POR APENAS *R$<PREÇO_ATUAL>* (sem usar 'DE'). Remova APENAS a linha de desconto (🎟️...)."

    amazon_24h_instruction = ""  # Initialize Amazon-specific warning instruction
    if product_url and detect_platform(product_url) == "amazon":  # Verify if the current product belongs to Amazon
        amazon_24h_instruction = "\n\n**IMPORTANTE**: Para produtos da Amazon, ADICIONE IMEDIATAMENTE ANTES DA LINHA DO LINK (👉 ...) a seguinte mensagem EM NEGRITO E EM MAIUSCULAS: *ATENÇÃO: LINK VÁLIDO POR 24 HORAS. APÓS 24 HORAS, SÓ PERMANECE VÁLIDO SE O PRODUTO FOR ADICIONADO AO CARRINHO DENTRO DESSE PRAZO.*"
    
    prompt = GEMINI_MARKETING_PROMPT_TEMPLATE.format(product_description=product_description) + International_instruction + no_discount_instruction + amazon_24h_instruction  # Format template with all instructions

    gemini = None  # Initialize Gemini client reference for safe cleanup in all execution paths.

    try:  # Try a single-key generation request and delegate key rotation to caller.
        verbose_output(  # Emit verbose key-attempt diagnostics for this single-key attempt.
            true_string=f"{BackgroundColors.GREEN}Attempting to use Gemini API key {key_index} of {total_keys}...{Style.RESET_ALL}"
        )  # Output verbose message.

        gemini = Gemini(api_key, api_key_index=key_index)  # Create Gemini instance with key metadata for quota signaling.
        formatted_output = gemini.generate_content(prompt)  # Generate formatted marketing text with the provided key.

        if formatted_output:  # Verify if generation returned content.
            description_dir = os.path.dirname(description_file)  # Get directory of description file.
            formatted_file = os.path.join(description_dir, f"Template.txt")  # Build output file path.
            gemini.write_output_to_file(formatted_output, formatted_file)  # Write output to file.
            try:  # Try to validate the generated template file immediately after writing it.
                valid_template = validate_template_file(Path(formatted_file))  # Validate generated template file and get boolean result.
                if not valid_template:  # Verify if validation failed for the generated template.
                    print(f"{BackgroundColors.YELLOW}[WARNING] Template validation failed for file: {BackgroundColors.CYAN}{formatted_file}{Style.RESET_ALL}")  # Log warning when template is invalid.
            except Exception as e:  # Handle unexpected exceptions raised by the validation function.
                print(f"{BackgroundColors.YELLOW}[WARNING] Template validation failed: {e}{Style.RESET_ALL}")  # Log warning including exception message when validation raises.

            return True  # Return success for this key attempt even if validation logged warnings.

        verbose_output(f"{BackgroundColors.YELLOW}API key {key_index} returned empty response.{Style.RESET_ALL}")  # Report empty successful-response body.
        return False  # Return failure for empty response.
    except QuotaExceededError as e:  # Handle controlled quota exhaustion from Gemini layer.
        verbose_output(f"{BackgroundColors.YELLOW}[WARNING] API key {key_index} quota exhausted. Rotating to next API key.{Style.RESET_ALL}")  # Emit deterministic quota-rotation warning.
        raise e  # Re-raise controlled signal so caller can rotate without skipping URL.
    except Exception as e:  # Handle non-quota generation failures.
        verbose_output(f"{BackgroundColors.RED}Error with API key {key_index}: {e}{Style.RESET_ALL}")  # Report unexpected generation failure.
        return False  # Return failure for non-quota errors.
    finally:  # Guarantee client cleanup regardless of success, quota signal, or generic failure.
        if gemini is not None:  # Verify if Gemini client was instantiated before cleanup.
            gemini.close()  # Close Gemini client to release resources.


def build_expected_index_url_map(urls_to_process: list) -> Dict[int, str]:
    """
    Builds expected index-to-URL mapping from processing input.

    :param urls_to_process: List of tuples containing URL and optional local HTML path.
    :return: Dictionary mapping 1-based index to URL.
    """

    expected_map = {}  # Store expected 1-based index mapped to URL

    for index, item in enumerate(urls_to_process, 1):  # Iterate through input tuples preserving deterministic order
        url = item[0] if isinstance(item, tuple) and len(item) > 0 else str(item)  # Resolve URL field from tuple-safe structure
        expected_map[index] = url  # Persist URL for this expected row index

    return expected_map  # Return expected index-to-URL mapping


def list_product_directories_from_run(timestamped_output_dir: Optional[str]) -> List[str]:
    """
    Lists product directory names from the final run directory.

    :param timestamped_output_dir: Absolute path to the run output directory.
    :return: List containing product directory names only.
    """

    if not timestamped_output_dir or not os.path.isdir(timestamped_output_dir):  # Verify if final run directory is available
        return []  # Return empty list when run directory is missing

    directory_names = []  # Initialize list of product directory names

    for item in os.listdir(timestamped_output_dir):  # Iterate through all entries in final run directory
        full_path = os.path.join(timestamped_output_dir, item)  # Build absolute path for the current entry
        if os.path.isdir(full_path):  # Verify if entry is a directory
            directory_names.append(item)  # Collect directory name for downstream parsing

    return directory_names  # Return collected product directory names


def extract_product_index_from_directory_name(directory_name: str) -> Optional[int]:
    """
    Extracts numeric product index from a directory name prefix.

    :param directory_name: Directory name in format '<index>. <product name>'.
    :return: Parsed index integer or None when format does not match.
    """

    match = re.match(r"^(\d+)\.\s+.+$", directory_name)  # Match expected indexed directory naming pattern
    if not match:  # Verify if name matched indexed pattern
        return None  # Return None when index prefix is unavailable

    try:  # Attempt integer conversion for captured index value
        return int(match.group(1))  # Return parsed integer index from prefix capture
    except Exception:  # Handle unexpected conversion errors safely
        return None  # Return None when conversion fails


def extract_product_name_from_directory_name(directory_name: str) -> Optional[str]:
    """
    Extracts product name portion from an indexed directory name.

    :param directory_name: Directory name in format '<index>. <product name>'.
    :return: Product name string without index prefix or None when format does not match.
    """

    match = re.match(r"^\d+\.\s+(.+)$", directory_name)  # Match and capture product name portion after index prefix
    if not match:  # Verify if name matched expected format
        return None  # Return None when product name cannot be extracted

    product_name = match.group(1).strip()  # Normalize extracted product name by trimming whitespace
    return product_name if product_name else None  # Return normalized product name when non-empty


def build_indexed_product_records(directory_names: List[str]) -> List[Tuple[int, str, str]]:
    """
    Builds indexed product records from directory names.

    :param directory_names: List of directory names from the final run output.
    :return: List of tuples containing (index, product_name, full_directory_name).
    """

    records = []  # Store parsed product directory records

    for directory_name in directory_names:  # Iterate over each directory name for parsing
        product_index = extract_product_index_from_directory_name(directory_name)  # Parse numeric prefix index from directory name
        product_name = extract_product_name_from_directory_name(directory_name)  # Parse product name portion from directory name

        if product_index is None or product_name is None:  # Verify if directory can be represented as an indexed product record
            continue  # Skip non-matching entries to keep verification deterministic

        records.append((product_index, product_name, directory_name))  # Append normalized record tuple for downstream validation

    return records  # Return parsed product records list


def build_existing_indexes_set(indexed_records: List[Tuple[int, str, str]]) -> Set[int]:
    """
    Builds a set of existing product indexes.

    :param indexed_records: Parsed indexed product records.
    :return: Set containing existing index values found in output directories.
    """

    existing_indexes = set()  # Initialize set for unique index values

    for product_index, _, _ in indexed_records:  # Iterate through records to collect indexes only
        existing_indexes.add(product_index)  # Add index value to unique set

    return existing_indexes  # Return set of existing indexes


def identify_missing_indexes(expected_indexes: Set[int], existing_indexes: Set[int]) -> List[int]:
    """
    Identifies missing indexes by set difference.

    :param expected_indexes: Set of expected indexes from input URLs.
    :param existing_indexes: Set of indexes found in output directories.
    :return: Sorted list of missing index values.
    """

    missing = sorted(expected_indexes - existing_indexes)  # Compute and sort missing indexes deterministically
    return missing  # Return sorted missing index list


def print_missing_product_warnings(missing_indexes: List[int], expected_index_url_map: Dict[int, str]) -> None:
    """
    Prints warnings for each missing product index with source URL.

    :param missing_indexes: Sorted list of missing indexes.
    :param expected_index_url_map: Dictionary mapping expected index to source URL.
    :return: None.
    """

    for product_index in missing_indexes:  # Iterate through each missing index for warning output
        product_url = expected_index_url_map.get(product_index, "URL_NOT_FOUND")  # Resolve URL mapped to missing index
        print(f"{BackgroundColors.CYAN}{product_index}{BackgroundColors.GREEN} - {BackgroundColors.CYAN}{product_url}{BackgroundColors.YELLOW}{Style.RESET_ALL}")  # Emit required missing-index warning format


def group_records_by_product_name(indexed_records: List[Tuple[int, str, str]]) -> Dict[str, List[Tuple[int, str]]]:
    """
    Groups indexed records by product name.

    :param indexed_records: Parsed indexed product records.
    :return: Dictionary mapping product name to list of (index, full_directory_name).
    """

    grouped_records = {}  # Initialize grouped records dictionary

    for product_index, product_name, directory_name in indexed_records:  # Iterate through records for grouping by name
        grouped_records.setdefault(product_name, []).append((product_index, directory_name))  # Append index and directory for this product name

    return grouped_records  # Return grouped dictionary by product name


def identify_duplicate_product_names(grouped_records: Dict[str, List[Tuple[int, str]]]) -> Dict[str, List[Tuple[int, str]]]:
    """
    Identifies product names that appear more than once.

    :param grouped_records: Dictionary mapping product name to indexed directory entries.
    :return: Dictionary containing only duplicated product names and their entries.
    """

    duplicates = {}  # Initialize duplicates dictionary

    for product_name, entries in grouped_records.items():  # Iterate grouped records to identify duplicate names
        if len(entries) > 1:  # Verify if current product name appears more than once
            duplicates[product_name] = entries  # Persist duplicate entry list for this product name

    return duplicates  # Return only duplicate name groups


def print_duplicate_product_warnings(product_name: str, directory_name_to_remove: str) -> None:
    """
    Prints warnings for duplicate product name cleanup.

    :param product_name: Duplicate product name portion without index prefix.
    :param directory_name_to_remove: Full directory name selected for removal.
    :return: None.
    """

    print(f"{BackgroundColors.YELLOW}[WARNING] Duplicate product name detected: {product_name}{Style.RESET_ALL}\n{BackgroundColors.YELLOW}[WARNING] Removing duplicate directory with highest index: {directory_name_to_remove}{Style.RESET_ALL}")  # Emit duplicate-name detection and removal warnings in single call


def remove_duplicate_directories_with_highest_index(timestamped_output_dir: Optional[str], duplicate_records: Dict[str, List[Tuple[int, str]]]) -> List[str]:
    """
    Removes duplicate product directories preserving the lowest index entry.

    :param timestamped_output_dir: Absolute path to the final run output directory.
    :param duplicate_records: Dictionary containing duplicated product names and indexed entries.
    :return: List containing removed directory names.
    """

    removed_directory_names = []  # Track removed directories for optional downstream usage

    if not timestamped_output_dir or not os.path.isdir(timestamped_output_dir):  # Verify if final run directory exists before removal operations
        return removed_directory_names  # Return empty removal list when directory is unavailable

    for product_name, entries in duplicate_records.items():  # Iterate each duplicate product name group
        sorted_entries = sorted(entries, key=lambda item: item[0])  # Sort by ascending index to preserve the lowest index entry
        entries_to_remove = sorted_entries[1:]  # Select all higher-index duplicate entries for removal

        for _, directory_name_to_remove in entries_to_remove:  # Iterate through duplicate directories selected for deletion
            print_duplicate_product_warnings(product_name, directory_name_to_remove)  # Emit warnings before deletion operation
            full_path_to_remove = os.path.join(timestamped_output_dir, directory_name_to_remove)  # Build absolute path to duplicate directory

            if os.path.isdir(full_path_to_remove):  # Verify if duplicate directory still exists before deletion
                try:  # Attempt to remove duplicate directory from disk
                    shutil.rmtree(full_path_to_remove)  # Delete directory tree for duplicate highest index entry
                    removed_directory_names.append(directory_name_to_remove)  # Track removed directory name
                except Exception as e:  # Handle filesystem deletion errors safely
                    print(f"{BackgroundColors.RED}Error removing duplicate directory {BackgroundColors.CYAN}{directory_name_to_remove}{BackgroundColors.RED}: {BackgroundColors.YELLOW}{e}{Style.RESET_ALL}")  # Report duplicate deletion failure

    return removed_directory_names  # Return removed directory names list


def print_output_count_mismatch_warning(expected_total: int, existing_total: int) -> None:
    """
    Prints warning when output directory count differs from expected URL count.

    :param expected_total: Total number of expected URLs.
    :param existing_total: Total number of detected product directories.
    :return: None.
    """

    if expected_total == existing_total:  # Verify if counts match before warning output
        return  # Return immediately when there is no mismatch

    print(f"{BackgroundColors.YELLOW}[WARNING] Output directory count mismatch: expected {BackgroundColors.CYAN}{expected_total}{BackgroundColors.YELLOW}, found {BackgroundColors.CYAN}{existing_total}{Style.RESET_ALL}")  # Emit count mismatch warning


def run_final_output_integrity_verification(timestamped_output_dir: Optional[str], urls_to_process: list) -> None:
    """
    Runs final output directory integrity verification pipeline.

    :param timestamped_output_dir: Absolute path to the final run output directory.
    :param urls_to_process: List of tuples containing URL and optional local HTML path.
    :return: None.
    """

    expected_index_url_map = build_expected_index_url_map(urls_to_process)  # Build deterministic expected index-to-URL mapping from original input order
    expected_indexes = set(expected_index_url_map.keys())  # Build expected index set from mapping keys

    directory_names = list_product_directories_from_run(timestamped_output_dir)  # Collect current directory names from final run output path
    indexed_records = build_indexed_product_records(directory_names)  # Parse indexed records for validation and duplicate detection
    existing_indexes = build_existing_indexes_set(indexed_records)  # Build existing index set from parsed records

    print_output_count_mismatch_warning(len(expected_index_url_map), len(indexed_records))  # Emit warning when expected and existing counts diverge

    missing_indexes = identify_missing_indexes(expected_indexes, existing_indexes)  # Determine missing expected indexes from current output
    print_missing_product_warnings(missing_indexes, expected_index_url_map)  # Emit one warning line per missing index using required format

    grouped_records = group_records_by_product_name(indexed_records)  # Group indexed records by product name only
    duplicate_records = identify_duplicate_product_names(grouped_records)  # Filter grouped records to duplicate product names only
    remove_duplicate_directories_with_highest_index(timestamped_output_dir, duplicate_records)  # Remove higher-index directories for duplicate product names


def show_amazon_update_warning(has_amazon: bool, title: str) -> None:
    """
    Show a GUI warning when Amazon URLs were present in the run.

    :param has_amazon: Boolean flag indicating whether any Amazon URLs were processed.
    :param title: Title for the GUI warning dialog.
    :return: None
    """

    if not has_amazon:  # Verify if no Amazon URLs were processed and nothing to do
        return  # Return immediately when no Amazon URLs were present

    try:  # Try to display a GUI warning to the user using tkinter
        root = Tk()  # Create a hidden Tk root window for the dialog
        root.withdraw()  # Hide the root window so only the dialog is shown
        message = (
            "One or more Amazon links were processed. Amazon short links are valid for 24 hours. "
            "Please update Amazon URLs that require freshness to avoid expired affiliate links in the generated template files."
        )  # Compose the user-facing message explaining the 24h validity constraint
        messagebox.showwarning(title, message)  # Show a modal warning dialog to the user
        root.destroy()  # Destroy the hidden root to clean up GUI resources
    except Exception as e:  # If GUI display fails, fallback to console warning without raising
        print(f"{BackgroundColors.YELLOW}[WARNING] Could not display GUI warning: {e}{Style.RESET_ALL}")  # Emit fallback console warning


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
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Welcome to the {BackgroundColors.CYAN}E-Commerces WebScraper{BackgroundColors.GREEN} program!{Style.RESET_ALL}",
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

    api_keys_raw = os.getenv(ENV_VARIABLES["GEMINI"], "")  # Get Gemini API key(s) from environment variables.
    api_keys = [key.strip() for key in api_keys_raw.split(",") if key.strip()]  # Split and normalize non-empty keys.
    if not api_keys:  # Verify if at least one Gemini API key exists before processing URLs.
        print(f"{BackgroundColors.RED}Error: No Gemini API keys configured in .env file.{Style.RESET_ALL}")  # Report missing API key configuration.
        return  # Exit early when no keys are available.
    
    create_directory(
        os.path.abspath(INPUT_DIRECTORY), INPUT_DIRECTORY.replace(".", "")
    )  # Create the input directory

    if not ensure_input_file_exists():  # Ensure the input file exists, and if not, create it with instructions
        return  # Exit if unable to ensure input file
    
    ensure_ffmpef_is_installed()  # Check if ffmpeg is installed and install it if not
    
    create_directory(
        os.path.abspath(OUTPUT_DIRECTORY), OUTPUT_DIRECTORY.replace(".", "")
    )  # Create the base output directory
    
    staging_output_dir = os.path.join(OUTPUT_DIRECTORY, ".staging")  # Staging area for interim outputs
    create_directory(os.path.abspath(staging_output_dir), "Outputs/.staging")  # Ensure staging exists

    timestamped_output_dir = None  # Will be created lazily on first successful scrape
    
    successful_scrapes = 0  # Counter for successful operations
    has_amazon = False  # Initialize flag to detect presence of Amazon URLs during processing

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
            if platform_id == "amazon":  # Verify if current platform is Amazon
                has_amazon = True  # Mark presence of Amazon URL for later GUI warning
            platform_name = ({v: k for k, v in PLATFORMS_MAP.items()}).get(platform_id, platform_id if platform_id else "Unknown")  # Derive reverse mapping from PLATFORMS_MAP and get human-friendly platform name
            desc = (
                f"{BackgroundColors.GREEN}Processing {BackgroundColors.CYAN}{index}{BackgroundColors.GREEN}/{BackgroundColors.CYAN}{total_urls}{BackgroundColors.GREEN} - {BackgroundColors.CYAN}{platform_name}{BackgroundColors.GREEN}"
            )  # Build colored description with platform
            pbar.set_description(desc)  # Update the progress bar description

            original_local_html_path = local_html_path  # Preserve original local path token from input file for deterministic retries and input clearing
            resolved_local_html_path = local_html_path  # Keep resolved local path value reused by retry attempts
            url_processed_successfully = False  # Track whether this URL finished with verified output directory and successful formatting

            verify_affiliate_url_format(url)  # Verify affiliate-format URL for supported platforms

            for retry_attempt in range(OUTPUT_DIRECTORY_RETRY_ATTEMPTS + 1):  # Retry URL processing only when output directory is not generated
                local_html_path = resolved_local_html_path  # Reuse resolved local path by default for deterministic retries

                if retry_attempt == 0 and local_html_path:  # Resolve local path only once in the first attempt
                    local_html_path = resolve_local_html_path(local_html_path)  # Resolve path with fallback variations
                    resolved_local_html_path = local_html_path  # Persist resolved path for retry attempts
                    verbose_output(f"{BackgroundColors.GREEN}Using local HTML file: {BackgroundColors.CYAN}{local_html_path}{Style.RESET_ALL}")  # Inform user about offline mode

                verbose_output(f"{BackgroundColors.CYAN}Step 1{BackgroundColors.GREEN}: Scraping the product information{Style.RESET_ALL}")  # Step 1: Scrape the product information
                scrape_result = scrape_product(url, staging_output_dir, local_html_path)  # Scrape the product writing into staging

                if not scrape_result or len(scrape_result) != 6:  # If scraping failed or returned invalid result
                    print(f"{BackgroundColors.RED}Skipping {BackgroundColors.CYAN}{url}{BackgroundColors.RED} due to scraping failure.{Style.RESET_ALL}\n")  # Notify user about skip
                    try:  # Attempt to clean any partial staging output for this URL
                        tmp_product_name = None  # Initialize temporary product name variable
                        if isinstance(scrape_result, tuple) and scrape_result[2]:  # Verify tuple shape and product dir field
                            tmp_product_name = scrape_result[2]  # Extract product directory name from scrape_result
                        if tmp_product_name:  # Only proceed if we found a temporary product directory name
                            tmp_path = os.path.join(staging_output_dir, tmp_product_name)  # Build staging path for that product
                            if os.path.exists(tmp_path):  # Verify if the staging path exists on disk
                                shutil.rmtree(tmp_path)  # Remove the partial staging directory to keep staging clean
                    except Exception:  # Catch and ignore any errors during staging cleanup
                        pass  # Ignore cleanup errors and continue

                    if retry_attempt < OUTPUT_DIRECTORY_RETRY_ATTEMPTS:  # Verify if another retry attempt is still allowed
                        print(f"{BackgroundColors.YELLOW}[WARNING] Output directory missing after processing URL index {index}. Retrying processing.{Style.RESET_ALL}")  # Warn and retry same URL position
                        continue  # Retry processing the same URL immediately

                    print(f"{BackgroundColors.YELLOW}[WARNING] Failed to generate output directory after retry for URL index {index}.{Style.RESET_ALL}")  # Report definitive failure after retry exhaustion
                    break  # Stop retry loop and keep URL as unsuccessful

                product_data, description_file, product_directory, html_path_for_assets, zip_path_to_cleanup, extracted_dir_to_cleanup = scrape_result  # Unpack the scrape result  # Destructure returned tuple

                if not product_data:  # If scraping failed unexpectedly  # Validate product_data presence
                    print(f"{BackgroundColors.RED}Skipping {BackgroundColors.CYAN}{url}{BackgroundColors.RED} due to scraping failure.{Style.RESET_ALL}\n")  # Inform about unexpected failure

                    if retry_attempt < OUTPUT_DIRECTORY_RETRY_ATTEMPTS:  # Verify if another retry attempt is still allowed
                        print(f"{BackgroundColors.YELLOW}[WARNING] Output directory missing after processing URL index {index}. Retrying processing.{Style.RESET_ALL}")  # Warn and retry same URL position
                        continue  # Retry processing the same URL immediately

                    print(f"{BackgroundColors.YELLOW}[WARNING] Failed to generate output directory after retry for URL index {index}.{Style.RESET_ALL}")  # Report definitive failure after retry exhaustion
                    break  # Stop retry loop and keep URL as unsuccessful

                if timestamped_output_dir is None:  # Lazily create run directory on first success
                    timestamped_output_dir = create_timestamped_output_directory(OUTPUT_DIRECTORY)  # Create timestamped run dir
                    clean_unknown_product_directories(timestamped_output_dir)  # Clean up any "Unknown Product" dirs inside this run  # Remove old placeholders

                indexed_product_directory = f"{index}. {product_directory}"  # Prefix final directory with source row index from urls.txt

                try:  # Attempt to move product output from staging to final run dir
                    src_dir = os.path.join(staging_output_dir, product_directory)  # Path to product in staging
                    dest_dir = os.path.join(timestamped_output_dir, indexed_product_directory)  # Target path inside final run dir with row index prefix
                    if os.path.exists(dest_dir):  # If destination exists, remove it first to replace  # Ensure replace semantics
                        shutil.rmtree(dest_dir)  # Remove existing destination to avoid conflicts
                    if os.path.exists(src_dir):  # Only move if staging source exists
                        shutil.move(src_dir, dest_dir)  # Move staging product to final run
                    product_name_safe = product_data.get("product_name_safe", "")  # Get canonical directory name from scraper
                    description_file = os.path.join(dest_dir, f"{product_name_safe}_description.txt")  # Update description file path to final location using canonical name
                    product_directory = indexed_product_directory  # Use indexed final directory name for downstream steps
                except Exception as e:  # Handle move errors
                    print(f"{BackgroundColors.YELLOW}Warning: Could not move staging output to final run directory: {e}{Style.RESET_ALL}")  # Warn user but continue

                final_product_directory_path = os.path.join(timestamped_output_dir, product_directory) if timestamped_output_dir and product_directory else None  # Build absolute path to expected final directory
                if not final_product_directory_path or not os.path.isdir(final_product_directory_path):  # Verify final directory exists before continuing pipeline
                    if retry_attempt < OUTPUT_DIRECTORY_RETRY_ATTEMPTS:  # Verify if another retry attempt is still allowed
                        print(f"{BackgroundColors.YELLOW}[WARNING] Output directory missing after processing URL index {index}. Retrying processing.{Style.RESET_ALL}")  # Warn and retry same URL position
                        continue  # Retry processing the same URL immediately

                    print(f"{BackgroundColors.YELLOW}[WARNING] Failed to generate output directory after retry for URL index {index}.{Style.RESET_ALL}")  # Report definitive failure after retry exhaustion
                    break  # Stop retry loop and keep URL as unsuccessful

                if product_directory and isinstance(product_directory, str):  # Only run image cleanup for valid product dirs
                    clean_duplicate_images(product_directory, timestamped_output_dir)  # Deduplicate images in final location
                    exclude_small_images(product_directory, timestamped_output_dir)  # Remove extremely small images

                input_source = html_path_for_assets or local_html_path  # Determine original input source to copy
                copy_original_input_to_output(input_source, product_directory, base_output_dir=timestamped_output_dir)  # Copy original input into final product folder

                if DELETE_LOCAL_HTML_FILE:  # Only perform deletions when configured
                    if extracted_dir_to_cleanup and os.path.exists(extracted_dir_to_cleanup):  # Remove extracted directory if present
                        try:  # Attempt deletion
                            shutil.rmtree(extracted_dir_to_cleanup)  # Delete extracted dir
                        except Exception:  # Ignore failures during deletion
                            pass  # Continue silently on failure
                    if zip_path_to_cleanup and os.path.exists(zip_path_to_cleanup):  # Remove original zip if present
                        try:  # Attempt deletion
                            os.remove(zip_path_to_cleanup)  # Delete zip file
                        except Exception:  # Ignore failures during deletion
                            pass  # Continue silently on failure
                
                try:  # Read the product description from the file
                    with open(str(description_file), "r", encoding="utf-8") as f:  # Open the description file with UTF-8 encoding
                        product_description = f.read()  # Read the product description
                except Exception as e:  # If reading the file fails
                    print(f"{BackgroundColors.RED}Error reading description file: {e}{Style.RESET_ALL}")

                    if retry_attempt < OUTPUT_DIRECTORY_RETRY_ATTEMPTS:  # Verify if another retry attempt is still allowed
                        print(f"{BackgroundColors.YELLOW}[WARNING] Output directory missing after processing URL index {index}. Retrying processing.{Style.RESET_ALL}")  # Warn and retry same URL position
                        continue  # Retry processing the same URL immediately

                    print(f"{BackgroundColors.YELLOW}[WARNING] Failed to generate output directory after retry for URL index {index}.{Style.RESET_ALL}")  # Report definitive failure after retry exhaustion
                    break  # Stop retry loop and keep URL as unsuccessful
                
                valid, invalid_reasons = validate_product_information(product_data, product_directory, description_file)  # Validate the product information

                if not valid:  # If the product information is not valid, skip Gemini formatting and output the reasons
                    print(
                        f"{BackgroundColors.RED}Skipping Step 2: Gemini formatting due to invalid product information for URL: {BackgroundColors.CYAN}{url}{BackgroundColors.RED}.{Style.RESET_ALL}"
                    )
                    break  # Stop retry loop because data is invalid and retrying directory creation is not meaningful

                verbose_output(f"{BackgroundColors.CYAN}Step 2{BackgroundColors.GREEN}: Formatting with Gemini AI{Style.RESET_ALL}")  # Step 2: Format the product description with Gemini AI
                
                success = False  # Initialize Gemini formatting success flag for this URL.
                exhausted_key_indices = set()  # Track exhausted key indices during the current rotation cycle.
                exhausted_cycles = 0  # Track how many full exhausted cycles happened for this URL.
                total_keys = len(api_keys)  # Compute total available keys for this URL attempt.

                global GEMINI_LAST_KEY_INDEX  # Reuse module-level key index to preserve deterministic rotation across URLs.
                current_idx = GEMINI_LAST_KEY_INDEX % total_keys if total_keys > 0 else 0  # Start from last successful key index.

                while True:  # Keep retrying same product request until success or maximum exhausted cycles reached.
                    key_index = current_idx + 1  # Convert zero-based key index to one-based display index.
                    api_key = api_keys[current_idx]  # Select API key for this iteration.

                    try:  # Try processing the same product with current key.
                        success = generate_marketing_text(  # Execute single-key Gemini generation attempt.
                            product_description,  # Reuse same product description for deterministic retry behavior.
                            description_file,  # Reuse same description file destination for deterministic retry behavior.
                            product_data,  # Reuse same product data context across retries.
                            url,  # Reuse same product URL across retries.
                            api_key=api_key,  # Pass current key only and let main handle rotations.
                            key_index=key_index,  # Pass one-based key index for logging and exception metadata.
                            total_keys=total_keys,  # Pass total key count for contextual logging.
                        )  # End single-key generation call.

                        if success:  # Verify whether generation succeeded for this key.
                            GEMINI_LAST_KEY_INDEX = current_idx  # Persist last successful key for next URL.
                            break  # Exit retry loop and continue URL pipeline.

                        current_idx = (current_idx + 1) % total_keys  # Rotate to next key on non-quota failure to maximize resilience.
                        if current_idx == 0:  # Verify if a full key round has been completed.
                            break  # Stop loop after one full non-quota rotation and keep failure result.
                    except QuotaExceededError as quota_error:  # Handle controlled quota exhaustion signal.
                        exhausted_key_index = quota_error.key_index if quota_error.key_index else key_index  # Resolve exhausted key index from exception metadata.
                        exhausted_key_indices.add(exhausted_key_index)  # Mark current key as exhausted for this cycle.
                        current_idx = (current_idx + 1) % total_keys  # Rotate to next key for same URL and same prompt.

                        if len(exhausted_key_indices) >= total_keys:  # Verify if all keys are exhausted in current cycle.
                            exhausted_cycles += 1  # Increment all-keys-exhausted cycle counter.
                            if exhausted_cycles > GEMINI_MAX_ALL_KEYS_EXHAUSTED_CYCLES:  # Verify if maximum cycle retries reached.
                                print(f"{BackgroundColors.RED}All API keys remained exhausted after {GEMINI_MAX_ALL_KEYS_EXHAUSTED_CYCLES} cycle(s) for URL: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}")  # Report final exhaustion failure for current URL.
                                break  # Stop retrying this URL after configured exhausted cycles.
                            print(f"{BackgroundColors.YELLOW}[WARNING] All API keys exhausted. Waiting {GEMINI_ALL_KEYS_EXHAUSTED_WAIT_SECONDS}s before retrying the same URL.{Style.RESET_ALL}")  # Report cooldown before restarting key rotation.
                            time.sleep(GEMINI_ALL_KEYS_EXHAUSTED_WAIT_SECONDS)  # Wait before restarting rotation to allow quota reset windows.
                            exhausted_key_indices.clear()  # Reset exhausted key tracking for next cycle.
                            current_idx = 0  # Restart rotation from first key after cooldown.

                        continue  # Continue retry loop for same URL.
                
                if success and os.path.isdir(final_product_directory_path):  # Count URL as successful only when formatting succeeded and final directory exists
                    description_dir = os.path.dirname(description_file)  # Get directory of description file
                    template_file = os.path.join(description_dir, "Template.txt")  # Path to the generated template file
                    validate_and_fix_output_file(template_file)  # Validate and fix formatting issues in the output file
                    
                    successful_scrapes += 1  # Increment successful scrapes counter
                    url_processed_successfully = True  # Mark URL as successfully processed for this index
                    if CLEAR_INPUT_FILE:  # Only clear input lines when configured
                        removed = remove_url_line_from_input_file(url, original_local_html_path)  # Attempt to remove the successful URL line from INPUT_FILE
                        verbose_output(f"{BackgroundColors.GREEN}Removed input line: {BackgroundColors.CYAN}{url}{BackgroundColors.GREEN} -> {removed}{Style.RESET_ALL}")  # Verbose result of removal
                elif success and not os.path.isdir(final_product_directory_path):  # Guard against impossible success-without-directory scenarios
                    if retry_attempt < OUTPUT_DIRECTORY_RETRY_ATTEMPTS:  # Verify if another retry attempt is still allowed
                        print(f"{BackgroundColors.YELLOW}[WARNING] Output directory missing after processing URL index {index}. Retrying processing.{Style.RESET_ALL}")  # Warn and retry same URL position
                        continue  # Retry processing the same URL immediately

                    print(f"{BackgroundColors.YELLOW}[WARNING] Failed to generate output directory after retry for URL index {index}.{Style.RESET_ALL}")  # Report definitive failure after retry exhaustion

                if url_processed_successfully:  # Exit retry loop immediately after successful and verified processing
                    break  # Stop retry loop for current URL

            if not url_processed_successfully:  # Ensure failures are explicit when URL did not complete with verified directory
                print(f"{BackgroundColors.YELLOW}[WARNING] URL index {index} finished without a verified output directory and was not counted as success.{Style.RESET_ALL}")  # Emit final warning for this URL
            
            if index < total_urls and not local_html_path:  # Add delay only for online requests (skip for local HTML inputs)
                time.sleep(DELAY_BETWEEN_REQUESTS)  # Sleep to avoid rate limiting between online requests

    run_final_output_integrity_verification(timestamped_output_dir, urls_to_process)  # Run final reliability verification after all URL processing has completed
    
    print(f"{BackgroundColors.GREEN}Successfully processed: {BackgroundColors.CYAN}{successful_scrapes}/{total_urls}{BackgroundColors.GREEN} URLs{Style.RESET_ALL}\n")  # Output the number of successful operations

    try:  # Clean up the staging directory if it's empty after processing all URLs
        if os.path.exists(staging_output_dir) and not os.listdir(staging_output_dir):  # If staging directory exists and is empty
            shutil.rmtree(staging_output_dir)  # Remove the empty staging directory
            verbose_output(f"{BackgroundColors.GREEN}Removed empty staging directory: {BackgroundColors.CYAN}{staging_output_dir}{Style.RESET_ALL}")
    except Exception:  # If an error occurs during cleanup, ignore it
        pass  # Best effort cleanup, ignore errors

    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
    )  # Output the start and finish times
    print(
        f"{BackgroundColors.BOLD}{BackgroundColors.GREEN}Program finished.{Style.RESET_ALL}"
    )  # Output the end of the program message
    show_amazon_update_warning(has_amazon, "Amazon URLs Expire in 24h")  # Show GUI warning when Amazon URLs were present in input

    (
        atexit.register(play_sound) if RUN_FUNCTIONS["Play Sound"] else None
    )  # Register the play_sound function to be called when the program finishes


if __name__ == "__main__":
    """
    This is the standard boilerplate that calls the main() function.

    :return: None
    """

    main()  # Call the main function
