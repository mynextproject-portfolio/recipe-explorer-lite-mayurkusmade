#!/usr/bin/env python3
"""
Validate recipe JSON files against the Recipe Explorer schema.

Usage:
    python scripts/validate_schema.py
    python scripts/validate_schema.py path/to/recipes.json
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models import RecipeImport  # noqa: E402


def validate_recipe_file(file_path: Path) -> tuple[int, list[str]]:
    """Validate a JSON file containing an array of recipes."""
    errors: list[str] = []

    if not file_path.exists():
        return 0, [f"File not found: {file_path}"]

    try:
        with open(file_path, "r", encoding="utf-8") as recipe_file:
            data = json.load(recipe_file)
    except json.JSONDecodeError as error:
        return 0, [f"Invalid JSON: {error}"]

    if not isinstance(data, list):
        return 0, ["Top-level JSON value must be an array of recipe objects"]

    if len(data) == 0:
        return 0, ["Recipe array must contain at least one recipe"]

    valid_count = 0
    for index, recipe_data in enumerate(data):
        if not isinstance(recipe_data, dict):
            errors.append(f"Recipe at index {index} must be a JSON object")
            continue

        try:
            RecipeImport.model_validate(recipe_data)
            valid_count += 1
        except ValidationError as error:
            error_details = "; ".join(
                f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
                for err in error.errors()
            )
            errors.append(f"Recipe at index {index} failed validation: {error_details}")

    return valid_count, errors


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "sample-recipes.json"
    valid_count, errors = validate_recipe_file(target)

    print(f"Validating: {target}")
    print(f"Valid recipes: {valid_count}")

    if errors:
        print("Schema compliance errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Schema compliance check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
