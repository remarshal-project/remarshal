# Remarshal, a utility to convert between serialization formats.
# Copyright (c) 2026 D. Bohdan
# License: MIT

"""Poe the Poet tasks for Remarshal."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START_MARKER = "<!-- USAGE -->"
END_MARKER = "<!-- END USAGE -->"
WIDTH = 80


def _fold_s(text: str, width: int = WIDTH) -> str:
    """Reproduce `fold -s -w <width>` with stripped whitespace on the right.
    Break at the rightmost space that fits."""
    out: list[str] = []

    for raw in text.splitlines():
        line = raw

        while len(line) > width:
            cut = line.rfind(" ", 0, width)

            if cut == -1:
                out.append(line[:width])
                line = line[width:]
            else:
                out.append(line[: cut + 1])
                line = line[cut + 1 :]

        out.append(line.rstrip())

    return "\n".join(out)


def _capture_help() -> str:
    env = {**os.environ, "COLUMNS": str(WIDTH), "NO_COLOR": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "remarshal", "--help"],
        capture_output=True,
        check=True,
        env=env,
        text=True,
    )

    return result.stdout


def update_readme() -> None:
    """Replace the `<!-- USAGE -->...<!-- END USAGE -->` block in README.md."""
    help_text = _fold_s(_capture_help()).rstrip("\n")
    block = f"{START_MARKER}\n```none\n{help_text}\n```\n{END_MARKER}"

    contents = README.read_text(encoding="utf-8")
    start = contents.find(START_MARKER)
    end = contents.find(END_MARKER)

    if start == -1 or end == -1 or end < start:
        msg = f"could not find '{START_MARKER}' ... '{END_MARKER}' in {README}"
        raise SystemExit(msg)

    new = contents[:start] + block + contents[end + len(END_MARKER) :]

    if new != contents:
        README.write_text(new, encoding="utf-8")
        print(f"Updated {README.name}")
    else:
        print(f"{README.name} is already up to date")
