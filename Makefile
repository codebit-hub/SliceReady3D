# Define the virtual environment directory path outside the current repository
VENV = ../.venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# This is the timestamp marker file
MARKER = $(VENV)/.installed

.PHONY: all install run lint clean fclean re

all: install

# Step 1: Install Target
# Relies on the marker file instead of running unconditionally
install: $(MARKER)

# The actual installation logic.
# It only triggers if requirements.txt is newer
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
# By adding 'install' as a dependency, this auto-installs if the user skipped Step 1.
run: install
	@echo "Starting SliceReady3D development server..."
	$(VENV)/bin/uvicorn src.main:app --reload

# Step 3: Lint Target
# Added 'install' dependency here as well for evaluator convenience.
lint: install
	@echo "Running Flake8 style compliance checks..."
	$(VENV)/bin/flake8 src/
	@echo "Running MyPy strict static type validation..."
	$(VENV)/bin/mypy src/

# Step 4: Clean Target
# Only removes intermediate cache files
clean:
	@echo "Purging local Python cache directories..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete."

# Step 5: Full Clean Target
# Removes cache files AND destroys the virtual environment
fclean: clean
	@echo "Removing external virtual environment..."
	rm -rf $(VENV)
	@echo "Full cleanup complete."

# Step 6: Rebuild Target
# Runs a full clean, then reinstalls everything
re: fclean all
