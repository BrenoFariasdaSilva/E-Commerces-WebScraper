<div align="center">
  
# [E-Commerces-WebScraper.](https://github.com/BrenoFariasdaSilva/E-Commerces-WebScraper) <img src="https://github.com/BrenoFariasdaSilva/E-Commerces-WebScraper/blob/main/.assets/Icons/web-scraper.png"  width="4%" height="4%">

</div>

<div align="center">
  
---

A production-ready web scraper for extracting product information from multiple e-commerce platforms with authenticated session support, intelligent path resolution, batch processing, and AI-powered marketing content generation.
  
---

</div>

<div align="center">

![GitHub Code Size in Bytes](https://img.shields.io/github/languages/code-size/BrenoFariasdaSilva/E-Commerces-WebScraper)
![GitHub Commits](https://img.shields.io/github/commit-activity/t/BrenoFariasDaSilva/E-Commerces-WebScraper/main)
![GitHub Last Commit](https://img.shields.io/github/last-commit/BrenoFariasdaSilva/E-Commerces-WebScraper)
![GitHub Forks](https://img.shields.io/github/forks/BrenoFariasDaSilva/E-Commerces-WebScraper)
![GitHub Language Count](https://img.shields.io/github/languages/count/BrenoFariasDaSilva/E-Commerces-WebScraper)
![GitHub License](https://img.shields.io/github/license/BrenoFariasdaSilva/E-Commerces-WebScraper)
![GitHub Stars](https://img.shields.io/github/stars/BrenoFariasdaSilva/E-Commerces-WebScraper)
![GitHub Contributors](https://img.shields.io/github/contributors/BrenoFariasdaSilva/E-Commerces-WebScraper)
![GitHub Created At](https://img.shields.io/github/created-at/BrenoFariasdaSilva/E-Commerces-WebScraper)
![wakatime](https://wakatime.com/badge/github/BrenoFariasdaSilva/E-Commerces-WebScraper.svg)

</div>

<div align="center">
  
![RepoBeats Statistics](https://repobeats.axiom.co/api/embed/09e9fa0d7bef614ea753a5312bcf3612a4f12a8c.svg "Repobeats analytics image")

</div>

## Table of Contents
- [E-Commerces-WebScraper. ](#e-commerces-webscraper-)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Supported Platforms](#supported-platforms)
  - [Architecture](#architecture)
    - [Core Components](#core-components)
    - [Workflow](#workflow)
    - [Authentication Flow (Shopee/Shein)](#authentication-flow-shopeeshein)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
    - [Environment Variables](#environment-variables)
      - [Variable Descriptions](#variable-descriptions)
    - [Browser Profile Setup for Authenticated Scraping](#browser-profile-setup-for-authenticated-scraping)
  - [Usage](#usage)
    - [Basic Usage](#basic-usage)
    - [Input File Format](#input-file-format)
    - [Batch Processing](#batch-processing)
    - [Offline Scraping](#offline-scraping)
      - [Path Resolution](#path-resolution)
  - [Authenticated Scraping](#authenticated-scraping)
    - [How Authentication Works](#how-authentication-works)
    - [Setup Steps](#setup-steps)
  - [Output Structure](#output-structure)
    - [Description File Format](#description-file-format)
  - [AI-Powered Marketing Content](#ai-powered-marketing-content)
  - [Dependencies](#dependencies)
  - [File Structure](#file-structure)
  - [Implementation Details](#implementation-details)
    - [Platform Detection](#platform-detection)
    - [Path Resolution](#path-resolution-1)
    - [Image Processing](#image-processing)
    - [Browser Automation](#browser-automation)
  - [Troubleshooting](#troubleshooting)
  - [Performance Considerations](#performance-considerations)
  - [Ethical Considerations](#ethical-considerations)
  - [Contributing](#contributing)
    - [Quick Contribution Guide](#quick-contribution-guide)
  - [Collaborators](#collaborators)
  - [License](#license)

## Introduction

**E-Commerces-WebScraper** is a comprehensive, production-ready Python application designed to automate the extraction of product information from multiple e-commerce platforms. Built with maintainability and extensibility in mind, it supports both traditional HTTP scraping and advanced authenticated browser automation for JavaScript-heavy websites.

The scraper extracts detailed product data including names, prices, discount information, descriptions, and high-resolution images. It features intelligent duplicate detection, asset optimization, batch processing capabilities, and optional AI-powered marketing content generation via Google Gemini.

## Features

- **Multi-Platform Support**: Scrapes Mercado Livre, Shein, and Shopee with dedicated, platform-specific scrapers
- **Authenticated Scraping**: Uses existing Chrome profiles to bypass login requirements for Shopee and Shein
- **Intelligent Path Resolution**: Automatically resolves local HTML paths with multiple fallback strategies
- **Batch Processing**: Process multiple URLs from input files with configurable delays between requests
- **Offline Scraping**: Support for scraping from local HTML files and zip archives
- **Image Optimization**: Automatic duplicate detection and removal of low-quality images
- **Asset Localization**: Downloads and localizes external assets (images, CSS, JavaScript)
- **AI Integration**: Optional marketing content generation using Google Gemini API
- **Comprehensive Logging**: Detailed logs for all operations with timestamp tracking
- **Error Recovery**: Robust exception handling with detailed error reporting
- **Platform-Specific Output**: Organized directory structure with platform prefixes
- **Product Validation**: Validates scraped data to filter out placeholder entries

## Supported Platforms

| Platform          | Scraping Method                 | Authentication Required | Status   |
| ----------------- | ------------------------------- | ----------------------- | -------- |
| **Mercado Livre** | HTTP Requests                   | No                      | ✅ Active |
| **Shein**         | Browser Automation (Playwright) | Yes                     | ✅ Active |
| **Shopee**        | Browser Automation (Playwright) | Yes                     | ✅ Active |

## Architecture

The application follows a modular, class-based architecture with clear separation of concerns:

### Core Components

- **main.py**: Orchestration layer that handles URL routing, batch processing, validation, and output management
- **MercadoLivre.py**: HTTP-based scraper using `requests` and `BeautifulSoup` for static content extraction
- **Shein.py**: Browser automation scraper using `Playwright` for JavaScript-rendered pages
- **Shopee.py**: Browser automation scraper using `Playwright` for JavaScript-rendered pages
- **Gemini.py**: AI integration module for generating marketing content via Google Gemini API
- **Logger.py**: Custom logging utility for simultaneous terminal and file output

### Workflow

1. **URL Loading**: Reads URLs from `Inputs/urls.txt` or test constants
2. **Platform Detection**: Analyzes URL patterns to determine the appropriate scraper
3. **Path Resolution**: Resolves local HTML paths with fallback mechanisms for offline scraping
4. **Scraping Execution**: Invokes platform-specific scraper with appropriate parameters
5. **Data Validation**: Verifies product data completeness and authenticity
6. **Asset Processing**: Downloads images, removes duplicates, excludes small files
7. **Output Generation**: Creates organized directories with product descriptions
8. **AI Enhancement**: Optionally generates marketing content via Gemini API
9. **Cleanup**: Removes temporary files and extracted archives

### Authentication Flow (Shopee/Shein)

```
User Authentication (One-time)
  ↓
Chrome Profile Creation
  ↓
Session Cookies Saved
  ↓
Playwright Launches Chrome with Profile
  ↓
Automatic Authentication via Cookies
  ↓
Page Rendering with JavaScript
  ↓
Content Extraction
```

## Requirements

- **Python**: >= 3.8
- **Operating System**: Windows, macOS, or Linux
- **Chrome Browser**: Required for authenticated scraping (Shopee/Shein)
- **Internet Connection**: Required for online scraping and AI features
- **Google Gemini API Key**: Optional, for AI-powered marketing content generation

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/BrenoFariasDaSilva/E-Commerces-WebScraper.git
   cd E-Commerces-WebScraper
   ```

2. **Create Virtual Environment** (Recommended)

   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright Browsers** (Required for Shopee/Shein)

   ```bash
   python -m playwright install chromium
   ```

5. **Configure Environment Variables**

   Create a `.env` file in the project root (see [Configuration](#configuration) section).

## Configuration

### Environment Variables

Create a `.env` file in the project root directory:

```env
# AI Integration (Optional - for marketing content generation)
GEMINI_API_KEY=your_gemini_api_key_here

# Browser Authentication (Required for Shopee and Shein)
CHROME_PROFILE_PATH=C:/Users/YourUsername/AppData/Local/Google/Chrome/User Data
CHROME_EXECUTABLE_PATH=
HEADLESS=False
```

#### Variable Descriptions

**GEMINI_API_KEY** (Optional)
- Google Gemini API key for AI-powered marketing content generation
- Obtain from: https://makersuite.google.com/app/apikey
- Leave empty to skip AI content generation

**CHROME_PROFILE_PATH** (Required for Shopee/Shein)
- Path to your Chrome user data directory with authenticated sessions
- **Windows**: `C:/Users/YourUsername/AppData/Local/Google/Chrome/User Data`
- **macOS**: `/Users/YourUsername/Library/Application Support/Google/Chrome`
- **Linux**: `/home/YourUsername/.config/google-chrome`
- ⚠️ Use forward slashes `/` even on Windows
- ⚠️ Close all Chrome windows before running the scraper

**CHROME_EXECUTABLE_PATH** (Optional)
- Path to Chrome executable if not in default location
- Leave empty if Chrome is installed in the standard location

**HEADLESS** (Optional)
- `False`: Show browser window (recommended for debugging)
- `True`: Run browser in background without window

### Browser Profile Setup for Authenticated Scraping

For Shopee and Shein scraping, you must authenticate once in your regular Chrome browser:

1. Open Google Chrome normally
2. Navigate to https://shopee.com.br and https://br.shein.com
3. Log into both websites with your credentials
4. Verify you can access product pages while logged in
5. Close all Chrome windows completely
6. Configure `CHROME_PROFILE_PATH` in `.env` file
7. Run the scraper - it will automatically use your saved sessions

The scraper will reuse your authenticated session without requiring credentials in the code.

## Usage

### Basic Usage

1. **Add URLs to Input File**

   Edit `Inputs/urls.txt` and add one URL per line:

   ```
   https://mercadolivre.com.br/product-url
   https://br.shein.com/product-url
   https://shopee.com.br/product-url
   ```

2. **Run the Scraper**

   ```bash
   python main.py
   ```

   Or using Make:

   ```bash
   make run
   ```

3. **Check Outputs**

   Results are saved in `Outputs/` directory organized by platform and product name.

### Input File Format

The `Inputs/urls.txt` file supports two formats per line:

**Online Scraping (URL only)**:
```
https://mercadolivre.com.br/product-url
```

**Offline Scraping (URL + Local HTML Path)**:
```
https://shopee.com.br/product-url ./Inputs/shopee-product/index.html
```

The scraper automatically detects which format is provided and routes accordingly.

### Batch Processing

Process multiple products in sequence with automatic delay:

```python
# In main.py
DELAY_BETWEEN_REQUESTS = 5  # Seconds between requests (default: 5)
```

The scraper processes all URLs in `Inputs/urls.txt` with rate limiting to avoid triggering anti-bot measures.

### Offline Scraping

The scraper supports offline scraping from local HTML files or zip archives:

**From HTML File**:
```
https://product-url ./Inputs/product-directory/index.html
```

**From Zip Archive**:
```
https://product-url ./Inputs/product-archive.zip
```

The scraper will:
1. Extract zip files to temporary directories
2. Scrape product information from local HTML
3. Copy associated assets (images, scripts, styles)
4. Clean up temporary files after processing

#### Path Resolution

The scraper includes intelligent path resolution with multiple fallback strategies:

If a path like `product-dir/index.html` is specified but not found, it automatically tries:
1. Original path as provided
2. With `./Inputs/` prefix
3. With `.zip` suffix
4. With `/index.html` suffix
5. All combinations of prefixes and suffixes
6. Base directory extraction for `.html` files

This ensures maximum flexibility in specifying input paths.

## Authenticated Scraping

Shopee and Shein require JavaScript rendering and authenticated sessions. The scraper uses Playwright browser automation with existing Chrome profiles.

### How Authentication Works

Instead of storing credentials or automating logins, the scraper:

1. Reuses your existing Chrome profile with saved cookies
2. Launches Chrome with `--user-data-dir` pointing to your profile
3. Inherits authentication automatically from saved session cookies
4. No credentials stored in code or configuration files
5. Works with 2FA/MFA-enabled accounts

### Setup Steps

1. **Authenticate in Chrome** (One-time)
   - Open Chrome normally
   - Log into Shopee and Shein
   - Verify access to product pages
   - Close all Chrome windows

2. **Configure Environment**
   ```env
   CHROME_PROFILE_PATH=C:/Users/YourUsername/AppData/Local/Google/Chrome/User Data
   HEADLESS=False
   ```

3. **Run Scraper**
   ```bash
   python main.py
   ```

The browser will launch with your authenticated profile and scrape products automatically.

## Output Structure

Each scraped product generates the following structure:

```
Outputs/
└── {Platform} - {Product Name}/
    ├── {Product Name}_description.txt          # Product details in template format
    ├── {Product Name}_Template.txt             # AI-generated marketing content (optional)
    ├── image_1.webp                            # High-resolution product images
    ├── image_2.webp
    ├── ...
    └── page.html                               # Complete page snapshot (Shopee/Shein only)
```

**Example**:
```
Outputs/
└── Shopee - Wireless Gaming Mouse/
    ├── Wireless Gaming Mouse_description.txt
    ├── Wireless Gaming Mouse_Template.txt
    ├── image_1.webp
    ├── image_2.webp
    └── page.html
```

### Description File Format

```
Product Name: Wireless Gaming Mouse

Price: From R$89.90 to R$149.90 (40% OFF)

Description: High-precision wireless gaming mouse with RGB lighting...

🛒 Encontre na Shopee:
👉 https://shopee.com.br/product-url
```

## AI-Powered Marketing Content

When `GEMINI_API_KEY` is configured, the scraper automatically generates marketing content for each product.

**Generated Content Includes**:
- Professional product descriptions
- Key feature highlights
- Usage scenarios
- Target audience recommendations
- Call-to-action text

**Output**: `{Product Name}_Template.txt` in the product directory.

**Processing**:
- Automatically triggered after successful scrape
- Validates and fixes formatting issues
- Retries on failures with error logging

## Dependencies

The project uses the following production dependencies:

**Core Libraries**:
- `beautifulsoup4==4.14.3` - HTML parsing and extraction
- `requests==2.32.5` - HTTP requests for web scraping
- `lxml==5.3.0` - Fast XML/HTML parsing backend

**Browser Automation**:
- `playwright==1.49.1` - Headless browser automation framework
- `pyee==12.0.0` - Event emitter for Playwright
- `greenlet==3.1.1` - Asynchronous support for Playwright

**Image Processing**:
- `pillow==12.1.0` - Image processing and optimization

**AI Integration**:
- `google-genai==1.61.0` - Google Gemini API client
- `google-auth==2.48.0` - Google authentication
- `tenacity==9.1.2` - Retry logic for API calls

**Utilities**:
- `colorama==0.4.6` - Terminal color formatting
- `python-dotenv==1.2.1` - Environment variable management

**HTTP & Networking**:
- `httpx==0.28.1` - Modern HTTP client
- `httpcore==1.0.9` - Low-level HTTP transport
- `urllib3==2.6.3` - HTTP connection pooling
- `certifi==2026.1.4` - SSL certificate bundle

**Data Validation**:
- `pydantic==2.12.5` - Data validation using Python type hints
- `pydantic_core==2.41.5` - Core validation logic

For a complete list, see [requirements.txt](requirements.txt).

## File Structure

```
E-Commerces-WebScraper/
├── main.py                              # Main orchestration script
├── MercadoLivre.py                      # Mercado Livre scraper class
├── Shein.py                             # Shein scraper class
├── Shopee.py                            # Shopee scraper class
├── Gemini.py                            # AI integration module
├── Logger.py                            # Custom logging utility
├── requirements.txt                     # Python dependencies
├── Makefile                             # Build and run commands
├── .env                                 # Environment configuration (not tracked)
├── .env.example                         # Environment template
├── README.md                            # This file
├── AUTHENTICATED_SCRAPING_SETUP.md      # Detailed authentication guide
├── IMPLEMENTATION_SUMMARY.md            # Technical implementation details
├── CONTRIBUTING.md                      # Contribution guidelines
├── LICENSE                              # Apache 2.0 license
├── Inputs/                              # Input files directory
│   └── urls.txt                         # URLs to scrape
├── Outputs/                             # Scraped data output directory
│   └── {Platform} - {Product}/          # Product-specific directories
├── Logs/                                # Execution logs
│   └── main.log                         # Main script log file
└── .assets/                             # Project assets
    ├── Icons/                           # Icon files
    └── Sounds/                          # Notification sounds
```

## Implementation Details

### Platform Detection

The scraper automatically detects platforms by analyzing URL patterns:

```python
PLATFORMS_MAP = {
    "MercadoLivre": "mercadolivre",
    "Shein": "shein",
    "Shopee": "shopee",
}
```

Detection logic checks for platform-specific domain keywords in the URL and routes to the appropriate scraper class.

### Path Resolution

Intelligent path resolution with 6+ variation attempts:

1. Path as provided
2. With `./Inputs/` prefix
3. With `.zip` suffix
4. With `/index.html` suffix
5. All combinations of above
6. Base directory extraction for `.html` files

This ensures maximum user convenience when specifying local HTML paths.

### Image Processing

**Duplicate Detection**:
- Normalizes images to minimum dimensions
- Computes MD5 hash of resized versions
- Groups duplicates by hash
- Keeps highest resolution version
- Deletes lower resolution duplicates

**Size Filtering**:
- Removes images smaller than 2KB (configurable)
- Filters out thumbnails and placeholder images
- Ensures only high-quality images are retained

### Browser Automation

**Playwright Configuration**:
- Uses existing Chrome profile for authentication
- Waits for network idle before extraction
- Auto-scrolls to trigger lazy-loaded content
- Captures complete page snapshots with assets
- Localizes external resources for offline viewing

**Asset Collection**:
- Downloads images, CSS, JavaScript files
- Rewrites URLs to use local paths
- Saves complete page snapshot with dependencies

## Troubleshooting

**Issue**: `Unable to open user data directory`
- **Cause**: Chrome is already running with the same profile
- **Solution**: Close all Chrome windows and check Task Manager for lingering chrome.exe processes

**Issue**: `No product data extracted`
- **Cause**: Not logged in, website structure changed, or anti-bot detection
- **Solution**: Verify login status in Chrome, try with `HEADLESS=False`, check logs for selector errors

**Issue**: `playwright._impl._api_types.Error: Executable doesn't exist`
- **Cause**: Playwright browsers not installed
- **Solution**: Run `python -m playwright install chromium`

**Issue**: `Could not resolve local HTML path`
- **Cause**: Local HTML file or directory not found
- **Solution**: Verify file paths, ensure `./Inputs/` prefix is correct, check zip file integrity

**Issue**: `Rate limiting or IP blocking`
- **Cause**: Too many requests in short time
- **Solution**: Increase `DELAY_BETWEEN_REQUESTS` in main.py, use VPN if necessary

For more detailed troubleshooting, see [AUTHENTICATED_SCRAPING_SETUP.md](AUTHENTICATED_SCRAPING_SETUP.md).

## Performance Considerations

**Execution Speed**:
- **Mercado Livre**: ~5-10 seconds per product (HTTP requests)
- **Shopee/Shein**: ~15-30 seconds per product (browser automation with rendering)

**Resource Usage**:
- **CPU**: Moderate during image processing and hash computation
- **Memory**: ~500MB-1GB for browser automation
- **Disk**: Depends on image quantity and quality
- **Network**: Varies by product image count and asset size

**Optimization Tips**:
- Process large batches during off-peak hours
- Use `HEADLESS=True` for production runs
- Increase `DELAY_BETWEEN_REQUESTS` to avoid rate limiting
- Consider parallel execution for independent URLs (not implemented)

## Ethical Considerations

**Respect Website Policies**:
- Review and comply with each platform's Terms of Service
- Respect `robots.txt` directives
- Implement appropriate rate limiting
- Do not overload servers with excessive requests

**Data Usage**:
- Scraped data is for personal analysis and monitoring
- Do not republish copyrighted content without permission
- Respect intellectual property rights
- Use product information ethically and legally

**Authentication**:
- Only scrape content you have legitimate access to
- Do not share or expose authentication credentials
- Do not circumvent security measures
- Use authenticated scraping responsibly

**Anti-Bot Measures**:
- The scraper mimics normal user behavior
- Uses authenticated sessions to avoid detection
- Implements delays between requests
- Does not attempt to bypass CAPTCHAs or security challenges

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. If you have suggestions for improving the code, your insights will be highly welcome.

Please follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md) for detailed information about the commit standards and the entire pull request process.

### Quick Contribution Guide

1. **Set Up Your Environment**: Follow the [Installation](#installation) section

2. **Make Your Changes**:
   - Create a branch: `git checkout -b feature/YourFeatureName`
   - Implement your changes with tests
   - Commit with clear messages:
     - Features: `git commit -m "FEAT: Add some AmazingFeature"`
     - Bug fixes: `git commit -m "FIX: Resolve Issue #123"`
     - Documentation: `git commit -m "DOCS: Update README with new instructions"`
     - Refactoring: `git commit -m "REFACTOR: Enhance component for better aspect"`

3. **Submit Your Contribution**:
   - Push changes: `git push origin feature/YourFeatureName`
   - Open a Pull Request with detailed description

4. **Stay Engaged**: Respond to feedback and make necessary adjustments
