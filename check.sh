#! /bin/sh

for cmd in black ruff mypy; do
    poetry run "$cmd" remarshal.py tests/*.py
done
