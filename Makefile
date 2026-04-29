# Variables
VENV := venv
OS := $(shell uname 2>/dev/null || echo Windows)

# Detect correct Python and Pip commands based on OS
ifeq ($(OS), Windows) # Windows
	PYTHON := $(VENV)/Scripts/python.exe
	PIP := $(VENV)/Scripts/pip.exe
	PYTHON_CMD := python
	CLEAR_CMD := cls
	TIME_CMD :=
else # Unix-like
	PYTHON := $(VENV)/bin/python3
	PIP := $(VENV)/bin/pip
	PYTHON_CMD := python3
	CLEAR_CMD := clear
	TIME_CMD := time
endif

# Logs directory
LOG_DIR := ./Logs

# Ensure logs directory exists (cross-platform)
ENSURE_LOG_DIR := @mkdir -p $(LOG_DIR) 2>/dev/null || $(PYTHON_CMD) -c "import os; os.makedirs('$(LOG_DIR)', exist_ok=True)"

# Run-and-log function
# On Windows: simply runs the Python script normally
# On Unix-like systems: supports DETACH variable
#   - If DETACH is set, runs the script in detached mode and tails the log file
#   - Else, runs the script normally
ifeq ($(OS), Windows) # Windows
RUN_AND_LOG = $(PYTHON) $(1)
else
# Single-line shell form to avoid line-continuation/backslash issues in recipes
RUN_AND_LOG = if [ -z "$(DETACH)" ]; then $(PYTHON) $(1); else LOG_FILE=$(LOG_DIR)/$$(basename $(1) .py).log; nohup $(PYTHON) $(1) > $$LOG_FILE 2>&1 & tail -f $$LOG_FILE; fi
endif

# Default target
all: run

run: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./Scripts/affiliate_pages_downloader.py --headerless True $(ARGS))
	$(call RUN_AND_LOG, ./compressed_archives_renamer.py $(ARGS))
	$(call RUN_AND_LOG, ./main.py --headerless True --sort_products_by_product_name True $(ARGS))

local: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./compressed_archives_renamer.py $(ARGS))
	$(call RUN_AND_LOG, ./main.py --sort_products_by_product_name True $(ARGS))

# Execute the main script with logging and updated dependency management
main: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./main.py --sort_products_by_product_name True $(ARGS))

sort_products: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
ifeq ($(OS), Windows)
	@if not defined OUTPUT_DIR ( \
		echo ERROR: OUTPUT_DIR variable must be set. Example: make sort_products OUTPUT_DIR=Outputs/1. 2026-04-14 - 07h31m39s && exit 1 \
	)
else
	@if [ "$(OUTPUT_DIR)" = "" ]; then \
		echo "ERROR: OUTPUT_DIR variable must be set. Example: make sort_products OUTPUT_DIR=Outputs/1.\ 2026-04-14\ -\ 07h31m39s"; \
		exit 1; \
	fi
endif
	$(call RUN_AND_LOG, ./main.py --sort_products_by_product_name True --output_dir "$(OUTPUT_DIR)")

generate_template_files_from_local: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./main.py --generate_template_files_from_local True $(ARGS))

sort_latest_products: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./main.py --sort_products_by_product_name True --output_dir Default $(ARGS))

merge_output_dirs: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./main.py --merge_output_dirs True $(ARGS))

compressed_archives_renamer: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./compressed_archives_renamer.py $(ARGS))

urls_input_file_adder: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./urls_input_file_adder.py $(ARGS))

affiliate_pages_downloader: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./Scripts/affiliate_pages_downloader.py $(ARGS))

affiliate_pages_downloader_only_renew_amazon_urls: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./Scripts/affiliate_pages_downloader.py --only-renew-amazon-urls true $(ARGS))

# Update repository and run
update_and_run: dependencies
	@echo "Updating repository: reset to HEAD and pulling latest changes..."
	@git reset --hard HEAD
	@git pull --ff-only || git pull
	run

# Create virtual environment if missing
$(VENV):
	@echo "Creating virtual environment..."
	$(PYTHON_CMD) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip

dependencies: $(VENV)
	@echo "Installing/Updating Python dependencies..."
	$(PIP) install -r requirements.txt

# Install Playwright + browser binaries inside venv
install_playwright: dependencies
	@echo "Installing Playwright..."
	$(PIP) install playwright
	@echo "Installing Playwright browser binaries..."
	$(PYTHON) -m playwright install

# Generate requirements.txt from current venv
generate_requirements: $(VENV)
	$(PIP) freeze > requirements.txt

# Clean artifacts
clean:
	rm -rf $(VENV) || rmdir /S /Q $(VENV) 2>nul
	find . -type f -name '*.pyc' -delete || del /S /Q *.pyc 2>nul
	find . -type d -name '__pycache__' -delete || rmdir /S /Q __pycache__ 2>nul

.PHONY: all run local main sort_products generate_template_files_from_local sort_latest_products merge_output_dirs compressed_archives_renamer urls_input_file_adder affiliate_pages_downloader affiliate_pages_downloader_only_renew_amazon_urls update_and_run clean dependencies generate_requirements