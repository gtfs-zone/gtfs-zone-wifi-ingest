"""Session schemas by version and validation against them."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from jsonschema import Draft202012Validator

if TYPE_CHECKING:
    from pathlib import Path

_NAME = re.compile(r"^session\.v(\d+)\.json$")
MAX_ERRORS = 10


class SessionSchemas:
    """Every `session.v<N>.json` in a directory, keyed by N."""

    def __init__(self, schema_dir: Path) -> None:
        self.validators: dict[int, Draft202012Validator] = {}
        for path in sorted(schema_dir.glob("session.v*.json")):
            m = _NAME.match(path.name)
            if not m:
                continue
            schema = json.loads(path.read_text())
            Draft202012Validator.check_schema(schema)
            self.validators[int(m.group(1))] = Draft202012Validator(
                schema, format_checker=Draft202012Validator.FORMAT_CHECKER
            )
        if not self.validators:
            raise FileNotFoundError(f"no session schemas in {schema_dir}")

    def errors(self, session: object) -> list[str]:
        """Up to MAX_ERRORS validation messages; empty when valid."""
        if not isinstance(session, dict):
            return ["$: session must be a JSON object"]
        version = session.get("schema_version")
        validator = (
            self.validators.get(version)
            if isinstance(version, int) and not isinstance(version, bool)
            else None
        )
        if validator is None:
            known = ", ".join(str(v) for v in sorted(self.validators))
            return [f"$.schema_version: must be one of {known}"]
        out = []
        for err in sorted(validator.iter_errors(session), key=lambda e: e.json_path):
            out.append(f"{err.json_path}: {err.message}")
            if len(out) >= MAX_ERRORS:
                break
        return out
