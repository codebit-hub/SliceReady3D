# Define the virtual environment directory path outside the current repository
VENV = ../.venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# This is the timestamp marker file
MARKER = $(VENV)/.installed

.PHONY: all install run lint clean

all: install

# Step 1: Install Target
# Now relies on the marker file instead of running unconditionally
install: $(MARKER)

# The actual installation logic. It only triggers if requirements.txt is newer
# than the MARKER, or if the MARKER doesn't exist.
$(MARKER): requirements.txt
	@echo "Creating virtual environment outside the repository at $(VENV)..."
	python3 -m venv $(VENV)
	@echo "Upgrading pip inside the external environment..."
	$(PIP) install --upgrade pip
	@echo "Installing project dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@echo "Marking installation as complete..."
	@touch $(MARKER)
	@echo "Installation complete. Environment is completely isolated."

# Step 2: Run Target
run:
	@echo "Starting SliceReady3D development server..."
	$(VENV)/bin/uvicorn src.main:app --reload

# Step 3: Lint Target
lint:
	@echo "Running Flake8 style compliance checks..."
	$(VENV)/bin/flake8 src/
	@echo "Running MyPy strict static type validation..."
	$(VENV)/bin/mypy src/

# Step 4: Clean Target
clean:
	@echo "Removing external virtual environment..."
	rm -rf $(VENV)
	@echo "Purging local Python cache directories..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup complete."
