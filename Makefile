.PHONY: install test lint clean build

install:
	pip install -e .[test]

test:
	pytest tests/ -v

lint:
	python -m compileall src/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:
	python -m build

binary:
	pyinstaller aicoder.spec --clean -y
