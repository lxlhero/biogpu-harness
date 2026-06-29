#!/usr/bin/env python3
"""Validate a YAML or JSON file against a JSON Schema."""

import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    print(json.dumps({"status": "error", "errors": ["PyYAML not installed"]}))
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    print(json.dumps({"status": "error", "errors": ["jsonschema not installed: pip install jsonschema"]}))
    sys.exit(2)


def load_file(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path) as f:
        if ext in (".yaml", ".yml"):
            return yaml.safe_load(f)
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Validate a YAML/JSON file against a JSON Schema")
    parser.add_argument("--schema", required=True, help="Path to JSON Schema file")
    parser.add_argument("--file",   required=True, help="Path to YAML or JSON file to validate")
    args = parser.parse_args()

    try:
        schema = json.load(open(args.schema))
    except FileNotFoundError:
        print(json.dumps({"status": "error", "file": args.file, "errors": [f"schema not found: {args.schema}"]}))
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"status": "error", "file": args.file, "errors": [f"failed to parse schema: {e}"]}))
        sys.exit(2)

    try:
        data = load_file(args.file)
    except FileNotFoundError:
        print(json.dumps({"status": "error", "file": args.file, "errors": [f"file not found: {args.file}"]}))
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"status": "error", "file": args.file, "errors": [f"failed to parse file: {e}"]}))
        sys.exit(2)

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        out = {"status": "pass", "schema": args.schema, "file": args.file, "errors": []}
        print(json.dumps(out, indent=2))
        sys.exit(0)

    error_list = []
    for e in errors:
        path = ".".join(str(p) for p in e.path) if e.path else "(root)"
        error_list.append({"path": path, "message": e.message})

    out = {"status": "fail", "schema": args.schema, "file": args.file, "errors": error_list}
    print(json.dumps(out, indent=2))
    sys.exit(1)


if __name__ == "__main__":
    main()
