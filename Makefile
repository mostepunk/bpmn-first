# BPMN-First Makefile
# Usage:
#   make run        - Run the web server (create venv if needed)
#   make run PORT=9000  - Run on custom port
#   make setup      - Force recreate venv and install deps
#   make clean      - Remove venv

# Default port
PORT ?= 8000

# Python executable
PYTHON = python3

# Virtual environment path
VENV = venv

# Check if venv exists
VENV_EXISTS := $(shell test -d $(VENV) && echo 1 || echo 0)

.PHONY: run setup clean

# Run server: create venv if needed, then start uvicorn
run:
ifeq ($(VENV_EXISTS),0)
	@echo "=== Virtual environment not found. Setting up... ==="
	$(PYTHON) -m venv $(VENV)
	@echo "=== Installing dependencies... ==="
	$(VENV)/bin/pip install -r requirements.txt
	@echo "=== Setup complete. Starting server... ==="
else
	@echo "=== Virtual environment found. Starting server... ==="
endif
	$(VENV)/bin/uvicorn app:app --host 0.0.0.0 --port $(PORT)

# Force recreate venv and install dependencies
setup:
	@echo "=== Removing old venv (if exists)... ==="
	rm -rf $(VENV)
	@echo "=== Creating new virtual environment... ==="
	$(PYTHON) -m venv $(VENV)
	@echo "=== Installing dependencies... ==="
	$(VENV)/bin/pip install -r requirements.txt
	@echo "=== Setup complete. Run 'make run' to start server ==="

# Clean: remove venv
clean:
	@echo "=== Removing virtual environment... ==="
	rm -rf $(VENV)
	@echo "=== Clean complete ==="
