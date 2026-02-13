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
