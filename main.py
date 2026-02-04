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
    4. Check outputs in the ./Outputs/ directory for scraped data.

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
import os  # For running a command in the terminal
import platform  # For getting the operating system name
import sys  # For system-specific parameters and functions
# from AliExpress import AliExpress  # Import the AliExpress class
from colorama import Style  # For coloring the terminal
from dotenv import load_dotenv  # For loading environment variables
from Gemini import Gemini  # Import the Gemini class
from Logger import Logger  # For logging output to both terminal and file
from MercadoLivre import MercadoLivre  # Import the MercadoLivre class
# from Shein import Shein  # Import the Shein class
# from Shopee import Shopee  # Import the Shopee class
from pathlib import Path  # For handling file paths


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

TEST_URLs = ["https://mercadolivre.com/sec/2XY9zrA"]  # Test URLs for scraping

PLATFORMS_MAP = {
    "AliExpress": "aliexpress",
    "MercadoLivre": "mercadolivre",
    "Shein": "shein",
    "Shopee": "shopee",
}  # Mapping of platform names to identifiers
    

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


def sanitize_filename(filename):
    """
    Sanitizes a filename by removing invalid characters for filesystem compatibility.
    
    :param filename: The filename string to sanitize
    :return: Sanitized filename string containing only alphanumeric characters, spaces, hyphens, and underscores
    """
    
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in filename).strip()  # Remove invalid characters


def detect_platform(url):
    """
    Detects the e-commerce platform from a given URL by checking domain names.
    
    :param url: The product URL to analyze
    :return: Platform name (e.g., 'mercadolivre', 'shein', 'shopee') or None if not recognized
    """
    
    url_lower = url.lower()  # Convert URL to lowercase for case-insensitive matching
    
    for platform_name, platform_id in PLATFORMS_MAP.items():  # Iterate through supported platforms
        if platform_id in url_lower:  # Check if platform identifier is in URL
            verbose_output(
                f"{BackgroundColors.GREEN}Detected platform: {BackgroundColors.CYAN}{platform_name}{Style.RESET_ALL}"
            )
            return platform_id  # Return the platform identifier
    
    print(f"{BackgroundColors.YELLOW}Warning: Could not detect platform from URL: {url}{Style.RESET_ALL}")
    return None  # Return None if platform not recognized


def scrape_product(url):
    """
    Scrapes product information from a URL by detecting the platform and using the appropriate scraper.
    
    :param url: The product URL to scrape
    :return: Tuple of (product_data dict, description_file path, product_name_safe string) or (None, None, None) on failure
    """
    
    platform = detect_platform(url)  # Detect the e-commerce platform
    
    if not platform:  # If platform detection failed
        print(f"{BackgroundColors.RED}Unsupported platform. Skipping URL: {url}{Style.RESET_ALL}")
        return None, None, None
    
    scraper_classes = {  # Mapping of platform identifiers to scraper classes
        # "aliexpress": AliExpress,
        "mercadolivre": MercadoLivre,
        # "shein": Shein,
        # "shopee": Shopee,
    }
    
    scraper_class = scraper_classes.get(platform)  # Get the appropriate scraper class
    
    if not scraper_class:  # If scraper class not found
        print(f"{BackgroundColors.RED}Scraper not implemented for platform: {platform}{Style.RESET_ALL}")
        return None, None, None  # Return None values
    
    try:  # Try to scrape the product
        scraper = scraper_class(url)  # Create scraper instance
        product_data = scraper.scrape()  # Scrape the product
        
        if not product_data:  # If scraping failed
            print(f"{BackgroundColors.RED}Failed to scrape product from: {url}{Style.RESET_ALL}")
            return None, None, None  # Return None values
        
        product_name = product_data.get("name", "Unknown Product")  # Get product name
        product_name_safe = sanitize_filename(product_name)  # Sanitize filename
        description_file = f"./Outputs/{product_name_safe}/{product_name_safe}_description.txt"
        
        if not verify_filepath_exists(description_file):  # If description file not found
            print(f"{BackgroundColors.RED}Description file not found: {description_file}{Style.RESET_ALL}")
            return None, None, None  # Return None values
        
        return product_data, description_file, product_name_safe  # Return scraped data and file paths
        
    except Exception as e:  # If an error occurs during scraping
        print(f"{BackgroundColors.RED}Error during scraping: {e}{Style.RESET_ALL}")  # Print error message
        return None, None, None  # Return None values


