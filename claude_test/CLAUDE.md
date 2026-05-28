# Core Commands
- Run test suite: `pytest`
- Run single test file: `pytest tests/test_filename.py`
- Code formatting check: `black --check .`
- Code linting & type check: `ruff check .` and `mypy .`

# Python Code Style & Rules
- **Python Version:** Target Python 3.10+ utilizing modern syntax.
- **Type Hinting:** Mandatory explicit type hints for all function arguments and return values (e.g., `def calculate_metric(data: list[int]) -> float:`).
- **Testing:** Always use `pytest` with clean fixtures. Avoid `unittest` class-based structures.
- **Error Handling:** Be explicit. Never use bare `except:` blocks; always catch specific exceptions (e.g., `except KeyError:`) and log errors cleanly.
- **Docstrings:** Use Google-style docstrings for public modules and complex functions.

# Agent Guardrails & Etiquette
- **Think First:** Before editing or creating any file, output a brief 2-3 sentence markdown bulleted list outlining your planned changes and why you are choosing that approach.
- **Surgical Edits:** Favor precise, targeted edits to existing files. Do not rewrite an entire file if modifying 5 lines accomplishes the goal.
- **Verification:** Automatically run the `pytest` suite after completing any code changes to verify nothing was broken. If tests fail, iterate and fix them autonomously.
