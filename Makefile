.PHONY: all install dev test serve mcp clean lint build

PYTHON ?= python3
PORT ?= 8088
HOST ?= 0.0.0.0

all: test

install:
	$(PYTHON) -m pip install .

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -v

serve:
	PYTHONPATH=src $(PYTHON) -m vision_gesture_control serve --port $(PORT) --host $(HOST) --open

mcp:
	PYTHONPATH=src $(PYTHON) -m vision_gesture_control mcp

lint:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ src/*.egg-info src/*/__pycache__ tests/__pycache__

build: clean
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build
