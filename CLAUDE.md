# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Setup
- Create virtual environment: `python -m venv venv && source venv/bin/activate`
- Install requirements: `pip install -r scraper/requirements.txt`
- Setup browsers: `playwright install`

## Run Commands
- Execute scraper: `python scraper/main.py`
- Run tests: `python -m pytest scraper/tests/`
- Run single test: `python -m pytest scraper/tests/test_file.py::test_function`
- Check types: `mypy scraper/`
- Format code: `black scraper/`
- Lint code: `ruff scraper/`

## Code Style Guidelines
- Python 3.9+ with async/await patterns
- Formatting: Black (default settings)
- Linting: Ruff
- Type checking: MyPy with strict mode
- Imports: Sorted alphabetically, standard lib first, then third-party, then local
- Naming: snake_case for functions/variables, PascalCase for classes
- Error handling: Use try/except with specific exceptions, log errors
- Documentation: Docstrings for all public functions/classes (Google style)
- Log all errors with appropriate level (ERROR for recoverable, CRITICAL for fatal)