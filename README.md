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