def generate_marketing_text(product_description, product_name_safe, description_file):
    """
    Generates marketing text from product description using Gemini AI.
    
    :param product_description: The raw product description text
    :param product_name_safe: Sanitized product name for file naming
    :param description_file: Path to the description file (used to determine output directory)
    :return: True if successful, False otherwise
    """
    
    try:  # Try to generate marketing text
        api_key = os.getenv(ENV_VARIABLES["GEMINI"])  # Get Gemini API key
        gemini = Gemini(api_key)  # Create Gemini instance
        
        # Create the prompt for Gemini with strict formatting instructions
        prompt = f"""Você é um especialista em marketing de e-commerce. Sua tarefa é transformar as informações do produto abaixo em um texto de marketing persuasivo e formatado.

INFORMAÇÕES DO PRODUTO:
{product_description}

FORMATO OBRIGATÓRIO (siga EXATAMENTE este formato):
**{{NOME DO PRODUTO}} – {{DIFERENCIAL CURTO}}**

**{{FRASE DE IMPACTO / BENEFÍCIO PRINCIPAL}}**

{{CARACTERÍSTICA 1}}
{{CARACTERÍSTICA 2}}
{{ONDE / COMO USAR}}
{{IDEIA DE PRESENTE / OCASIÃO}}

💰 DE **R${{PREÇO_ANTIGO}}** POR APENAS **R${{PREÇO_ATUAL}}**
🎟️ {{INFORMAÇÃO DE CUPOM / % DE DESCONTO}}

🛒 Encontre na {{LOJA / PLATAFORMA}}:
👉 {{LINK DO PRODUTO}}

INSTRUÇÕES:
1. Use as informações fornecidas para preencher cada campo
2. Seja persuasivo e criativo
3. Mantenha o formato EXATAMENTE como mostrado
4. Use os preços e descontos reais do produto
5. Inclua o link real do produto
6. Crie 2-3 características principais marcantes
7. Sugira onde/como usar o produto
8. Se aplicável, sugira como presente ou ocasião especial

Gere APENAS o texto formatado, sem explicações adicionais."""
        
        formatted_output = gemini.generate_content(prompt) # Generate formatted marketing text
        
        if formatted_output: # If generation successful
            description_dir = os.path.dirname(description_file)  # Get directory of description file
            formatted_file = os.path.join(description_dir, f"{product_name_safe}_marketing.txt")  # Output file path
            gemini.write_output_to_file(formatted_output, formatted_file)  # Write output to file
            
            gemini.close()  # Close Gemini client
            return True  # Return success
        else:  # If generation failed
            print(f"{BackgroundColors.RED}Failed to generate formatted text.{Style.RESET_ALL}")
            gemini.close()  # Close Gemini client
            return False  # Return failure
        
    except Exception as e:  # If an error occurs during formatting
        print(f"{BackgroundColors.RED}Error during AI formatting: {e}{Style.RESET_ALL}")
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
    
    create_directory(
        os.path.abspath(OUTPUT_DIRECTORY), OUTPUT_DIRECTORY.replace(".", "")
    )  # Create the output directory
    
    successful_scrapes = 0  # Counter for successful operations
    total_urls = len(TEST_URLs)  # Total number of URLs to process
    
    for index, url in enumerate(TEST_URLs, 1):  # Iterate through all URLs
        print(f"{BackgroundColors.GREEN}Processing URL {BackgroundColors.CYAN}{index}{BackgroundColors.GREEN}/{BackgroundColors.CYAN}{total_urls}{BackgroundColors.GREEN}: {BackgroundColors.CYAN}{url}{Style.RESET_ALL}") # Print section header
        
        print(f"{BackgroundColors.CYAN}Step 1{BackgroundColors.GREEN}: Scraping the product information{Style.RESET_ALL}")  # Step 1: Scrape the product information
        product_data, description_file, product_name_safe = scrape_product(url)  # Scrape the product
        
        if not product_data:  # If scraping failed
            print(f"{BackgroundColors.RED}Skipping URL due to scraping failure.{Style.RESET_ALL}\n")
            continue  # Move to next URL
        
        try:  # Read the product description from the file
            with open(str(description_file), "r", encoding="utf-8") as f:  # Open the description file with UTF-8 encoding
                product_description = f.read()  # Read the product description
        except Exception as e:  # If reading the file fails
            print(f"{BackgroundColors.RED}Error reading description file: {e}{Style.RESET_ALL}")
            continue  # Move to next URL
        
        print(f"{BackgroundColors.CYAN}Step 2{BackgroundColors.GREEN}: Formatting with Gemini AI{Style.RESET_ALL}")  # Step 2: Format the product description with Gemini AI
        success = generate_marketing_text(product_description, product_name_safe, description_file)  # Generate marketing text
        
        if success:  # If both scraping and formatting succeeded
            successful_scrapes += 1  # Increment successful scrapes counter
    
    print(f"{BackgroundColors.GREEN}Successfully processed: {BackgroundColors.CYAN}{successful_scrapes}/{total_urls}{BackgroundColors.GREEN} URLs{Style.RESET_ALL}\n")  # Output the number of successful operations

    finish_time = datetime.datetime.now()  # Get the finish time of the program
    print(
        f"{BackgroundColors.GREEN}Start time: {BackgroundColors.CYAN}{start_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Finish time: {BackgroundColors.CYAN}{finish_time.strftime('%d/%m/%Y - %H:%M:%S')}\n{BackgroundColors.GREEN}Execution time: {BackgroundColors.CYAN}{calculate_execution_time(start_time, finish_time)}{Style.RESET_ALL}"
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
