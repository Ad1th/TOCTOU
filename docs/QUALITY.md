# Quality Checks

Run these commands from the repository root before submitting changes:

```bash
python -m pip install -e ".[dev]"
ruff check .
black --check .
mypy .
pytest
```

All production Python code uses Python 3.12+ syntax, complete type hints, module and public API docstrings, and structured logging where runtime events are emitted.
