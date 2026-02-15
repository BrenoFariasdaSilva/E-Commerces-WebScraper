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

# Make Rules
run: dependencies
	$(ENSURE_LOG_DIR)
	$(CLEAR_CMD)
	$(call RUN_AND_LOG, ./main.py)

# Update repository and run
run_updated:
	@echo "Updating repository: reset to HEAD and pulling latest changes..."
	@git reset --hard HEAD
	@git pull --ff-only || git pull
	run

# Create virtual environment if missing
$(VENV):
	@echo "Creating virtual environment..."
	$(PYTHON_CMD) -m venv $(VENV)
	$(PIP) install --upgrade pip

dependencies: $(VENV)
	@echo "Installing/Updating Python dependencies..."
	$(PIP) install -r requirements.txt

# Generate requirements.txt from current venv
generate_requirements: $(VENV)
	$(PIP) freeze > requirements.txt

# Clean artifacts
clean:
	rm -rf $(VENV) || rmdir /S /Q $(VENV) 2>nul
	find . -type f -name '*.pyc' -delete || del /S /Q *.pyc 2>nul
	find . -type d -name '__pycache__' -delete || rmdir /S /Q __pycache__ 2>nul

.PHONY: all run run_updated clean dependencies generate_requirements