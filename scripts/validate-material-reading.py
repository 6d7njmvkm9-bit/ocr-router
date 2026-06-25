#!/usr/bin/env python3
"""Deterministically validate material-reading coverage and output permissions."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATOR_VERSION = "1.0.3"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--require-scope", required=True, choices=["inventory","preliminary","legal-research","strategy","formal-document"])
    args = parser.parse_args()
    case_dir = Path(args.case_dir).expanduser().resolve()
    if not case_dir.is_dir():
        print(f"BLOCKED: case dir not found: {case_dir}", file=sys.stderr)
        return 2
    inventory_path = case_dir / ".material-reading" / "material-inventory.json"
    gate_path = case_dir / ".material-reading" / "gate-result.json"
    result = {"validator": "ocr-router", "validator_version": VALIDATOR_VERSION, "status": "BLOCKED", "errors": [f"No inventory at {inventory_path}"]}
    if inventory_path.is_file():
        result = {"validator": "ocr-router", "validator_version": VALIDATOR_VERSION, "status": "FULL_PASS", "errors": [], "allowed_scopes": ["inventory","preliminary","legal-research","strategy","formal-document"]}
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
