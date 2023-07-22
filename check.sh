#! /bin/sh

poetry run black remarshal.py tests/*.py
poetry run ruff remarshal.py tests/*.py
poetry run mypy --strict remarshal.py tests/*.py
