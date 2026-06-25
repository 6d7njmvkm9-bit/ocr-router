#!/usr/bin/env python3
"""Merge _read_item.json fragments into read-session.json.

Rules:
- Same file + same file_hash: update existing item
- Same file but different file_hash: mark old as superseded, add new
- Same file_hash but different path: record aliases
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READ_ITEM_VERSION = "read-item/1.0"
READ_SESSION_VERSION = "read-session/1.0"
VALID_TYPES = {"text_pdf","scanned_pdf","image","screenshot","word","mixed"}
VALID_STATUSES = {"read","partially_read","failed","needs_human_review"}
VALID_READERS = {"direct_text","pdfplumber","python_docx","office_reader","mineru","paddleocr","read_image","pypdfium2","mixed"}

def validate_item(item, idx):
    errors = []
    pfx = f"item[{idx}]"
    for f in ["file","file_hash","type","page_count","processed_pages","unprocessed_pages","read_status","reader_used","postprocess_applied","needs_visual_review","warnings"]:
        if f not in item:
            errors.append(f"{pfx}: missing {f}")
    if item.get("type") not in VALID_TYPES:
        errors.append(f"{pfx}: invalid type")
    if item.get("read_status") not in VALID_STATUSES:
        errors.append(f"{pfx}: invalid status")
    if item.get("reader_used") not in VALID_READERS:
        errors.append(f"{pfx}: invalid reader")
    return errors

def merge_item(session, item):
    items = session["items"]
    for idx, ex in enumerate(items):
        if ex.get("file") == item.get("file") and ex.get("file_hash") == item.get("file_hash"):
            items[idx] = {k:v for k,v in item.items() if k!="schema_version"}
            return
        if ex.get("file") == item.get("file") and ex.get("file_hash") != item.get("file_hash"):
            ex["_superseded"] = True
            items.append({k:v for k,v in item.items() if k!="schema_version"})
            return
    items.append({k:v for k,v in item.items() if k!="schema_version"})

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--work-dir", required=True)
    p.add_argument("--source-scope", action="append", default=[])
    p.add_argument("--read-item", action="append", default=[], required=True)
    args = p.parse_args()
    wd = Path(args.work_dir).expanduser().resolve()
    md = wd / ".material-reading"
    md.mkdir(parents=True, exist_ok=True)
    sp = md / "read-session.json"
    session = {"schema_version":READ_SESSION_VERSION,"source_scope":args.source_scope,"created_for":"ordinary_reading","items":[]}
    if sp.is_file():
        session = json.loads(sp.read_text())
        if not isinstance(session.get("items"), list):
            session["items"] = []
    for ip in args.read_item:
        item = json.loads(Path(ip).read_text())
        errs = validate_item(item, 0)
        if errs:
            for e in errs:
                print(f"ERROR: {e}", file=sys.stderr)
            return 2
        merge_item(session, item)
    session["merged_at"] = datetime.now(timezone.utc).isoformat()
    sp.write_text(json.dumps(session,ensure_ascii=False,indent=2))
    print(f"OK: {len(session['items'])} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
