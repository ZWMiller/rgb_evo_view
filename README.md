# rgb_evo_view

_TODO: project description._

---

## Installation

```bash
# Install dependencies (requires Python 3.13+)
poetry install

# Install the pre-commit hooks
poetry run pre-commit install
```

---

## Development

```bash
# Run the test suite
poetry run pytest

# Run all pre-commit hooks across the repo
poetry run pre-commit run --all-files

# Regenerate API docs from docstrings (edit the module list in the script first)
poetry run bash scripts/generate_api_docs.sh
```

Documentation lives in [`docs/`](docs/): see [`docs/TECHNICAL_DOCS.md`](docs/TECHNICAL_DOCS.md)
for the technical reference and [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) for the history of
design decisions.
