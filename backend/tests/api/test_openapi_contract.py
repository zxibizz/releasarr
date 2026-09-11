"""Contract tests ensuring the generated OpenAPI matches the canonical spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from src.api.app import app

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def _load_contract() -> dict[str, Any]:
    spec_path = Path(__file__).resolve().parents[3] / "openapi.yaml"
    with spec_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _collect_operations(spec: dict[str, Any]) -> set[tuple[str, str]]:
    operations = set()
    for path, definition in spec.get("paths", {}).items():
        for method, operation in definition.items():
            if method.lower() not in HTTP_METHODS:
                continue
            operations.add((path, method.lower()))
            responses = operation.get("responses", {})
            for status_code in responses:
                operations.add((f"{path}::{method.lower()}::response", str(status_code)))
    return operations


@pytest.mark.asyncio
async def test_generated_openapi_covers_contract_operations() -> None:
    contract = _load_contract()
    generated = app.openapi()

    contract_ops = _collect_operations(contract)
    generated_ops = _collect_operations(generated)

    missing = contract_ops - generated_ops
    assert not missing, f"Missing OpenAPI operations: {sorted(missing)}"
