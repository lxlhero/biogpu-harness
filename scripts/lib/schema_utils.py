"""Shared schema validation helpers for BioGPU-Harness validators."""

import json
import os

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

try:
    import jsonschema
    _JSONSCHEMA_OK = True
except ImportError:
    _JSONSCHEMA_OK = False

_HARNESS_ROOT = os.path.normpath(
    os.environ.get("BIOGPU_HARNESS_ROOT",
                   os.path.join(os.path.dirname(__file__), "..", ".."))
)
_SCHEMAS_DIR = os.path.join(_HARNESS_ROOT, "schemas")


def load_yaml_or_json(path):
    """Load a YAML or JSON file and return the parsed object."""
    if not _YAML_OK:
        raise ImportError("PyYAML not installed")
    ext = os.path.splitext(path)[1].lower()
    with open(path) as f:
        if ext in (".yaml", ".yml"):
            return yaml.safe_load(f)
        return json.load(f)


def load_schema(schema_filename):
    """Load a schema JSON file from the schemas/ directory."""
    path = os.path.join(_SCHEMAS_DIR, schema_filename)
    with open(path) as f:
        return json.load(f)


def validate_against_schema(data, schema):
    """
    Validate data against a JSON Schema (Draft7).
    Returns a list of error dicts: [{"path": ..., "message": ...}, ...]
    Returns [] on pass.
    Raises RuntimeError if jsonschema is not installed.
    """
    if not _JSONSCHEMA_OK:
        raise RuntimeError("jsonschema not installed: pip install jsonschema")
    validator = jsonschema.Draft7Validator(schema)
    raw = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    return format_schema_errors(raw)


def format_schema_errors(raw_errors):
    """Convert jsonschema ValidationError objects to dicts."""
    result = []
    for e in raw_errors:
        path = ".".join(str(p) for p in e.path) if e.path else "(root)"
        result.append({"path": path, "message": e.message})
    return result
