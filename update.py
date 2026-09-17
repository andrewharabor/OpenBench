#!/usr/bin/env python3
"""Update C++ TUNABLE and TUNABLE_CALLBACK values from a parameter list.

Input format: one parameter per line, as:

    TT_REPLACE_DEPTH_OFFSET, 615
    TT_REPLACE_PV_SCALE, 255
    TT_QUALITY_DEPTH_SCALE, 130
    TT_QUALITY_AGE_DIFF_SCALE, 213
    SEE_PAWN_VALUE, 91

Blank lines and lines beginning with "#" are ignored.

Usage:
    uv run python update.py final.txt tunable.cpp -o tunable.cpp

The script changes only the value (the second macro argument) for parameter
names that appear in the parameter file. All other source text is retained
exactly.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

# Matches either of these forms:
#   TUNABLE(name, value, min, max)
#   TUNABLE_CALLBACK(name, value, min, max, callback)
#
# It captures only the parts required to replace the second argument. The
# suffix intentionally includes all later macro arguments unchanged.
TUNABLE_RE = re.compile(
    r"(?P<prefix>\bTUNABLE(?:_CALLBACK)?\s*\(\s*)"
    r"(?P<name>[A-Za-z_]\w*)"
    r"(?P<before_value>\s*,\s*)"
    r"(?P<value>[^,\r\n]+)"
    r"(?P<suffix>\s*,[^\r\n]*\))"
)

PARAMETER_NAME_RE = re.compile(r"^[A-Za-z_]\w*$")


def rounded_int(value: Any, parameter_name: str) -> int:
    """Validate a numeric value and round it for C++ output."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Parameter {parameter_name!r} has a non-numeric value: {value!r}"
        )

    if not math.isfinite(value):
        raise ValueError(
            f"Parameter {parameter_name!r} has a non-finite value: {value!r}"
        )

    return int(round(value))


def load_values(parameter_path: Path) -> dict[str, int]:
    """Load comma-separated NAME, VALUE entries into a name-to-value mapping."""
    values: dict[str, int] = {}

    with parameter_path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if "," not in line:
                raise ValueError(
                    f"Line {line_number} must use the format NAME, VALUE: "
                    f"{raw_line.rstrip()!r}"
                )

            name_text, value_text = line.split(",", maxsplit=1)
            name = name_text.strip()
            value_text = value_text.strip()

            if not PARAMETER_NAME_RE.fullmatch(name):
                raise ValueError(
                    f"Line {line_number} has an invalid parameter name: {name!r}"
                )

            if not value_text:
                raise ValueError(
                    f"Line {line_number} ({name!r}) has no value."
                )

            if name in values:
                raise ValueError(
                    f"Duplicate parameter name on line {line_number}: {name!r}"
                )

            try:
                value = float(value_text)
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_number} ({name!r}) has an invalid numeric value: "
                    f"{value_text!r}"
                ) from exc

            values[name] = rounded_int(value, name)

    return values


def update_source(source: str, values: dict[str, int]) -> tuple[str, set[str]]:
    """Replace only values for matching parameter names in supported macros."""
    found: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name not in values:
            return match.group(0)

        found.add(name)
        return (
            match.group("prefix")
            + name
            + match.group("before_value")
            + str(values[name])
            + match.group("suffix")
        )

    return TUNABLE_RE.sub(replace, source), found


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replace TUNABLE and TUNABLE_CALLBACK values using a "
            "comma-separated NAME, VALUE parameter list."
        )
    )
    parser.add_argument(
        "parameter_file",
        type=Path,
        help="Path to the parameter list file containing NAME, VALUE lines",
    )
    parser.add_argument(
        "cpp_file",
        type=Path,
        help="Path to the input C++ source file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Path for the updated C++ output file",
    )
    args = parser.parse_args()

    values = load_values(args.parameter_file)
    source = args.cpp_file.read_text(encoding="utf-8")
    updated_source, found = update_source(source, values)
    args.output.write_text(updated_source, encoding="utf-8")

    print(f"Updated {len(found)} declaration(s): {args.output}")

    missing = sorted(set(values) - found)
    if missing:
        print("Warning: parameters not found in the C++ source:")
        for name in missing:
            print(f"  {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
